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

n_boreholes_fractional_1 = _sym.Symbol("nBor_frac_1")
n_boreholes_1_per_MWh = _sym.Symbol("nBor_1_per_MWh")
n_boreholes_1_per_m2 = _sym.Symbol("nBor_1_per_m2")

equations = [
    _sym.Eq(n_boreholes_fractional_1, n_boreholes_1_per_MWh * demand_MWh),
    _sym.Eq(n_boreholes_fractional_1, n_boreholes_1_per_m2 * collector_area_m2),
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
    n_boreholes = btes_storage.n_boreholes

    scaling = n_boreholes.scaling
    value = n_boreholes.value

    if scaling == "absolute_1":
        return _SpecifiedVariable(
            n_boreholes_fractional_1,
            value,
            [n_boreholes_1_per_MWh, n_boreholes_1_per_m2],
        )
    if scaling == "relative_to_demand_1_per_MWh":
        return _SpecifiedVariable(
            n_boreholes_1_per_MWh,
            value,
            [n_boreholes_fractional_1, n_boreholes_1_per_m2],
        )
    if scaling == "relative_to_collector_area_1_per_m2":
        return _SpecifiedVariable(
            n_boreholes_1_per_m2,
            value,
            [n_boreholes_fractional_1, n_boreholes_1_per_MWh],
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
            "n_boreholes": {
                "scaling": "relative_to_collector_area_1_per_m2",
                "value": 4e-3,
            },
            "borehole_depth_m": 70,
            "borehole_spacing_m": 3,
            "heat_exchanger": {
                "fluid_to_ground_resistance_m_K_per_W": 0.1,
                "pipe_to_pipe_resistance_m_K_per_W": 0.18,
            },
        },
    }

    parameters = _pbtes.BtesSpecificParameters(**data)

    result = _create_parameters_ddck_contents(parameters)

    print(result)


def _create_parameters_ddck_contents(parameters: _pbtes.BtesSpecificParameters) -> str:
    formatted_specified_and_solved_variables_block = (
        _get_formatted_specified_variables_and_solved_equations(parameters)
    )

    storage = parameters.storage

    parameters_ddck_contents = f"""\
*******************************
**BEGIN parameters.ddck 
*******************************
CONSTANTS #
$BoHxZ = {storage.borehole_depth_m}
BoSpacing = {storage.borehole_spacing_m}
$BoHxNBor = INT({n_boreholes_fractional_1.name} + 0.5)
$BoHxV = $BoHxNBor * (0.525 * BoSpacing)**2 * $PI * $BoHxZ
$BoHxRb = {storage.heat_exchanger.fluid_to_ground_resistance_m_K_per_W}
$BoHxRa = {-storage.heat_exchanger.pipe_to_pipe_resistance_m_K_per_W}

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
