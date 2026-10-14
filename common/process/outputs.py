"""The post-processing's scalar outputs, `output.json`, which the client reads for the KPIs.

Shared by the systems' post-processing scripts (`[T|P|B]TES/process.pytrnsys`).
"""

import pathlib as _pl
import typing as _tp

if _tp.TYPE_CHECKING:
    import pandas as _pd

# The version of the outputs, written into `output.json` as `OutputsVersion`, so that the
# client can tell results processed by different versions of the post-processing apart.
# Results without it are version 0. One version for all three systems.
#
# If you add, rename or remove outputs the client reads, or change their meaning, bump
# `OUTPUTS_VERSION`. The client (`create[T|P|B]tesKpis.ts`) may need changes: if you don't
# make them yourself, tell whoever works on the client, e.g. with an issue in
# https://github.com/resultes-net/issues.
OUTPUTS_VERSION = 1

FILE_NAME = "output.json"


class Simulation(_tp.Protocol):
    """The parts of `pytrnsys_process.api.Simulation` used here."""

    scalar: "_pd.DataFrame"
    path: str


def write_output_json(sim: Simulation) -> None:
    """Writes `sim.scalar` and `OutputsVersion` to `<sim.path>/output.json`, as an array with
    one record. `OutputsVersion` describes the file, not the simulation, so it isn't added to
    `sim.scalar`."""
    scalar = sim.scalar.assign(OutputsVersion=OUTPUTS_VERSION)
    scalar.to_json(_pl.Path(sim.path) / FILE_NAME, orient="records", indent=4)
