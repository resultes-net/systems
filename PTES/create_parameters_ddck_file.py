import collections.abc as _cabc
import dataclasses as _dc
import json as _json
import pathlib as _pl
import sys as _sys
import typing as _tp

import resultes_pydantic_models.simulations.parameters as _params
import resultes_pydantic_models.simulations.parameters.common.collector_field as _pcoll
import resultes_pydantic_models.simulations.parameters.ptes as _pptes
import resultes_pydantic_models.simulations.parameters.ptes.parameters.thermal_energy_storage as _pptess
import sympy as _sym

demand_MWh = _sym.Symbol("QSnkQ_MWh")

collector_area_m2 = _sym.Symbol("CollAcollAp")
collector_area_m2_per_MWh = _sym.Symbol("szAperDemand_m2_per_MWh")

pit_store_volume_m3 = _sym.Symbol("pitStoreStVolume")
pit_store_volume_m3_per_MWh = _sym.Symbol("szVperDemand_m3_per_MWh")

equations = [
    _sym.Eq(collector_area_m2, collector_area_m2_per_MWh * demand_MWh),
    _sym.Eq(pit_store_volume_m3, pit_store_volume_m3_per_MWh * demand_MWh),
]

PARAMETERS_DDCK_FILE_PATH = (
    _pl.Path(__file__).parent / "ddck" / "parameters" / "parameters.ddck"
)


@_dc.dataclass
class _SpecifiedVariable:
    specified_variable: _sym.Symbol
    value: float
    variable_to_solve_for: _sym.Symbol


def get_specified_variables_and_solved_equations(
    parameters: _pptes.PtesParameters,
) -> tuple[_cabc.Sequence[_SpecifiedVariable], _cabc.Sequence[_sym.Eq]]:
    collector_field_area_specified_variable = (
        _get_collector_field_area_specified_variable(parameters.collector_field)
    )

    pit_store_volume_specified_variable = _get_pit_store_volume_specified_variable(
        parameters.storage
    )

    variables_to_solve_for = [
        collector_field_area_specified_variable.variable_to_solve_for,
        pit_store_volume_specified_variable.variable_to_solve_for,
    ]

    solutions = _sym.solve(equations, variables_to_solve_for, dict=True)

    assert len(solutions) == 1
    solution = solutions[0]

    solved_equations = [_sym.Eq(k, v) for k, v in solution.items()]

    specified_variables = [
        collector_field_area_specified_variable,
        pit_store_volume_specified_variable,
    ]

    return specified_variables, solved_equations


def _get_collector_field_area_specified_variable(
    collector_field: _pcoll.CollectorField,
) -> _SpecifiedVariable:
    area = collector_field.area

    scaling = area.scaling
    value = area.value

    if scaling == "absolute_m2":
        return _SpecifiedVariable(collector_area_m2, value, collector_area_m2_per_MWh)
    if scaling == "relative_to_demand_m2_per_MWh":
        return _SpecifiedVariable(collector_area_m2_per_MWh, value, collector_area_m2)

    _tp.assert_never(scaling)


def _get_pit_store_volume_specified_variable(
    ptes_storage: _pptess.PtesStorage,
) -> _SpecifiedVariable:
    volume = ptes_storage.volume

    scaling = volume.scaling
    value = volume.value

    if scaling == "absolute_m3":
        return _SpecifiedVariable(
            pit_store_volume_m3, value, pit_store_volume_m3_per_MWh
        )
    if scaling == "relative_to_demand_m3_per_MWh":
        return _SpecifiedVariable(
            pit_store_volume_m3_per_MWh, value, pit_store_volume_m3
        )

    _tp.assert_never(scaling)


def _get_formatted_specified_variables_and_solved_equations(parameters):
    specified_variables, solved_equations = (
        get_specified_variables_and_solved_equations(parameters.values)
    )

    result = "EQUATIONS #\n"

    for specified_variable in specified_variables:
        formatted_equation = (
            f"{specified_variable.specified_variable}={specified_variable.value}\n"
        )
        result += formatted_equation

    for solved_equation in solved_equations:
        formatted_equation = f"{solved_equation.lhs}={solved_equation.rhs}\n"
        result += formatted_equation

    return result


def test_get_solved_equations() -> None:
    data = {
        "values": {
            "type": "ptes",
            "demand": {"profile": {"profile_type": "predefined", "name": "default"}},
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
            "storage": {"volume": {"scaling": "absolute_m3", "value": 400}},
        }
    }

    parameters = _params.Parameters(**data)

    result = _get_formatted_specified_variables_and_solved_equations(parameters)

    print(result)


def main(parameters_json_file_path: _pl.Path) -> None:
    with parameters_json_file_path.open("r") as file:
        data = _json.load(file)

    parameters = _params.Parameters(**data)

    equations_block = _get_formatted_specified_variables_and_solved_equations(
        parameters
    )

    parameters_ddck_contents = f"""\
*******************************
**BEGIN parameters.ddck 
*******************************

{equations_block}

*******************************
**END parameters.ddck
*******************************
"""

    PARAMETERS_DDCK_FILE_PATH.write_text(parameters_ddck_contents)


if __name__ == "__main__":
    if len(_sys.argv) != 2:
        print(f"ERROR: Usage: {_sys.argv[0]} <path-to-parameters-json-file>")
        _sys.exit(-1)

    parameters_json_file_path = _sys.argv[1]

    main(parameters_json_file_path)
