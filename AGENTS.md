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
  `ci/requirements.txt` only holds the CI tooling (OpenStack client, `uv`, ...). The `common/` scripts run in the runner's Python
  environment, so their dependencies are pinned there: https://github.com/resultes-net/runner/tree/main/requirements-3.13
  (`run-3rd-party.txt`, plus `resultes-pydantic-models` from the runner's `pydantic-models` submodule).
- `pytest.ini` sets `python_files = *.py`, so pytest imports *every* Python file, including run and processing scripts.
  Collection fails with `ModuleNotFoundError` unless the dependencies above are installed.
- To run only the parameters script's tests: `pytest common/test_create_common_parameters_ddck_file.py
  common/create_common_parameters_ddck_file.py`.

## Parameters and weather data
- `common/create_common_parameters_ddck_file.py <parameters-json>` generates the per-simulation inputs into
  `common/ddck/parameters/`: `parameters.ddck`, `demand.csv`, the waste-heat source profile and `weather_data.ddck`.
  Its tests are in `common/test_create_common_parameters_ddck_file.py` (they use temporary directories).
- The simulation has a `weather_data_id` (no longer a `location`). Before the script runs, the runner downloads the
  selected weather data into `common/ddck/parameters/selected_weather/` (`DIR_NAME` in
  `resultes_pydantic_models.weather_data`): the data file (`get_data_file_name`: `data.csv` for ISO, `data.tm2` for
  TM2) and a `README.md` (don't delete or overwrite it). The script tells the format by which data file exists.
- It copies the matching ddck from `common/ddck/weather/` (`weather_data_iso.ddck` or `weather_data_tm2.ddck`) to
  `common/ddck/parameters/weather_data.ddck`, so the run configs include `COMMON$ parameters\weather_data`.
- ISO: the data is rolled out over 10 years into `selected_weather/data_rolled_out.type99` (read via Type 99). The
  location (longitude, standard longitude, latitude) for its header comes from `LOCATION_PARAMETERS`, keyed by weather
  data ID (for the shared ISO data the lower-case climate name, e.g. `alpine`).
- TM2: no roll-out (`weather_data_tm2.ddck` reads the file itself); the statistics are computed with
  `pvlib.iotools.read_tmy2`. `pvlib` rejects raw Meteonorm files, but the server fixes them up on upload
  (`fix_up_and_validate_tm2_contents`), so the downloaded file is fine.
- Statistics (yearly average, amplitude, first coldest day) go into `parameters.ddck` in both cases.
- `common/ddck/weather/` holds the ddcks and the shared weather data: one CSV per ISO reference climate (`Alpine.csv`,
  `Cold.csv`, ...) and `CH-Zuerich-Kloten-66700.tm2` (TMY2, Zurich). The runner doesn't read them from here anymore
  (it downloads the selected data), but keep them: all shared weather data are kept in the repo, so that users who
  download a project have them. Don't write code for switching to other weather data.
- `selected_weather_data.ddck` / `weather_data_base.ddck` are the older ddcks for the ISO-only setup; the new ddcks
  `weather_data_iso.ddck` and `weather_data_tm2.ddck` are written by hand.
