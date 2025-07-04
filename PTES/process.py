import pathlib as _pl
import matplotlib.pyplot as _plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api

def solar(sim: api.Simulation):

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

def ptes(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["pitStoreQLosses_kW_Tot"] = sim.hourly["pitStoreQLosses_kW"].sum()
    sim.scalar["pitStoreQ13_kW_Tot"] = sim.hourly["pitStoreQ13_kW"].sum()
    sim.scalar["pitStoreQ23_kW_Tot"] = sim.hourly["pitStoreQ23_kW"].sum()
    sim.scalar["pitStoreQ31_kW_Tot"] = sim.hourly["pitStoreQ31_kW"].sum()
    sim.scalar["pitStoreQAccum_kW_Tot"] = sim.hourly["pitStoreQAccum_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["pitStoreTTherStat1", "pitStoreTTherStat2", "pitStoreTTherStat3"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "t-ptes-hourly", "ptes")






def hp(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["HPQEvap_kW_Tot"] = sim.hourly["HPQEvap_kW"].sum()
    sim.scalar["HPQCond_kW_Tot"] = sim.hourly["HPQCond_kW"].sum()
    sim.scalar["HPPelComp_kW_Tot"] = sim.hourly["HPPelComp_kW"].sum()
    sim.scalar["HPCOP"] = sim.scalar["HPQCond_kW_Tot"] / sim.scalar["HPPelComp_kW_Tot"]

    #### Q vs T ####
    plot_variables = [
        ["HPQEvap_kW", "HPTEvapOut"],
        ["HPQCond_kW", "HPTCondOut"],

    ]

    dataframes = []

    _plt.figure()

    for q, t in plot_variables:
        a = sim.hourly[q]
        b = sim.hourly[t]
        df = pd.DataFrame({q: a, t: b})

        df = df.sort_values(by=t)
        df[q] = np.cumsum(df[q])
        dataframes.append(df)

        fig = _plt.plot(df[t], df[q], label=q+"____"+t)  # , linestyle='-', color='blue', label='Q_cum')

    #     _plt.ion()
    #
    #
    # _plt.ioff()  # Desactivar modo interactivo
    _plt.xlabel('Temperature [°C]')
    _plt.ylabel('Cumulative energy [kWh]')
    _plt.grid()
    _plt.legend()
    # _plt.show()
    api.export_plots_in_configured_formats(fig[0].figure, sim.path, "q_t", "hp")



def boiler(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["BolrPOut_kW_Tot"] = sim.hourly["BolrPOut_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["BolrPOut_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "boiler-hourly", "boiler")

def source(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["QSrcP_kW_Tot"] = sim.hourly["QSrcP_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["QSrcP_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "source-hourly", "source")

def sink(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["QSnkP_kW_Tot"] = sim.hourly["QSnkP_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["QSnkP_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "sink-hourly", "sink")

def balance(sim: api.Simulation):


    #### Calculations ####
    sim.scalar["QSources"] = sim.scalar["CollP_kW_HO_Tot"] + sim.scalar["BolrPOut_kW_Tot"] + sim.scalar["QSrcP_kW_Tot"] + sim.scalar["HPPelComp_kW_Tot"]
    sim.scalar["QSinks"] = sim.scalar["QSnkP_kW_Tot"]
    sim.scalar["QStore"] = sim.scalar["pitStoreQAccum_kW_Tot"]
    sim.scalar["QLosses"] = sim.scalar["pitStoreQLosses_kW_Tot"]

    sim.scalar["QImb"] = sim.scalar["QSources"] - sim.scalar["QStore"] - sim.scalar["QSinks"] - sim.scalar["QLosses"]

def kpi(sim: api.Simulation):


    #### Calculations ####
    sim.scalar["FactorRenewable"] = (sim.scalar["QSnkP_kW_Tot"] - sim.scalar["BolrPOut_kW_Tot"]) / sim.scalar["QSnkP_kW_Tot"]
    5

def to_json(sim: api.Simulation):
    sim.scalar.to_json(sim.path + "\output.json", orient="records", indent=4)
    
if __name__ == "__main__":
    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\PTES\results")
    api.global_settings.reader.force_reread_prt = True
    api.global_settings.reader.read_step_files = False

    processing_steps = [
                        solar,
                        ptes,
                        hp,
                        boiler,
                        source,
                        sink,
                        balance,
                        kpi,
                        to_json,
                        ]

    simulation_data = api.process_whole_result_set(
        path_to_sim,
        processing_steps,
    )