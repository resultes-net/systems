import pathlib as _pl
import matplotlib.pyplot as _plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api

def solar(sim):

    #### Calculations ####
    sim.monthly["CollP_MW_MO"] = sim.monthly["CollP_kW_MO"] / 1000

    sim.scalar["CollP_kW_HO_Tot"] = sim.hourly["CollP_kW_HO"].sum()

    # sim.scalar["HxCollHpPhxload_kW_Tot"] = sim.hourly["HxCollHpPhxload_kW"].sum()
    # sim.scalar["HxCollDemandPhxload_kW_Tot"] = sim.hourly["HxCollDemandPhxload_kW"].sum()


    df = pd.DataFrame({
        'T': sim.hourly["CollTOut"],
        'Q':  sim.hourly["CollP_kW_HO"] / 1000
    })

    df = df.sort_values(by="T")
    df["Q_cum"] = np.cumsum(df["Q"])


    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["CollP_kW_HO"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "solar-hourly", "solar")

    fig, ax = api.bar_chart(sim.monthly, ["CollP_kW_MO"])
    ax.set_ylabel("Power (kW)")
    ax.legend()
    ax.legend_ = None
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "solar-monthly", "solar")

    fig, ax = api.line_plot(sim.hourly, ["CollTIn", "CollTOut"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()

    _plt.figure()
    fig = _plt.plot(df["T"], df["Q_cum"]) #, linestyle='-', color='blue', label='Q_cum')
    _plt.xlabel('$T_{coll,out}$ [°C]')
    _plt.ylabel('$Q_{coll,cum}$ [MWh]')
    _plt.tight_layout()
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig[0].figure, sim.path, "q_t", "solar")