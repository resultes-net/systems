import dataclasses as _dc

import pandas as _pd
import pytest as _pt

from . import financial as _financial

_PARAMETERS = _financial.FinancialParameters(
    real_discount_rate_1=0.03,
    calculation_period_a=30,
    maintenance_rate_1=0.01,
    fuel_price_per_kWh=0.08,
    electricity_price_per_kWh=0.2,
    boiler_efficiency_1=0.9,
    storage_cost=_financial.PowerLawCost(19142, -0.539),
    collector_field_cost=_financial.PowerLawCost(1330.12 / 1.24, -0.0873),
    heat_pump_cost_per_kW=954.1,
    boiler_cost_per_kW=250,
)

_HEAT_PUMP = _financial.HeatPump(capacity_kW=800, yearly_compressor_electricity_kWh=1e6)

_SYSTEM = _financial.System(
    yearly_demand_kWh=10e6,
    collector_area_m2=5000,
    storage_volume_water_equivalent_m3=20000,
    boiler_capacity_kW=3000,
    yearly_boiler_output_kWh=4e6,
    heat_pump=_HEAT_PUMP,
)


def test_present_value_factor() -> None:
    # b = ((1 + r)^T − 1) / ((1 + r)^T · r)
    assert _financial.get_present_value_factor(0.03, 30) == _pt.approx(19.600441)
    assert _financial.get_present_value_factor(0.05, 1) == _pt.approx(1 / 1.05)
    assert _financial.get_present_value_factor(0, 30) == 30
    assert _financial.get_present_value_factor(1e-9, 30) == _pt.approx(30)


def test_power_law_cost() -> None:
    cost = _financial.PowerLawCost(27102, -0.527)

    assert cost.get_specific_cost(1000) == _pt.approx(27102 * 1000**-0.527)
    assert cost.get_cost(1000) == _pt.approx(27102 * 1000**-0.527 * 1000)


def test_water_equivalent_volume() -> None:
    assert _financial.get_water_equivalent_volume_m3(1000, 2016) == _pt.approx(481.1456)
    assert _financial.get_water_equivalent_volume_m3(1000, 4190) == _pt.approx(1000)


def test_lcoh_with_heat_pump() -> None:
    result = _financial.calculate_financial_results(_SYSTEM, _PARAMETERS)

    I_solar = 1330.12 / 1.24 * 5000**-0.0873 * 5000
    I_tes = 19142 * 20000**-0.539 * 20000
    I_boiler = 250 * 3000
    I_hp = 954.1 * 800
    I = I_solar + I_tes + I_boiler + I_hp
    E_0 = 4e6 / 0.9 * 0.08 + 1e6 * 0.2
    b = 19.600441
    annuity = (I * (1 + 0.01 * b) + E_0 * b) / b

    assert result.collector_field_investment == _pt.approx(I_solar)
    assert result.storage_investment == _pt.approx(I_tes)
    assert result.boiler_investment == _pt.approx(I_boiler)
    assert result.heat_pump_investment == _pt.approx(I_hp)
    assert result.total_investment == _pt.approx(I)
    assert result.annuity_per_a == _pt.approx(annuity)
    assert result.lcoh_per_kWh == _pt.approx(annuity / 10e6)
    assert result.yearly_fuel_kWh == _pt.approx(4e6 / 0.9)
    assert result.yearly_fuel_cost_per_a == _pt.approx(4e6 / 0.9 * 0.08)

    # The annuity is the yearly capital cost, maintenance and energy cost.
    assert result.annuity_per_a == _pt.approx(I / b + 0.01 * I + E_0)


def test_lcoh_without_heat_pump_ignores_electricity() -> None:
    system = _dc.replace(_SYSTEM, heat_pump=None)
    parameters = _dc.replace(
        _PARAMETERS, electricity_price_per_kWh=1000, heat_pump_cost_per_kW=1e6
    )

    result = _financial.calculate_financial_results(system, parameters)
    with_heat_pump = _financial.calculate_financial_results(_SYSTEM, _PARAMETERS)

    assert result.heat_pump_investment == 0
    assert result.total_investment == _pt.approx(
        with_heat_pump.total_investment - with_heat_pump.heat_pump_investment
    )
    assert result.annuity_per_a == _pt.approx(
        with_heat_pump.annuity_per_a
        - with_heat_pump.heat_pump_investment * (1 / 19.600441 + 0.01)
        - 1e6 * 0.2
    )


