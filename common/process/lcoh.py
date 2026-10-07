"""The levelized cost of heat (LCOH), with the annuity method of the final report (section 5.3).

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
    lifetime_a: float
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
            lifetime_a=get_value("FinLifetime_a"),
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
class Lcoh:
    """Named like the outputs. Costs in the cost region's currency."""

    I_solar: float
    I_tes: float
    I_boiler: float
    I_hp: float
    I_total: float
    # Per year.
    annuity: float
    # Per kWh.
    LCOH: float


def get_water_equivalent_volume_m3(
    volume_m3: float, volumetric_heat_capacity_kJ_per_m3_K: float
) -> float:
    return volume_m3 * volumetric_heat_capacity_kJ_per_m3_K / RHO_C_WATER_KJ_PER_M3_K


def get_present_value_factor(real_discount_rate_1: float, lifetime_a: float) -> float:
    r = real_discount_rate_1
    T = lifetime_a

    if r == 0:
        # The limit for r -> 0.
        return T

    return ((1 + r) ** T - 1) / ((1 + r) ** T * r)


def calculate_lcoh(system: System, parameters: FinancialParameters) -> Lcoh:
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
    E_0 = (
        yearly_fuel_kWh * parameters.fuel_price_per_kWh
        + yearly_electricity_kWh * parameters.electricity_price_per_kWh
    )

    m = parameters.maintenance_rate_1
    b = get_present_value_factor(parameters.real_discount_rate_1, parameters.lifetime_a)
    a = 1 / b

    annuity = a * (I * (1 + m * b) + E_0 * b)
    lcoh = annuity / system.yearly_demand_kWh

    return Lcoh(
        I_solar=I_solar,
        I_tes=I_tes,
        I_boiler=I_boiler,
        I_hp=I_hp,
        I_total=I,
        annuity=annuity,
        LCOH=lcoh,
    )


class Simulation(_tp.Protocol):
    """The parts of `pytrnsys_process.api.Simulation` used here."""

    scalar: "_pd.DataFrame"
    hourly: "_pd.DataFrame"


def add_lcoh(
    sim: Simulation, storage_volume_water_equivalent_m3: float, has_heat_pump: bool
) -> Lcoh:
    """Calculates the LCOH from the simulation's results and writes it, together with the
    investment costs, into `sim.scalar` (see `Lcoh` for the names).

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

    lcoh = calculate_lcoh(system, parameters)

    for name, value in _dc.asdict(lcoh).items():
        sim.scalar[name] = value

    print(f"LCOH of the system: {lcoh.LCOH} per kWh (in the cost region's currency)")

    return lcoh
