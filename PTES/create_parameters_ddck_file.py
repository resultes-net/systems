import collections.abc as _cabc
import dataclasses as _dc
import json as _json
import pathlib as _pl
import sys as _sys
import typing as _tp

import pydantic as _pyd
import resultes_pydantic_models.simulations.parameters.common.collector_field as _pcoll
import resultes_pydantic_models.simulations.parameters.ptes as _pptes
import resultes_pydantic_models.simulations.parameters.ptes.parameters.thermal_energy_storage as _pptess
import resultes_pydantic_models.simulations.simulation as _sim
import sympy as _sym

demand_MWh = _sym.Symbol("$QSnkQ_MWh")

collector_area_m2 = _sym.Symbol("$CollAcollAp")
collector_area_m2_per_MWh = _sym.Symbol("AperDemand_m2_per_MWh")

pit_store_volume_m3 = _sym.Symbol("$pitStoreStVolume")
pit_store_volume_m3_per_MWh = _sym.Symbol("VperDemand_m3_per_MWh")
pit_store_volume_m3_per_m2 = _sym.Symbol("VperCollArea_m3_per_m2")

equations = [
    _sym.Eq(collector_area_m2, collector_area_m2_per_MWh * demand_MWh),
    _sym.Eq(pit_store_volume_m3, pit_store_volume_m3_per_MWh * demand_MWh),
    _sym.Eq(pit_store_volume_m3, pit_store_volume_m3_per_m2 * collector_area_m2),
]

PARAMETERS_DDCK_DIR_PATH = _pl.Path(__file__).parent / "ddck" / "parameters"

PARAMETERS_DDCK_FILE_PATH = PARAMETERS_DDCK_DIR_PATH / "parameters.ddck"

PREDEFINED_DEMAND_PROFILE_FILE_PATH = (
    _pl.Path(__file__).parents[1] / "common" / "ddck" / "QSnk" / "profile_norm.csv"
)

DEMAND_PROFILE_FILE_PATH = PARAMETERS_DDCK_DIR_PATH / "demand.csv"


@_dc.dataclass
class _SpecifiedVariable:
    specified_variable: _sym.Symbol
    value: float
    variables_to_solve_for: _cabc.Sequence[_sym.Symbol]


def get_specified_variables_and_solution(
    parameters: _pptes.PtesParameters,
) -> tuple[_cabc.Sequence[_SpecifiedVariable], _cabc.Mapping[_sym.Symbol, _sym.Expr]]:
    collector_field_area_specified_variable = (
        _get_collector_field_area_specified_variable(parameters.collector_field)
    )

    pit_store_volume_specified_variable = _get_pit_store_volume_specified_variable(
        parameters.storage
    )

    variables_to_solve_for = [
        *collector_field_area_specified_variable.variables_to_solve_for,
        *pit_store_volume_specified_variable.variables_to_solve_for,
    ]

    solutions = _sym.solve(equations, variables_to_solve_for, dict=True)

    assert len(solutions) == 1
    solution = _tp.cast(_cabc.Mapping[_sym.Symbol, _sym.Expr], solutions[0])

    specified_variables = [
        collector_field_area_specified_variable,
        pit_store_volume_specified_variable,
    ]

    return specified_variables, solution


def _get_collector_field_area_specified_variable(
    collector_field: _pcoll.CollectorField,
) -> _SpecifiedVariable:
    area = collector_field.area

    scaling = area.scaling
    value = area.value

    if scaling == "absolute_m2":
        return _SpecifiedVariable(collector_area_m2, value, [collector_area_m2_per_MWh])
    if scaling == "relative_to_demand_m2_per_MWh":
        return _SpecifiedVariable(collector_area_m2_per_MWh, value, [collector_area_m2])

    _tp.assert_never(scaling)


def _get_pit_store_volume_specified_variable(
    ptes_storage: _pptess.PtesStorage,
) -> _SpecifiedVariable:
    volume = ptes_storage.volume

    scaling = volume.scaling
    value = volume.value

    if scaling == "absolute_m3":
        return _SpecifiedVariable(
            pit_store_volume_m3,
            value,
            [pit_store_volume_m3_per_MWh, pit_store_volume_m3_per_m2],
        )
    if scaling == "relative_to_demand_m3_per_MWh":
        return _SpecifiedVariable(
            pit_store_volume_m3_per_MWh,
            value,
            [pit_store_volume_m3, pit_store_volume_m3_per_m2],
        )
    if scaling == "relative_to_collector_area_m3_per_m2":
        return _SpecifiedVariable(
            pit_store_volume_m3_per_m2,
            value,
            [pit_store_volume_m3, pit_store_volume_m3_per_MWh],
        )

    _tp.assert_never(scaling)


