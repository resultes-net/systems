"""The financial results: the levelized cost of heat (LCOH) and the investment costs, with the
annuity method of the final report (section 5.3).

Shared by the systems' post-processing scripts (`[T|P|B]TES/process.pytrnsys`). The financial
parameters are read from the deck (they're written into `parameters.ddck` by
`common/create_common_parameters_ddck_file.py`). They are in the cost region's currency, which
the systems don't know: the results are in the same currency.
"""

import dataclasses as _dc
import typing as _tp

if _tp.TYPE_CHECKING:
    import pandas as _pd

# Volumetric heat capacity of water, to get a water equivalent volume.
RHO_C_WATER_KJ_PER_M3_K = 4190.0


@_dc.dataclass(frozen=True)
class PowerLawCost:
    """A specific cost of `a * x**b`, per unit of `x`."""

    a: float
    b: float

    def get_specific_cost(self, x: float) -> float:
        return self.a * x**self.b

    def get_cost(self, x: float) -> float:
        return self.get_specific_cost(x) * x


@_dc.dataclass(frozen=True)
class FinancialParameters:
    real_discount_rate_1: float
    calculation_period_a: float
    maintenance_rate_1: float
    fuel_price_per_kWh: float
    electricity_price_per_kWh: float
    boiler_efficiency_1: float
    # Per m³ water equivalent.
    storage_cost: PowerLawCost
    # Per m² aperture area.
    collector_field_cost: PowerLawCost
    # Per kW thermal.
    heat_pump_cost_per_kW: float
    boiler_cost_per_kW: float

    @staticmethod
    def from_deck_variables(
        get_value: _tp.Callable[[str], float],
    ) -> "FinancialParameters":
        return FinancialParameters(
            real_discount_rate_1=get_value("FinRealDiscountRate"),
            calculation_period_a=get_value("FinCalculationPeriod_a"),
            maintenance_rate_1=get_value("FinMaintRate"),
            fuel_price_per_kWh=get_value("FinFuelPrice_per_kWh"),
            electricity_price_per_kWh=get_value("FinElecPrice_per_kWh"),
            boiler_efficiency_1=get_value("FinBoilerEff"),
            storage_cost=PowerLawCost(
                get_value("FinCostTesA"), get_value("FinCostTesB")
            ),
            collector_field_cost=PowerLawCost(
                get_value("FinCostCollA"), get_value("FinCostCollB")
            ),
            heat_pump_cost_per_kW=get_value("FinCostHp_per_kW"),
            boiler_cost_per_kW=get_value("FinCostBoiler_per_kW"),
        )


@_dc.dataclass(frozen=True)
class HeatPump:
    capacity_kW: float
    yearly_compressor_electricity_kWh: float


@_dc.dataclass(frozen=True)
class System:
    yearly_demand_kWh: float
    collector_area_m2: float
    storage_volume_water_equivalent_m3: float
    boiler_capacity_kW: float
    yearly_boiler_output_kWh: float
    heat_pump: HeatPump | None


@_dc.dataclass(frozen=True)
class FinancialResults:
    """The costs are in the cost region's currency."""

    collector_field_investment: float
    storage_investment: float
    boiler_investment: float
    heat_pump_investment: float
    total_investment: float
    annuity_per_a: float
    lcoh_per_kWh: float
    yearly_fuel_kWh: float
    yearly_fuel_cost_per_a: float


def get_water_equivalent_volume_m3(
    volume_m3: float, volumetric_heat_capacity_kJ_per_m3_K: float
) -> float:
    return volume_m3 * volumetric_heat_capacity_kJ_per_m3_K / RHO_C_WATER_KJ_PER_M3_K


def get_present_value_factor(
    real_discount_rate_1: float, calculation_period_a: float
) -> float:
    r = real_discount_rate_1
    T = calculation_period_a

    if r == 0:
        # The limit for r -> 0.
        return T

    return ((1 + r) ** T - 1) / ((1 + r) ** T * r)


