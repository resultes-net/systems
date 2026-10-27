"""The system energy balance: a fixed color and label for each quantity, and the monthly and
yearly balance plots.

Shared by the systems' post-processing scripts (`[T|P|B]TES/process.pytrnsys`), so that a
quantity looks the same in every system, whatever other quantities a system has. The colors are
from the Okabe-Ito palette, which people with red-green color blindness can tell apart, plus
greys. A storage's losses are a pale tint of its accumulation's color: they differ in lightness,
which every kind of color blindness keeps. Check new colors with a color blindness simulator.
"""

import collections.abc as _cabc
import dataclasses as _dc
import typing as _tp

import matplotlib.axes as _mpla
import matplotlib.figure as _mplf
import pandas as _pd
from pytrnsys_process import api as _api

_YELLOW = "#F0E442"
_BLUE = "#0072B2"
_VERMILLION = "#D55E00"
_REDDISH_PURPLE = "#CC79A7"
_BLUISH_GREEN = "#009E73"
_SKY_BLUE = "#56B4E9"
_PALE_SKY_BLUE = "#BBE1F6"
_ORANGE = "#E69F00"
_PALE_ORANGE = "#F5D58C"
_MID_GREY = "#999999"
_DARK_GREY = "#666666"
_BLACK = "#000000"


@_dc.dataclass(frozen=True)
class Quantity:
    label: str
    color: str
    # Inputs are drawn above zero, outputs below.
    is_input: bool


SOLAR = Quantity("Solar collectors", _YELLOW, is_input=True)
COMPRESSOR = Quantity("Heat pump compressor", _BLUE, is_input=True)
BOILER = Quantity("Boiler", _VERMILLION, is_input=True)
WASTE_HEAT = Quantity("Waste heat source", _REDDISH_PURPLE, is_input=True)
DEMAND = Quantity("Demand", _BLUISH_GREEN, is_input=False)
# The seasonal storage (TTES, PTES, BTES).
STORAGE_ACCUMULATION = Quantity("Storage: accumulation", _SKY_BLUE, is_input=False)
STORAGE_LOSSES = Quantity("Storage: losses", _PALE_SKY_BLUE, is_input=False)
BUFFER_TANK_ACCUMULATION = Quantity(
    "Buffer tank: accumulation", _ORANGE, is_input=False
)
BUFFER_TANK_LOSSES = Quantity("Buffer tank: losses", _PALE_ORANGE, is_input=False)
SOLAR_LOOP_PIPE_LOSSES = Quantity("Solar loop pipe losses", _MID_GREY, is_input=False)
DISTRICT_HEATING_LOSSES = Quantity(
    "District heating losses", _DARK_GREY, is_input=False
)
# Computed from the others, not passed in.
IMBALANCE = Quantity("Imbalance", _BLACK, is_input=False)

# The order in which the quantities are stacked, from zero outwards.
QUANTITIES = (
    SOLAR,
    COMPRESSOR,
    BOILER,
    WASTE_HEAT,
    DEMAND,
    STORAGE_ACCUMULATION,
    STORAGE_LOSSES,
    BUFFER_TANK_ACCUMULATION,
    BUFFER_TANK_LOSSES,
    SOLAR_LOOP_PIPE_LOSSES,
    DISTRICT_HEATING_LOSSES,
)

_GWH_PER_KWH = 1e-6


class Simulation(_tp.Protocol):
    """The parts of `pytrnsys_process.api.Simulation` used here."""

    monthly: _pd.DataFrame
    path: str


def plot_system_balance(
    sim: Simulation, columns_by_quantity: _cabc.Mapping[Quantity, str]
) -> None:
    """Draws the monthly and the yearly system balance into `<sim.path>/balance/`.

    `columns_by_quantity` maps each of the system's quantities to its column in `sim.monthly`
    (in kWh). The imbalance is computed from the others.
    """
    monthly_GWh = get_monthly_balance_GWh(sim.monthly, columns_by_quantity)

    fig, _ = plot_balance(monthly_GWh)
    _api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "balance")

    yearly_GWh = monthly_GWh.sum().to_frame().T
    yearly_GWh.index = monthly_GWh.index[:1]
    fig, ax = plot_balance(yearly_GWh)
    ax.set_xticklabels([f"{monthly_GWh.index[0].year}"], rotation=0)
    _api.export_plots_in_configured_formats(fig, sim.path, "balance-yearly", "balance")


def get_monthly_balance_GWh(
    monthly_kWh: _pd.DataFrame, columns_by_quantity: _cabc.Mapping[Quantity, str]
) -> _pd.DataFrame:
    """The quantities' columns in GWh, named by their labels, in the order of `QUANTITIES`."""
    unknown_quantities = set(columns_by_quantity) - set(QUANTITIES)
    if unknown_quantities:
        labels = sorted(q.label for q in unknown_quantities)
        raise ValueError(f"Not a quantity of the system balance: {labels}")

    missing_columns = set(columns_by_quantity.values()) - set(monthly_kWh.columns)
    if missing_columns:
        raise ValueError(f"No such columns: {sorted(missing_columns)}")

    return _pd.DataFrame(
        {
            q.label: monthly_kWh[columns_by_quantity[q]] * _GWH_PER_KWH
            for q in QUANTITIES
            if q in columns_by_quantity
        },
        index=monthly_kWh.index,
    )


def plot_balance(
    balance_GWh: _pd.DataFrame,
) -> tuple[_mplf.Figure, _mpla.Axes]:
    """Draws the columns of `get_monthly_balance_GWh` (or of its sum) as a stacked bar chart."""
    quantities = [q for q in QUANTITIES if q.label in balance_GWh.columns]
    inputs = [q for q in quantities if q.is_input]
    outputs = [q for q in quantities if not q.is_input]
    plotted = [*inputs, *outputs, IMBALANCE]

    fig, ax = _api.energy_balance(
        balance_GWh,
        q_in_columns=[q.label for q in inputs],
        q_out_columns=[q.label for q in outputs],
        use_legend=False,
        xlabel="",
        ylabel="Energy [GWh]",
        # Otherwise `energy_balance` adds its default colormap, which pandas ignores, with a
        # warning, when colors are given.
        cmap=None,
        color=[q.color for q in plotted],
        # Separates neighboring segments of similar colors.
        edgecolor="white",
        linewidth=0.5,
    )

    # The inputs are stacked upwards, so they're listed in reverse to read like the bars.
    legend_quantities = [*reversed(inputs), *outputs, IMBALANCE]
    handles_by_quantity = dict(zip(plotted, ax.containers, strict=True))
    ax.legend(
        [handles_by_quantity[q] for q in legend_quantities],
        [q.label for q in legend_quantities],
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
    )

    return fig, ax