def test_lcoh_matches_prototype() -> None:
    """The prototype (`lcoh()` in `TTES/process.pytrnsys` before resultes-net/issues#38) had
    no boiler and heat pump costs and a boiler efficiency of 1."""
    demand = 10e6
    consumption = 4e6
    size_solar = 5000
    size_tes = 2000
    r, T, m, fuel_price = 0.03, 30, 0.01, 0.08

    cost_solar = 1330.12 * size_solar ** (-0.0873)
    cost_tes = 1.24 * 27102 * size_tes ** (-0.527)
    b = ((1 + r) ** T - 1) / ((1 + r) ** T * r)
    I = cost_solar * size_solar + cost_tes * size_tes
    expected_lcoh = (1 / b) * (I + consumption * fuel_price * b + I * m * b) / demand

    parameters = _financial.FinancialParameters(
        real_discount_rate_1=r,
        calculation_period_a=T,
        maintenance_rate_1=m,
        fuel_price_per_kWh=fuel_price,
        electricity_price_per_kWh=0.2,
        boiler_efficiency_1=1,
        storage_cost=_financial.PowerLawCost(1.24 * 27102, -0.527),
        collector_field_cost=_financial.PowerLawCost(1330.12, -0.0873),
        heat_pump_cost_per_kW=954.1,
        boiler_cost_per_kW=0,
    )
    system = _financial.System(
        yearly_demand_kWh=demand,
        collector_area_m2=size_solar,
        storage_volume_water_equivalent_m3=size_tes,
        boiler_capacity_kW=3000,
        yearly_boiler_output_kWh=consumption,
        heat_pump=None,
    )

    assert _financial.calculate_financial_results(
        system, parameters
    ).lcoh_per_kWh == _pt.approx(expected_lcoh)


def test_boiler_efficiency_increases_fuel_cost() -> None:
    efficient = _financial.calculate_financial_results(
        _SYSTEM, _dc.replace(_PARAMETERS, boiler_efficiency_1=1)
    )
    inefficient = _financial.calculate_financial_results(
        _SYSTEM, _dc.replace(_PARAMETERS, boiler_efficiency_1=0.8)
    )

    assert inefficient.annuity_per_a - efficient.annuity_per_a == _pt.approx(
        4e6 * 0.08 * (1 / 0.8 - 1)
    )


_DECK_VARIABLES = {
    "FinRealDiscountRate": 0.03,
    "FinCalculationPeriod_a": 30,
    "FinMaintRate": 0.01,
    "FinFuelPrice_per_kWh": 0.08,
    "FinElecPrice_per_kWh": 0.2,
    "FinBoilerEff": 0.9,
    "FinCostTesA": 19142,
    "FinCostTesB": -0.539,
    "FinCostCollA": 1330.12 / 1.24,
    "FinCostCollB": -0.0873,
    "FinCostHp_per_kW": 954.1,
    "FinCostBoiler_per_kW": 250,
}


def test_financial_parameters_from_deck_variables() -> None:
    parameters = _financial.FinancialParameters.from_deck_variables(
        _DECK_VARIABLES.__getitem__
    )

    assert parameters == _PARAMETERS


@_dc.dataclass
class _Simulation:
    scalar: _pd.DataFrame
    hourly: _pd.DataFrame


def _create_simulation(has_heat_pump: bool) -> _Simulation:
    scalar = _pd.DataFrame(
        [
            {
                **_DECK_VARIABLES,
                "QSnkP_kW_Tot": 10e6,
                "CollAcollAp": 5000,
                "BolrPOut_kW_Tot": 4e6,
                **({"HpPelComp_kW_Tot": 1e6} if has_heat_pump else {}),
            }
        ]
    )

    hourly = _pd.DataFrame({"BolrPOut_kW": [0, 3000, 1500]})
    if has_heat_pump:
        hourly["HpQCond_kW"] = [800, 0, 400]

    return _Simulation(scalar, hourly)


@_pt.mark.parametrize("has_heat_pump", [True, False])
def test_add_financial_outputs(has_heat_pump: bool) -> None:
    sim = _create_simulation(has_heat_pump)

    _financial.add_financial_outputs(
        sim, storage_volume_water_equivalent_m3=20000, has_heat_pump=has_heat_pump
    )

    system = _SYSTEM if has_heat_pump else _dc.replace(_SYSTEM, heat_pump=None)
    expected = _financial.calculate_financial_results(system, _PARAMETERS)

    assert sim.scalar["LCOH"].iloc[0] == expected.lcoh_per_kWh
    assert sim.scalar["annuity"].iloc[0] == expected.annuity_per_a
    assert sim.scalar["I_solar"].iloc[0] == expected.collector_field_investment
    assert sim.scalar["I_tes"].iloc[0] == expected.storage_investment
    assert sim.scalar["I_boiler"].iloc[0] == expected.boiler_investment
    assert sim.scalar["I_hp"].iloc[0] == expected.heat_pump_investment
    assert sim.scalar["I_total"].iloc[0] == expected.total_investment
    assert sim.scalar["FuelCost_per_a"].iloc[0] == expected.yearly_fuel_cost_per_a
    assert sim.scalar["FuelConsumption_kWh"].iloc[0] == expected.yearly_fuel_kWh

    assert sim.scalar["BolrCap_kW"].iloc[0] == 3000
    assert sim.scalar["HpCap_kW"].iloc[0] == (800 if has_heat_pump else 0)
    assert sim.scalar["TesVolWaterEq_m3"].iloc[0] == 20000

    records = _pd.read_json(sim.scalar.to_json(orient="records"), orient="records")
    assert records["LCOH"].iloc[0] == _pt.approx(expected.lcoh_per_kWh)
    assert records["HpCap_kW"].iloc[0] == (800 if has_heat_pump else 0)
