import collections.abc as _cabc
import dataclasses as _dc
import json as _json
import pathlib as _pl
import sys as _sys
import typing as _tp

import pydantic as _pyd
import resultes_pydantic_models.simulations.parameters.btes as _pbtes
import resultes_pydantic_models.simulations.parameters.btes.parameters.thermal_energy_storage as _pbtess
import resultes_pydantic_models.simulations.simulation as _sim
import sympy as _sym

demand_MWh = _sym.Symbol("$QSnkQ_MWh")

collector_area_m2 = _sym.Symbol("$CollAcollAp")

borehole_store_volume_m3 = _sym.Symbol("$BoHxV")
borehole_store_volume_m3_per_MWh = _sym.Symbol("VperDemand_m3_per_MWh")
borehole_store_volume_m3_per_m2 = _sym.Symbol("VperCollArea_m3_per_m2")

equations = [
    _sym.Eq(borehole_store_volume_m3, borehole_store_volume_m3_per_MWh * demand_MWh),
    _sym.Eq(
        borehole_store_volume_m3, borehole_store_volume_m3_per_m2 * collector_area_m2
    ),
]

PARAMETERS_DDCK_DIR_PATH = _pl.Path(__file__).parent / "ddck" / "parameters"

PARAMETERS_DDCK_FILE_PATH = PARAMETERS_DDCK_DIR_PATH / "parameters.ddck"


@_dc.dataclass
class _SpecifiedVariable:
    specified_variable: _sym.Symbol
    value: float
    variables_to_solve_for: _cabc.Sequence[_sym.Symbol]


def get_specified_variables_and_solution(
    parameters: _pbtes.BtesSpecificParameters,
) -> tuple[_cabc.Sequence[_SpecifiedVariable], _cabc.Mapping[_sym.Symbol, _sym.Expr]]:
    borehole_store_volume_specified_variable = (
        _get_borehole_store_volume_specified_variable(parameters.storage)
    )

    variables_to_solve_for = [
        *borehole_store_volume_specified_variable.variables_to_solve_for,
    ]

    solutions = _sym.solve(equations, variables_to_solve_for, dict=True)

    assert len(solutions) == 1
    solution = _tp.cast(_cabc.Mapping[_sym.Symbol, _sym.Expr], solutions[0])

    specified_variables = [
        borehole_store_volume_specified_variable,
    ]

    return specified_variables, solution


def _get_borehole_store_volume_specified_variable(
    btes_storage: _pbtess.BtesStorage,
) -> _SpecifiedVariable:
    volume = btes_storage.volume

    scaling = volume.scaling
    value = volume.value

    if scaling == "absolute_m3":
        return _SpecifiedVariable(
            borehole_store_volume_m3,
            value,
            [borehole_store_volume_m3_per_MWh, borehole_store_volume_m3_per_m2],
        )
    if scaling == "relative_to_demand_m3_per_MWh":
        return _SpecifiedVariable(
            borehole_store_volume_m3_per_MWh,
            value,
            [borehole_store_volume_m3, borehole_store_volume_m3_per_m2],
        )
    if scaling == "relative_to_collector_area_m3_per_m2":
        return _SpecifiedVariable(
            borehole_store_volume_m3_per_m2,
            value,
            [borehole_store_volume_m3, borehole_store_volume_m3_per_MWh],
        )

    _tp.assert_never(scaling)


def _get_formatted_specified_variables_and_solved_equations(
    parameters: _pbtes.BtesSpecificParameters,
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
        "type": "btes",
        "storage": {
            "volume": {"scaling": "absolute_m3", "value": 400},
        },
    }

    parameters = _pbtes.BtesSpecificParameters(**data)

    result = _create_parameters_ddck_contents(parameters)

    print(result)


def _create_parameters_ddck_contents(parameters: _pbtes.BtesSpecificParameters) -> str:
    formatted_specified_and_solved_variables_block = (
        _get_formatted_specified_variables_and_solved_equations(parameters)
    )

    parameters_ddck_contents = f"""\
*******************************
**BEGIN parameters.ddck 
*******************************
{formatted_specified_and_solved_variables_block}


*******************************
**END parameters.ddck
*******************************
"""

    return parameters_ddck_contents


def main(parameters_json_file_path: _pl.Path) -> None:
    with parameters_json_file_path.open("r") as file:
        data = _json.load(file)

    simulation = _sim.SimulationWithParams(**data)

    values = simulation.parameters.values
    assert isinstance(values, _pbtes.BtesSpecificParameters)

    parameters_ddck_contents = _create_parameters_ddck_contents(values)
    PARAMETERS_DDCK_FILE_PATH.write_text(parameters_ddck_contents)


if __name__ == "__main__":
    if len(_sys.argv) != 2:
        print(f"ERROR: Usage: {_sys.argv[0]} <path-to-parameters-json-file>")
        _sys.exit(-1)

    parameters_json_file_path = _pl.Path(_sys.argv[1])

    main(parameters_json_file_path)
