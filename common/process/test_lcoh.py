import dataclasses as _dc

import pandas as _pd
import pytest as _pt

from . import lcoh as _lcoh

_PARAMETERS = _lcoh.FinancialParameters(
    real_discount_rate_1=0.03,
    lifetime_a=30,
    maintenance_rate_1=0.01,
    fuel_price_per_kWh=0.08,
    electricity_price_per_kWh=0.2,
    boiler_efficiency_1=0.9,
    storage_cost=_lcoh.PowerLawCost(19142, -0.539),
    collector_field_cost=_lcoh.PowerLawCost(1330.12 / 1.24, -0.0873),
    heat_pump_cost_per_kW=954.1,
    boiler_cost_per_kW=250,
)

_HEAT_PUMP = _lcoh.HeatPump(capacity_kW=800, yearly_compressor_electricity_kWh=1e6)

_SYSTEM = _lcoh.System(
    yearly_demand_kWh=10e6,
    collector_area_m2=5000,
    storage_volume_water_equivalent_m3=20000,
    boiler_capacity_kW=3000,
    yearly_boiler_output_kWh=4e6,
    heat_pump=_HEAT_PUMP,
)


def test_present_value_factor() -> None:
    # b = ((1 + r)^T − 1) / ((1 + r)^T · r)
    assert _lcoh.get_present_value_factor(0.03, 30) == _pt.approx(19.600441)
    assert _lcoh.get_present_value_factor(0.05, 1) == _pt.approx(1 / 1.05)
    assert _lcoh.get_present_value_factor(0, 30) == 30
    assert _lcoh.get_present_value_factor(1e-9, 30) == _pt.approx(30)


def test_power_law_cost() -> None:
    cost = _lcoh.PowerLawCost(27102, -0.527)

    assert cost.get_specific_cost(1000) == _pt.approx(27102 * 1000**-0.527)
    assert cost.get_cost(1000) == _pt.approx(27102 * 1000**-0.527 * 1000)


def test_water_equivalent_volume() -> None:
    assert _lcoh.get_water_equivalent_volume_m3(1000, 2016) == _pt.approx(481.1456)
    assert _lcoh.get_water_equivalent_volume_m3(1000, 4190) == _pt.approx(1000)


def test_lcoh_with_heat_pump() -> None:
    result = _lcoh.calculate_lcoh(_SYSTEM, _PARAMETERS)

    I_solar = 1330.12 / 1.24 * 5000**-0.0873 * 5000
    I_tes = 19142 * 20000**-0.539 * 20000
    I_boiler = 250 * 3000
    I_hp = 954.1 * 800
    I = I_solar + I_tes + I_boiler + I_hp
    E_0 = 4e6 / 0.9 * 0.08 + 1e6 * 0.2
    b = 19.600441
    annuity = (I * (1 + 0.01 * b) + E_0 * b) / b

    assert result.I_solar == _pt.approx(I_solar)
    assert result.I_tes == _pt.approx(I_tes)
    assert result.I_boiler == _pt.approx(I_boiler)
    assert result.I_hp == _pt.approx(I_hp)
    assert result.I_total == _pt.approx(I)
    assert result.annuity == _pt.approx(annuity)
    assert result.LCOH == _pt.approx(annuity / 10e6)

    # The annuity is the yearly capital cost, maintenance and energy cost.
    assert result.annuity == _pt.approx(I / b + 0.01 * I + E_0)


def test_lcoh_without_heat_pump_ignores_electricity() -> None:
    system = _dc.replace(_SYSTEM, heat_pump=None)
    parameters = _dc.replace(
        _PARAMETERS, electricity_price_per_kWh=1000, heat_pump_cost_per_kW=1e6
    )

    result = _lcoh.calculate_lcoh(system, parameters)
    with_heat_pump = _lcoh.calculate_lcoh(_SYSTEM, _PARAMETERS)

    assert result.I_hp == 0
    assert result.I_total == _pt.approx(with_heat_pump.I_total - with_heat_pump.I_hp)
    assert result.annuity == _pt.approx(
        with_heat_pump.annuity
        - with_heat_pump.I_hp * (1 / 19.600441 + 0.01)
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

    parameters = _lcoh.FinancialParameters(
        real_discount_rate_1=r,
        lifetime_a=T,
        maintenance_rate_1=m,
        fuel_price_per_kWh=fuel_price,
        electricity_price_per_kWh=0.2,
        boiler_efficiency_1=1,
        storage_cost=_lcoh.PowerLawCost(1.24 * 27102, -0.527),
        collector_field_cost=_lcoh.PowerLawCost(1330.12, -0.0873),
        heat_pump_cost_per_kW=954.1,
        boiler_cost_per_kW=0,
    )
    system = _lcoh.System(
        yearly_demand_kWh=demand,
        collector_area_m2=size_solar,
        storage_volume_water_equivalent_m3=size_tes,
        boiler_capacity_kW=3000,
        yearly_boiler_output_kWh=consumption,
        heat_pump=None,
    )

    assert _lcoh.calculate_lcoh(system, parameters).LCOH == _pt.approx(expected_lcoh)


def test_boiler_efficiency_increases_fuel_cost() -> None:
    efficient = _lcoh.calculate_lcoh(
        _SYSTEM, _dc.replace(_PARAMETERS, boiler_efficiency_1=1)
    )
    inefficient = _lcoh.calculate_lcoh(
        _SYSTEM, _dc.replace(_PARAMETERS, boiler_efficiency_1=0.8)
    )

    assert inefficient.annuity - efficient.annuity == _pt.approx(
        4e6 * 0.08 * (1 / 0.8 - 1)
    )


_DECK_VARIABLES = {
    "FinRealDiscountRate": 0.03,
    "FinLifetime_a": 30,
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
    parameters = _lcoh.FinancialParameters.from_deck_variables(
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
def test_add_lcoh(has_heat_pump: bool) -> None:
    sim = _create_simulation(has_heat_pump)

    result = _lcoh.add_lcoh(
        sim, storage_volume_water_equivalent_m3=20000, has_heat_pump=has_heat_pump
    )

    system = _SYSTEM if has_heat_pump else _dc.replace(_SYSTEM, heat_pump=None)
    expected = _lcoh.calculate_lcoh(system, _PARAMETERS)
    assert result == expected

    for name in ["LCOH", "I_solar", "I_tes", "I_boiler", "I_hp", "I_total", "annuity"]:
        assert sim.scalar[name].iloc[0] == getattr(expected, name)

    records = _pd.read_json(sim.scalar.to_json(orient="records"), orient="records")
    assert records["LCOH"].iloc[0] == _pt.approx(expected.LCOH)
