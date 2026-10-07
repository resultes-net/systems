import pathlib as _pl
from pytrnsys_process import api


def _set_legend(ax, title, loc):
    # rebuild the legend placed by scalar_compare_plot, which sticks to the axes corner
    old = ax.get_legend()
    labels = [t.get_text() for t in old.get_texts()]
    fontsize = old.get_texts()[0].get_fontsize()
    ax.legend(old.legend_handles, labels, title=title, loc=loc, borderaxespad=1.5, fontsize=fontsize)


def relative_to_demand(sims_data: api.SimulationsData):
    # size collector and TES relative to the simulated annual heat demand (MWh/a)
    df = sims_data.scalar
    demand_MWh = df["QSnkP_kW_Tot"] / 1000
    df["CollAcollAp_per_MWh"] = (df["CollAcollAp"] / demand_MWh).round(2)
    df["Vol_Tes1_per_MWh"] = (df["Vol_Tes1"] / demand_MWh).round(2)


def compare_lcoh(sims_data: api.SimulationsData):

    # LCOH vs specific TES volume, grouped by specific collector area
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "Vol_Tes1_per_MWh",
        "LCOH",
        group_by_color="CollAcollAp_per_MWh"
    )

    for line in ax.get_lines():
        line.set_marker("o")
    _set_legend(ax, "$A_{coll}/Q_{dem}~[m^2/(MWh)]$", "upper left")
    ax.grid(True)
    ax.set_xlabel('$V_{TTES}/Q_{dem}~[m^3/(MWh)]$')
    ax.set_ylabel('$LCOE~[€/kWh]$')
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe_vs_volume", "../comparison")

    # LCOH vs specific collector area, grouped by specific TES volume
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "CollAcollAp_per_MWh",
        "LCOH",
        group_by_color="Vol_Tes1_per_MWh"
    )

    for line in ax.get_lines():
        line.set_marker("o")
    _set_legend(ax, "$V_{TTES}/Q_{dem}~[m^3/MWh]$", "upper right")
    ax.grid(True)
    ax.set_xlabel('$A_{coll}/Q_{dem}~[m^2/MWh]$')
    ax.set_ylabel('$LCOE~[€/kWh]$')
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe_vs_area", "../comparison")


if __name__ == "__main__":

    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\TTES\results_parametric")
    api.global_settings.reader.force_reread_prt = False
    comparison_steps = [
                        relative_to_demand,
                        compare_lcoh,
    ]
    api.do_comparison(comparison_steps, results_folder=path_to_sim)
