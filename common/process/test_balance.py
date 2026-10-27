import dataclasses as _dc
import pathlib as _pl

import matplotlib.colors as _mplc
import matplotlib.pyplot as _plt
import pandas as _pd
import pytest as _pt
from pytrnsys_process import api as _api

from . import balance as _balance

_COLUMNS_BY_QUANTITY = {
    _balance.SOLAR: "CollP_kW_calc",
    _balance.COMPRESSOR: "HpPelComp_kW",
    _balance.BOILER: "BolrPOut_kW",
    _balance.DEMAND: "QSnkP_kW",
    _balance.STORAGE_ACCUMULATION: "QAcum_Tes1",
    _balance.STORAGE_LOSSES: "QLoss_Tes1",
}


def _create_monthly_kWh() -> _pd.DataFrame:
    index = _pd.date_range("2028-01-01", periods=12, freq="MS")
    return _pd.DataFrame(
        {
            "CollP_kW_calc": 2e6,
            "HpPelComp_kW": 0.5e6,
            "BolrPOut_kW": 1e6,
            "QSnkP_kW": 3e6,
            "QAcum_Tes1": 0.25e6,
            "QLoss_Tes1": 0.2e6,
            "Unused": 1.0,
        },
        index=index,
    )


@_dc.dataclass
class _Simulation:
    monthly: _pd.DataFrame
    path: str


def test_quantities_have_distinct_colors_and_labels() -> None:
    quantities = [*_balance.QUANTITIES, _balance.IMBALANCE]
    colors = {q.color.lower() for q in quantities}
    labels = {q.label for q in quantities}
    assert len(colors) == len(quantities)
    assert len(labels) == len(quantities)


def test_get_monthly_balance_GWh() -> None:
    balance_GWh = _balance.get_monthly_balance_GWh(
        _create_monthly_kWh(), _COLUMNS_BY_QUANTITY
    )

    assert list(balance_GWh.columns) == [
        "Solar collectors",
        "Heat pump compressor",
        "Boiler",
        "Demand",
        "Storage: accumulation",
        "Storage: losses",
    ]
    assert balance_GWh["Solar collectors"].tolist() == _pt.approx([2.0] * 12)
    assert balance_GWh["Storage: losses"].tolist() == _pt.approx([0.2] * 12)


def test_get_monthly_balance_GWh_order_doesnt_depend_on_mapping() -> None:
    reversed_mapping = dict(reversed(_COLUMNS_BY_QUANTITY.items()))
    monthly_kWh = _create_monthly_kWh()

    _pd.testing.assert_frame_equal(
        _balance.get_monthly_balance_GWh(monthly_kWh, reversed_mapping),
        _balance.get_monthly_balance_GWh(monthly_kWh, _COLUMNS_BY_QUANTITY),
    )


def test_get_monthly_balance_GWh_rejects_unknown_quantities_and_columns() -> None:
    monthly_kWh = _create_monthly_kWh()

    with _pt.raises(ValueError, match="Imbalance"):
        _balance.get_monthly_balance_GWh(monthly_kWh, {_balance.IMBALANCE: "Unused"})

    with _pt.raises(ValueError, match="NoSuchColumn"):
        _balance.get_monthly_balance_GWh(monthly_kWh, {_balance.SOLAR: "NoSuchColumn"})


@_pt.mark.parametrize(
    "columns_by_quantity",
    [
        _COLUMNS_BY_QUANTITY,
        # Another system: without the compressor, with a waste heat source.
        {
            _balance.WASTE_HEAT: "HpPelComp_kW",
            _balance.STORAGE_LOSSES: "QLoss_Tes1",
            _balance.SOLAR: "CollP_kW_calc",
            _balance.DEMAND: "QSnkP_kW",
        },
    ],
)
def test_plot_balance_colors_and_labels_dont_depend_on_position(
    columns_by_quantity: dict[_balance.Quantity, str],
) -> None:
    balance_GWh = _balance.get_monthly_balance_GWh(
        _create_monthly_kWh(), columns_by_quantity
    )

    _, ax = _balance.plot_balance(balance_GWh)

    legend = ax.get_legend()
    labels = [text.get_text() for text in legend.get_texts()]
    quantities_by_label = {
        q.label: q for q in [*_balance.QUANTITIES, _balance.IMBALANCE]
    }
    for label, handle in zip(labels, legend.legend_handles, strict=True):
        quantity = quantities_by_label[label]
        assert _mplc.to_hex(handle.get_facecolor()) == quantity.color.lower()

    assert sorted(labels) == sorted(
        [*(q.label for q in columns_by_quantity), _balance.IMBALANCE.label]
    )
    _plt.close("all")


def test_plot_balance_legend_reads_like_the_bars() -> None:
    balance_GWh = _balance.get_monthly_balance_GWh(
        _create_monthly_kWh(), _COLUMNS_BY_QUANTITY
    )

    _, ax = _balance.plot_balance(balance_GWh)

    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    assert labels == [
        "Boiler",
        "Heat pump compressor",
        "Solar collectors",
        "Demand",
        "Storage: accumulation",
        "Storage: losses",
        "Imbalance",
    ]
    _plt.close("all")


def test_plot_system_balance_writes_monthly_and_yearly_plots(
    tmp_path: _pl.Path, monkeypatch: _pt.MonkeyPatch
) -> None:
    # EMF needs Inkscape.
    monkeypatch.setattr(_api.global_settings.plot, "file_formats", [".png"])
    sim = _Simulation(monthly=_create_monthly_kWh(), path=str(tmp_path))

    _balance.plot_system_balance(sim, _COLUMNS_BY_QUANTITY)

    written = {p.name for p in (tmp_path / "balance").iterdir()}
    assert "balance-monthly-A4.png" in written
    assert "balance-yearly-A4.png" in written
    _plt.close("all")
