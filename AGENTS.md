# Guidance for agents working on `systems`

For the overall ResulTES architecture, read the org-wide guide first:
https://github.com/resultes-net/issues/blob/main/AGENTS.md. This file only adds what's specific to this repo.

## Layout
1. `TTES/`, `PTES/`, `BTES/`: the three (py)TRNSYS system simulations. `common/`: shared ddck components and
   `create_common_parameters_ddck_file.py` (see below).
1. `ci/`: requirements, scripts and data for CI. *Every* push to `main` uploads `systems-main.zip` to Swift for the runners
   and then starts a PTES simulation on `dev.resultes.net` from `ci/data/ptes.json.template`.

## Environment and tests
1. There's no venv checked out in the repo by default. `requirements.txt` pins `pytrnsys_process` etc.;
   `ci/requirements.txt` only holds the CI tooling (OpenStack client, `uv`, ...). The `common/` scripts run in the runner's Python
   environment, so their dependencies are pinned there: https://github.com/resultes-net/runner/tree/main/requirements-3.13.
   `run.txt` is what runs in production and staging (`run-3rd-party.txt` plus the runner's own packages, e.g.
   `resultes-pydantic-models` from its `pydantic-models` submodule). For dev work, use `dev.txt`: the same plus Black,
   pytest, ...
1. The runner's requirements are pinned for Windows, so that environment, and with it pytest and Black for `systems`, only
   exists as a Windows venv in a runner checkout. From WSL, run it as `<runner checkout>/venv/Scripts/python.exe -m pytest
   ...` from the `systems` checkout. A Linux checkout of the runner can't have it.
1. That venv imports `resultes_pydantic_models` from its runner checkout's `pydantic-models` submodule. To test against
   another (e.g. unpushed) `pydantic-models`, set `PYTHONPATH` to that checkout's `pydantic-models/src`. From WSL, also
   pass it on to the Windows process with `WSLENV=PYTHONPATH`.
1. The Python code, including the `.pytrnsys` scripts, is Black-formatted (default settings). Use the Black from the
   runner's `dev.txt`, and format only the files you change.
1. `pytest.ini` sets `python_files = *.py`, so pytest imports *every* Python file, including run and processing scripts.
   Collection fails with `ModuleNotFoundError` unless the dependencies above are installed.
