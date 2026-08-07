import collections.abc as _cabc
import dataclasses as _dc
import json as _json
import pathlib as _pl
import sys as _sys
import typing as _tp

import pydantic as _pyd
import resultes_pydantic_models.simulations.parameters.ttes as _pttes
import resultes_pydantic_models.simulations.parameters.ttes.parameters.thermal_energy_storage as _pttess
import resultes_pydantic_models.simulations.simulation as _sim
import sympy as _sym


def create_real_positive_symbol(name: str) -> _sym.Symbol:
    return _sym.Symbol(name, real=True, positive=True)


demand_MWh = create_real_positive_symbol("$QSnkQ_MWh")

collector_area_m2 = create_real_positive_symbol("$CollAcollAp")

tank_volume_m3 = create_real_positive_symbol("$Vol_Tes1")
tank_volume_m3_per_MWh = create_real_positive_symbol("VperDemand_m3_per_MWh")
tank_volume_m3_per_m2 = create_real_positive_symbol("VperCollArea_m3_per_m2")

tank_h_to_D_ratio_1 = create_real_positive_symbol("tankHToDRatio")
tank_height_m = create_real_positive_symbol("$Heigh_Tes1")
tank_diameter_m = create_real_positive_symbol("tankDiameter")

tank_lambda_W_per_m_K = create_real_positive_symbol("tankLambda_W_per_m_K")
tank_U_value_W_per_m2_K = create_real_positive_symbol("$Ufoam_Tes1")
tank_insulation_thickness_cm = create_real_positive_symbol("tankInsulation_cm")

pi = create_real_positive_symbol("PI")

equations = [
    _sym.Eq(tank_volume_m3, tank_volume_m3_per_MWh * demand_MWh),
    _sym.Eq(tank_volume_m3, tank_volume_m3_per_m2 * collector_area_m2),
    _sym.Eq(tank_volume_m3, (tank_diameter_m / 2) ** 2 * pi * tank_height_m),
    _sym.Eq(tank_h_to_D_ratio_1, tank_height_m / tank_diameter_m),
    _sym.Eq(
        tank_U_value_W_per_m2_K,
        tank_lambda_W_per_m_K / (tank_insulation_thickness_cm / 100),
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
    parameters: _pttes.TtesSpecificParameters,
) -> tuple[_cabc.Sequence[_SpecifiedVariable], _cabc.Mapping[_sym.Symbol, _sym.Expr]]:
    tank_volume_specified_variable = _get_tank_volume_specified_variable(
        parameters.storage
    )

    tank_height_specified_variable = _SpecifiedVariable(
        tank_h_to_D_ratio_1,
        parameters.storage.height_to_diameter_ratio_1,
        [tank_height_m, tank_diameter_m],
    )

    tank_lambda_specified_variable = _SpecifiedVariable(tank_lambda_W_per_m_K, 0.04, [])

    tank_insulation_thickness_specified_variable = _SpecifiedVariable(
        tank_insulation_thickness_cm,
        parameters.storage.insulation_thickness_cm,
        [tank_U_value_W_per_m2_K],
    )

    variables_to_solve_for = [
        *tank_volume_specified_variable.variables_to_solve_for,
        *tank_height_specified_variable.variables_to_solve_for,
        *tank_insulation_thickness_specified_variable.variables_to_solve_for,
        *tank_lambda_specified_variable.variables_to_solve_for,
    ]

    solutions = _sym.solve(equations, variables_to_solve_for, dict=True)

    real_solutions = [s for s in solutions if all(v.is_real for v in s.values())]

    assert len(real_solutions) == 1
    solution = _tp.cast(_cabc.Mapping[_sym.Symbol, _sym.Expr], real_solutions[0])

    specified_variables = [
        tank_volume_specified_variable,
        tank_height_specified_variable,
        tank_insulation_thickness_specified_variable,
        tank_lambda_specified_variable,
    ]

    return specified_variables, solution


def _get_tank_volume_specified_variable(
    ptes_storage: _pttess.TtesStorage,
) -> _SpecifiedVariable:
    volume = ptes_storage.volume

    scaling = volume.scaling
    value = volume.value

    if scaling == "absolute_m3":
        return _SpecifiedVariable(
            tank_volume_m3,
            value,
            [tank_volume_m3_per_MWh, tank_volume_m3_per_m2],
        )
    if scaling == "relative_to_demand_m3_per_MWh":
        return _SpecifiedVariable(
            tank_volume_m3_per_MWh,
            value,
            [tank_volume_m3, tank_volume_m3_per_m2],
        )
    if scaling == "relative_to_collector_area_m3_per_m2":
        return _SpecifiedVariable(
            tank_volume_m3_per_m2,
            value,
            [tank_volume_m3, tank_volume_m3_per_MWh],
        )

    _tp.assert_never(scaling)


def _get_formatted_specified_variables_and_solved_equations(
    parameters: _pttes.TtesSpecificParameters,
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
        "storage": {
            "volume": {"scaling": "relative_to_collector_area_m3_per_m2", "value": 0.5},
            "ports_relative_heights_1": {
                "top": 0.80,
                "middle": 0.70,
                "bottom": 0.05,
            },
            "height_to_diameter_ratio_1": 3.0,
            "insulation_thickness_cm": 6,
        },
    }

    parameters = _pttes.TtesSpecificParameters(**data)

    result = _create_parameters_ddck_contents(parameters)

    print(result)


def _create_parameters_ddck_contents(parameters: _pttes.TtesSpecificParameters) -> str:
    port_heights = parameters.storage.ports_relative_heights_1

    formatted_specified_and_solved_variables_block = (
        _get_formatted_specified_variables_and_solved_equations(parameters)
    )

    parameters_ddck_contents = f"""\
*******************************
**BEGIN parameters.ddck 
*******************************
CONSTANTS #
$zInDp1_Tes1 = {port_heights.top}
$zInDp2_Tes1 = {port_heights.middle}
$zOutDp1_Tes1 = {port_heights.bottom}
$zOutDp2_Tes1 = {port_heights.bottom}

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
    assert isinstance(values, _pttes.TtesSpecificParameters)

    parameters_ddck_contents = _create_parameters_ddck_contents(values)
    PARAMETERS_DDCK_FILE_PATH.write_text(parameters_ddck_contents)


if __name__ == "__main__":
    if len(_sys.argv) != 2:
        print(f"ERROR: Usage: {_sys.argv[0]} <path-to-parameters-json-file>")
        _sys.exit(-1)

    parameters_json_file_path = _pl.Path(_sys.argv[1])

    main(parameters_json_file_path)
