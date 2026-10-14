import dataclasses as _dc
import json as _json
import pathlib as _pl

import pandas as _pd

from . import outputs as _outputs


@_dc.dataclass
class _Simulation:
    scalar: _pd.DataFrame
    path: str


def test_write_output_json(tmp_path: _pl.Path) -> None:
    scalar = _pd.DataFrame([{"LCOH": 0.1, "I_total": 1e6}])
    sim = _Simulation(scalar.copy(), str(tmp_path))

    _outputs.write_output_json(sim)

    records = _json.loads((tmp_path / "output.json").read_text())
    assert records == [
        {"LCOH": 0.1, "I_total": 1e6, "OutputsVersion": _outputs.OUTPUTS_VERSION}
    ]
    assert _outputs.OUTPUTS_VERSION >= 1

    # The version describes the file, not the simulation.
    _pd.testing.assert_frame_equal(sim.scalar, scalar)