def _get_formatted_specified_variables_and_solved_equations(
    parameters: _pptes.PtesParameters,
) -> str:
    specified_variables, solution = get_specified_variables_and_solution(parameters)

    result = "CONSTANTS #\n"

    for specified_variable in specified_variables:
        formatted_equation = (
            f"{specified_variable.specified_variable}={specified_variable.value}\n"
        )
        result += formatted_equation

    for variable, expression in solution.items():
        formatted_equation = f"{variable}={expression}\n"
        result += formatted_equation

    return result


def test_get_solved_equations() -> None:
    data: _pyd.JsonValue = {
        "type": "ptes",
        "time": {"start": 5760, "stop": 17280, "dt_sim": 0.5},
        "demand": {
            "name": "synthetic",
            "scaling_factor": 2,
            "hourly_heat_demand_MW": [3 if i % 2 == 0 else 5 for i in range(365 * 24)],
        },
        "collector_field": {
            "area": {"scaling": "relative_to_demand_m2_per_MWh", "value": 4.0},
            "inclination_deg": 45.0,
            "orientation_east_west_deg": 0.0,
            "type": "flat-plate",
            "performance_coefficients": {
                "a0": 0.857,
                "a1_kW_per_m2_per_K": 0.00416,
                "a2_kW_per_m2_per_K2": 8.9e-06,
            },
            "nominal_massflow": {
                "scaling": "relative_to_collector_area_kg_per_h_m2",
                "value": 15.0,
            },
        },
        "storage": {
            "volume": {"scaling": "absolute_m3", "value": 400},
            "ports_relative_heights_1": {
                "top": 0.80,
                "middle": 0.70,
                "bottom": 0.05,
            },
        },
        "control": {
            "demand_temperature_setpoint_degC": 80.0,
            "demand_delta_T_degC": 30.0,
            "storage_temperature_maximum_degC": 85.0,
        },
    }

    parameters = _pptes.PtesParameters(**data)

    result = _create_parameters_ddck_contents(parameters)

    print(result)


def _create_parameters_ddck_contents(parameters: _pptes.PtesParameters) -> str:
    time = parameters.time

    demand = parameters.demand

    unscaledYearlyHeatDemandMWh = sum(demand.hourly_heat_demand_MW)

    control = parameters.control

    port_heights = parameters.storage.ports_relative_heights_1

    formatted_specified_and_solved_variables_block = (
        _get_formatted_specified_variables_and_solved_equations(parameters)
    )

    parameters_ddck_contents = f"""\
*******************************
**BEGIN parameters.ddck 
*******************************
CONSTANTS #
$START = {time.start}
$STOP = {time.stop}
$dtSim = {time.dt_sim}

$QSnkScalingFactor = {demand.scaling_factor:.2}
$QSnkQUnscaled_MWh = {unscaledYearlyHeatDemandMWh}
$QSnkQ_MWh = $QSnkScalingFactor*$QSnkQUnscaled_MWh

$HPsizeUsed = $QSnkQ_MWh/10

$TSetDem = {control.demand_temperature_setpoint_degC}
$QSnkdT = {control.demand_delta_T_degC}
$TTesMax = {control.storage_temperature_maximum_degC}

$psPtesPortsHeightRelTop = {port_heights.top}
$psPtesPortsHeightRelMiddle = {port_heights.middle}
$psPtesPortsHeightRelBottom = {port_heights.bottom}

{formatted_specified_and_solved_variables_block}


*******************************
**END parameters.ddck
*******************************
"""

    return parameters_ddck_contents


def main(parameters_json_file_path: _pl.Path) -> None:
    with parameters_json_file_path.open("r") as file:
        data = _json.load(file)

    simulation = _sim.Simulation(**data)

    values = simulation.parameters.values
    assert isinstance(values, _pptes.PtesParameters)

    parameters_ddck_contents = _create_parameters_ddck_contents(values)
    PARAMETERS_DDCK_FILE_PATH.write_text(parameters_ddck_contents)

    _write_demand_profile(values.demand.hourly_heat_demand_MW)


def _write_demand_profile(hourly_heat_demand_MW: _cabc.Sequence[float]) -> None:
    header = "Hourly heat demand [MW]\n"

    formatted_hourly_heat_demands = "\n".join(str(p) for p in hourly_heat_demand_MW)

    demand_profile_contents = header + formatted_hourly_heat_demands

    DEMAND_PROFILE_FILE_PATH.write_text(demand_profile_contents)


if __name__ == "__main__":
    if len(_sys.argv) != 2:
        print(f"ERROR: Usage: {_sys.argv[0]} <path-to-parameters-json-file>")
        _sys.exit(-1)

    parameters_json_file_path = _pl.Path(_sys.argv[1])

    main(parameters_json_file_path)