def calculate_financial_results(
    system: System, parameters: FinancialParameters
) -> FinancialResults:
    """`LCOH = a · (I · (1 + m · b) + E₀ · b) / Q_demand`, with `b` the present value factor
    and `a = 1 / b` the annuity factor."""
    I_solar = parameters.collector_field_cost.get_cost(system.collector_area_m2)
    I_tes = parameters.storage_cost.get_cost(system.storage_volume_water_equivalent_m3)
    I_boiler = parameters.boiler_cost_per_kW * system.boiler_capacity_kW
    I_hp = (
        parameters.heat_pump_cost_per_kW * system.heat_pump.capacity_kW
        if system.heat_pump
        else 0.0
    )
    I = I_solar + I_tes + I_boiler + I_hp

    yearly_fuel_kWh = system.yearly_boiler_output_kWh / parameters.boiler_efficiency_1
    yearly_electricity_kWh = (
        system.heat_pump.yearly_compressor_electricity_kWh if system.heat_pump else 0.0
    )
    yearly_fuel_cost = yearly_fuel_kWh * parameters.fuel_price_per_kWh
    E_0 = (
        yearly_fuel_cost + yearly_electricity_kWh * parameters.electricity_price_per_kWh
    )

    m = parameters.maintenance_rate_1
    b = get_present_value_factor(
        parameters.real_discount_rate_1, parameters.calculation_period_a
    )
    a = 1 / b

    annuity = a * (I * (1 + m * b) + E_0 * b)
    lcoh = annuity / system.yearly_demand_kWh

    return FinancialResults(
        collector_field_investment=I_solar,
        storage_investment=I_tes,
        boiler_investment=I_boiler,
        heat_pump_investment=I_hp,
        total_investment=I,
        annuity_per_a=annuity,
        lcoh_per_kWh=lcoh,
        yearly_fuel_kWh=yearly_fuel_kWh,
        yearly_fuel_cost_per_a=yearly_fuel_cost,
    )


class Simulation(_tp.Protocol):
    """The parts of `pytrnsys_process.api.Simulation` used here."""

    scalar: "_pd.DataFrame"
    hourly: "_pd.DataFrame"


def add_financial_outputs(
    sim: Simulation, storage_volume_water_equivalent_m3: float, has_heat_pump: bool
) -> None:
    """Calculates the LCOH from the simulation's results and writes it, together with the
    investment costs and the quantities they're based on, and the yearly fuel cost and
    consumption (the boiler's input), into `sim.scalar`. The collector aperture area is
    already there (`CollAcollAp`).

    Expects the boiler's and the demand's yearly totals (`BolrPOut_kW_Tot`, `QSnkP_kW_Tot`) and,
    with a heat pump, the compressor's (`HpPelComp_kW_Tot`) in `sim.scalar`. The capacities
    are the peaks of the hourly values.
    """

    def get_scalar(name: str) -> float:
        return float(sim.scalar[name].iloc[0])

    def get_hourly_peak(name: str) -> float:
        return float(sim.hourly[name].max())

    heat_pump = (
        HeatPump(
            capacity_kW=get_hourly_peak("HpQCond_kW"),
            yearly_compressor_electricity_kWh=get_scalar("HpPelComp_kW_Tot"),
        )
        if has_heat_pump
        else None
    )

    system = System(
        yearly_demand_kWh=get_scalar("QSnkP_kW_Tot"),
        collector_area_m2=get_scalar("CollAcollAp"),
        storage_volume_water_equivalent_m3=storage_volume_water_equivalent_m3,
        boiler_capacity_kW=get_hourly_peak("BolrPOut_kW"),
        yearly_boiler_output_kWh=get_scalar("BolrPOut_kW_Tot"),
        heat_pump=heat_pump,
    )

    parameters = FinancialParameters.from_deck_variables(get_scalar)

    results = calculate_financial_results(system, parameters)

    sim.scalar["LCOH"] = results.lcoh_per_kWh
    sim.scalar["annuity"] = results.annuity_per_a
    sim.scalar["I_solar"] = results.collector_field_investment
    sim.scalar["I_tes"] = results.storage_investment
    sim.scalar["I_boiler"] = results.boiler_investment
    sim.scalar["I_hp"] = results.heat_pump_investment
    sim.scalar["I_total"] = results.total_investment
    sim.scalar["FuelCost_per_a"] = results.yearly_fuel_cost_per_a
    sim.scalar["FuelConsumption_kWh"] = results.yearly_fuel_kWh

    sim.scalar["BolrCap_kW"] = system.boiler_capacity_kW
    # 0 without a heat pump, like `I_hp`.
    sim.scalar["HpCap_kW"] = heat_pump.capacity_kW if heat_pump else 0.0
    sim.scalar["TesVolWaterEq_m3"] = system.storage_volume_water_equivalent_m3
