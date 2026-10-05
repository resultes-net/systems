import pathlib as _pl
from pytrnsys_process import api


def _set_legend(ax, title, loc):
    # rebuild the legend placed by scalar_compare_plot, which sticks to the axes corner
    old = ax.get_legend()
    labels = [t.get_text() for t in old.get_texts()]
    fontsize = old.get_texts()[0].get_fontsize()
    ax.legend(old.legend_handles, labels, title=title, loc=loc, borderaxespad=1.5, fontsize=fontsize)


def compare_lcoh(sims_data: api.SimulationsData):

    # LCOH vs TES volume, grouped by collector area
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "Vol_Tes1",
        "LCOH",
        group_by_color="CollAcollAp"
    )

    for line in ax.get_lines():
        line.set_marker("o")
    _set_legend(ax, "$A_{coll}~[m^2]$", "upper left")
    ax.grid(True)
    ax.set_xlabel('$V_{TTES}~[m^3]$')
    ax.set_ylabel('$LCOE~[€/kWh]$')
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe_vs_volume", "../comparison")

    # LCOH vs collector area, grouped by TES volume
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "CollAcollAp",
        "LCOH",
        group_by_color="Vol_Tes1"
    )

    for line in ax.get_lines():
        line.set_marker("o")
    _set_legend(ax, "$V_{TTES}~[m^3]$", "upper right")
    ax.grid(True)
    ax.set_xlabel('$A_{coll}~[m^2]$')
    ax.set_ylabel('$LCOE~[€/kWh]$')
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe_vs_area", "../comparison")


if __name__ == "__main__":

    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\TTES\results_parametric")
    api.global_settings.reader.force_reread_prt = False
    comparison_steps = [
                        compare_lcoh,
    ]
    api.do_comparison(comparison_steps, results_folder=path_to_sim)
