# Guidance for agents working on `systems`

For the overall ResulTES architecture, read the org-wide guide first:
https://github.com/resultes-net/issues/blob/main/AGENTS.md. This file only adds what's specific to this repo.

## Layout
- `TTES/`, `PTES/`, `BTES/`: the three (py)TRNSYS system simulations. `common/`: shared ddck components and
  `create_common_parameters_ddck_file.py` (see below).
- `ci/`: requirements, scripts and data for CI. Pushes to `main` upload `systems-main.zip` to Swift for the runners and
  then start a PTES simulation on `dev.resultes.net` from `ci/data/ptes.json.template`.

## Environment and tests
- There's no venv checked out in the repo by default. `requirements.txt` pins `pytrnsys_process` etc.;
  `ci/requirements.txt` only holds the CI tooling (OpenStack client, `uv`, ...). `common/create_common_parameters_ddck_file.py`
  additionally needs `resultes_pydantic_models`, `pydantic`, `sympy` and `pandas`, which aren't pinned here.
- `pytest.ini` sets `python_files = *.py`, so pytest imports *every* Python file, including run and processing scripts.
  Collection fails with `ModuleNotFoundError` unless the dependencies above are installed.

## Parameters and weather data
- `common/create_common_parameters_ddck_file.py <parameters-json>` generates the per-simulation inputs into
  `common/ddck/parameters/`: `parameters.ddck`, `demand.csv`, the waste-heat source profile and the weather data.
- Weather data: one CSV per ISO reference climate in `common/ddck/weather/` (`Alpine.csv`, `Cold.csv`, ...), chosen by
  the simulation's `location`. The script copies it to `parameters/selected_weather_data.csv`, rolls it out over 10 years
  into `selected_weather_data_rolled_out.type99`, and derives statistics (yearly average, amplitude, coldest day) that
  go into `parameters.ddck`. Location coordinates live in `LOCATION_PARAMETERS` in the same script.
- `common/ddck/weather/selected_weather_data.ddck` assigns the rolled-out file (user format, `formatWeatherData = 1`);
  `weather_data_base.ddck` reads it via TRNSYS Type 99 (Type 109 is no longer used). The run configs include both via
  `COMMON$ weather\...`.