1. To run only the parameters script's tests: `pytest common/test_create_common_parameters_ddck_file.py
   common/create_common_parameters_ddck_file.py`.

## Simulation model
1. Each system's deck is assembled from ddcks (`[T|P|B]TES/ddck/`, `common/ddck/`) by its `run_*.config`.
   `deck <variable> <value>` lines there override ddck variables (e.g. `loop2Len`), so a ddck's value isn't necessarily
   the one that ran. The generated `.dck` is the source of truth: `executeTrnsys.py` marks overridden values with "value
   changed from original".
1. Solar loop: a primary pump (collector field) and a secondary pump (heat exchanger to storage), switched in
   `common/ddck/SolarControl/SolarActivation.ddck`. The primary pump runs above `GhiMin`, unless the over-temperature
   cut-off on `CollTOut` has stopped it: it stops above `TCollMax` (150 °C) and restarts only below `TCollMin` (130 °C).
   The secondary pump additionally needs a temperature difference and no stagnation (`Stagnation.ddck`: the storage top
   above `TTesMax`). Stagnation stops only the secondary pump.
1. Temperatures without flow aren't physical: Type 2221 (pumps and connections between components) picks the upstream
   temperature by flow direction, and without flow it outputs its own last value (confirmed in its source), possibly
   for years, while pipes (Type 931) cool down. Don't base control or analysis on them.
1. The pytrnsys GUI exports every connection that isn't simulated (`shallBeSimulated: false` in `[T|P|B]TES/*.json`, or
   a loop with `dummy-pipes`) as Type 2221. So a temperature that a controller monitors must come from a pipe or a
   component with capacity: in TTES, the collector inlet came from a Type 2221, and the over-temperature cut-off never
   released (https://github.com/resultes-net/issues/issues/57).
1. Loops with loop-wide defaults (the collector loops) are exported with the GUI's fixed defaults (`loopNLen`,
   `loopNDia`, `loopNUVal`). Their actual values are `deck` overrides in the run configs.
1. BTES's borehole field is TRNSYS Type 548 (TESS, a duct storage model; `BTES/ddck/BoHx/type548/`). Of its heat
   outputs, only these are energy flows:
   1. `BoHxQAve_kW`: the heat from the fluid into the field, per time step. It matches `BoHxQCalc_kW`, computed from
      mass flow and temperatures.
   1. `BoHxQLoss_kW`: the losses through the top, side and bottom. They're computed once per "global" time step (16–17 h
      in the variations checked so far) and reported in a single time step, zero in between.

   `BoHxQAccum_kW` is only an estimate: the change in the mean storage temperature times an approximate heat capacity.
   It matches `BoHxQAve_kW − BoHxQLoss_kW` only over the year, and is off by up to about 290 MWh in a single month. Use
   `BoHxQAve_kW − BoHxQLoss_kW` for the accumulation, as the system balance does.

## Post-processing
1. The runner runs `[T|P|B]TES/process.pytrnsys results` with the system's directory as working directory, so `common/` isn't
   on the module search path: shared code is imported via a `sys.path` insert (see `TTES/process.pytrnsys`).
1. All deck variables, including the constants from `parameters.ddck`, are in `sim.scalar`, without the `$` (e.g.
   `CollAcollAp`, `Vol_Tes1`).
1. `to_json` writes `sim.scalar` to `output.json` (`common/process/outputs.py`), which the client reads for the KPIs.
   Scalars for the client must be set in a processing step before `to_json`.
1. `output.json` has a version, `OutputsVersion` (`OUTPUTS_VERSION` in `common/process/outputs.py`; missing means 0), one for
   all three systems, so that the client can tell old results from new ones. If you add, rename or remove outputs the client
   reads, or change their meaning, bump it. The client (`create[T|P|B]tesKpis.ts`) may need changes: if you don't make
   them yourself, tell whoever works on the client, e.g. with an issue in https://github.com/resultes-net/issues.
1. Write the scalars for the client with their names spelled out (`sim.scalar["I_total"] = ...`), not in a loop over a
   dataclass's fields: the names are the interface to the client (`create[T|P|B]tesKpis.ts`), so they must be greppable
   in both repos.
1. The system energy balance plots (`balance/`) are drawn by `common/process/balance.py`, which fixes each quantity's
   color and label for all three systems (readable with red-green color blindness). A script only maps its
   columns to the quantities: add a new quantity there, rather than passing colors or legend labels in a script.
1. The three scripts contain a lot of duplicated code. Put new shared logic into `common/process/` (as `financial.py`) instead of
   copying it, as a step towards removing the duplication.

## Inspecting results
1. The variation's results zip in Swift (see the org-wide guide) holds the whole working directory, e.g.
   `TTES/results/complete-0/`: the generated `.dck`, the per-time-step printer files (`*_Mfr.prt`, `*_T.prt`), hourly
   printers in `temp/` (e.g. `STAGNATION_HR.Prt`) and `processing.log`.
1. Simulations cover several years (`time.stop`: so far 5 for TTES and BTES, 3 for PTES), but the processing (`last_year`
   in `process.pytrnsys`) cuts the hourly and monthly data to the last one: the KPIs, `output.json`, `hourly.csv` (TTES
   only) and the plots only cover that year. For the first years, use the `.prt` files.
1. The "solar" plots and the KPIs show `CollP_kW_calc` (mass flow × cp × ΔT through the field), the heat that actually
   flows into the system. Type 1357's own gain, `CollP_kW`, can differ completely from it, e.g. when there's no flow
   through the field.

## Running a simulation locally
To reproduce a simulation or test a change without pushing (every push to `main` deploys, see "Layout"), run the
runner's commands by hand:
1. Inputs: the create-variations job's working directory, `results/<simulation ID>.zip` in Swift's `resultes-results`
   (see the org-wide guide). Take `parameters.json` and `common/ddck/parameters/selected_weather/` from it (without
   `data_rolled_out.type99`, which is generated), and everything else from the `systems` checkout to test. Parameters
   can be changed in `parameters.json`, e.g. `parameters.values.collector_field.area`.
1. Python: the runner's Windows venv (see "Environment and tests"). Its `pydantic-models` must match the parameters'
   format, otherwise the scripts fail, e.g. with `'TtesParameters' object has no attribute 'financial'`: set
   `PYTHONPATH` to an up-to-date checkout, as described there.
1. TRNSYS: the runners' one. Unpack `create-disk-image/contents/TRNSYS18_resultes.zip` from the `runner` repo and run
   its `Exe\TrnEXE.exe`. A standard TRNSYS installation lacks our modified Types, e.g. Type 1357, and the decks fail at
   time 0 ("19 INPUTS are required and 20 INPUTS were specified").
1. The commands, as the scheduler sends them to the runner (`scheduler/src/scheduler/runner/client.py`):
   1. In the working directory: `python common/create_common_parameters_ddck_file.py parameters.json`, then
      `python <SYSTEM>/create_parameters_ddck_file.py parameters.json`.
   1. In `<SYSTEM>/`: `python run.pytrnsys`, which generates `results/complete-0/complete-0.dck`.
   1. In `<SYSTEM>/results/complete-0/`: `TrnEXE.exe complete-0.dck /N`.
   1. In `<SYSTEM>/`: `python process.pytrnsys results`.
1. A 5-year run takes tens of minutes: run it in the background. Several runs can run in parallel, each in its own
   working directory.

## Parameters and weather data
1. `common/create_common_parameters_ddck_file.py <parameters-json>` generates the per-simulation inputs into
   `common/ddck/parameters/`: `parameters.ddck`, `demand.csv`, the waste-heat source profile and `weather_data.ddck`.
   Its tests are in `common/test_create_common_parameters_ddck_file.py` (they use temporary directories).
1. The simulation has a `weather_data_id` (no longer a `location`). Before the script runs, the runner downloads the
   selected weather data into `common/ddck/parameters/selected_weather/` (`DIR_NAME` in
   `resultes_pydantic_models.weather_data`): the data file (`get_data_file_name`: `data.csv` for ISO, `data.tm2` for
   TM2) and a `README.md` (don't delete or overwrite it). The script tells the format by which data file exists.
1. It copies the matching ddck from `common/ddck/weather/` (`weather_data_iso.ddck` or `weather_data_tm2.ddck`) to
   `common/ddck/parameters/weather_data.ddck`, so the run configs include `COMMON$ parameters\weather_data`.
1. ISO: the data is rolled out over 10 years into `selected_weather/data_rolled_out.type99` (read via Type 99). The
   location (longitude, standard longitude, latitude) for its header comes from `LOCATION_PARAMETERS`, keyed by weather
   data ID (the shared ISO data's IDs, hard-coded in the server's migrations).
1. TM2: no roll-out (`weather_data_tm2.ddck` reads the file itself, via Type 109); the statistics and the site
   elevation (`$altid`, for Type 69's sky temperature) are read with `pvlib.iotools.read_tmy2`. `pvlib` rejects raw
   Meteonorm files, but the server fixes them up on upload (`fix_up_and_validate_tm2_contents`), so the downloaded file
   is fine.
1. Statistics (yearly average, amplitude, first coldest day) go into `parameters.ddck` in both cases.
1. Long-wave radiation: the collector (Type 1357, modified by us) gets `$LgwRadMode` from `parameters.ddck`: 5 for ISO
   (takes `EL` from the data; undocumented, our addition), 2 for TM2 (computes it from `Tsky`, `EmSky` and `EmGnd`). Both
   weather ddcks define all four variables; the ones the mode doesn't use are explicit placeholders.
1. `common/ddck/weather/` holds the ddcks and the shared weather data: one CSV per ISO reference climate (`Alpine.csv`,
   `Cold.csv`, ...) and `CH-Zuerich-Kloten-66700.tm2` (TMY2, Zurich). The runner doesn't read them from here anymore
   (it downloads the selected data), but keep them: all shared weather data are kept in the repo, so that users who
   download a project have them. Don't write code for switching to other weather data.
1. `weather_data_iso.ddck` and `weather_data_tm2.ddck` are maintained by hand.
