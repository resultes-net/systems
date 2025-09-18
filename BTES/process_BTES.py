import pathlib as _pl
import matplotlib.pyplot as _plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api

import sys
import os
dir_project = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
dir_common = carpeta_a_path = os.path.join(dir_project, 'common')
sys.path.append(dir_common)


def solar(sim: api.Simulation):

    #### Calculations ####
    sim.monthly["CollP_MW"] = sim.monthly["CollP_kW"] / 1000

    sim.scalar["CollP_kW_Tot"] = sim.hourly["CollP_kW"].sum()
    sim.scalar["qSysOut_PipeLoss_Tot"] = sim.hourly["qSysOut_PipeLoss"].sum()

    # sim.scalar["HxCollHpPhxload_kW_Tot"] = sim.hourly["HxCollHpPhxload_kW"].sum()
    # sim.scalar["HxCollDemandPhxload_kW_Tot"] = sim.hourly["HxCollDemandPhxload_kW"].sum()


    df = pd.DataFrame({
        'T': sim.hourly["CollTOut"],
        'Q':  sim.hourly["CollP_kW"] / 1000
    })

    df = df.sort_values(by="T")
    df["Q_cum"] = np.cumsum(df["Q"])


    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["CollP_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "solar-hourly", "solar")

    fig, ax = api.bar_chart(sim.monthly, ["CollP_kW"])
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

def tes(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["TesQAcum_Tes1_Tot"] = sim.monthly["TesQAcum_Tes1"].sum()
    sim.scalar["TesQLoss_Tes1_Tot"] = sim.monthly["TesQLoss_Tes1"].sum()

    #### Q vs T ####
    df = pd.DataFrame({
        'T': sim.hourly["TTesDpR10_95"],
        'Q': -sim.hourly["TesQdp2_Tes1"] / 1000
    })

    df = df.sort_values(by="T")
    df["Q_cum"] = np.cumsum(df["Q"])


    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["TesT1_Tes1", "TesT2_Tes1", "TesT3_Tes1", "TesT4_Tes1",
                                         "TesT5_Tes1", "TesT6_Tes1", "TesT7_Tes1", "TesT8_Tes1",
                                         "TesT9_Tes1", "TesT10_Tes1"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "tes-temps", "tes")

    _plt.figure()
    fig = _plt.plot(df["T"], df["Q_cum"]) #, linestyle='-', color='blue', label='Q_cum')
    _plt.xlabel('$T_{dem}$ [°C]')
    _plt.ylabel('$Q_{coll}$ [MWh]')
    _plt.tight_layout()
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig[0].figure, sim.path, "q_t", "tes")

def btes(sim: api.Simulation):

    #### Calculations ####
    sim.hourly["BoHxQChar_kW"] = abs(sim.hourly["BoHxQ_kW"]) * sim.hourly["ControlBorOnChar"]
    sim.hourly["BoHxQDischar_kW"] = abs(sim.hourly["BoHxQ_kW"]) * sim.hourly["ControlBorOnDischar"]

    # ENERGY DENSITY
    cp = sim.scalar["BoHxCpGround"]
    rho = sim.scalar["BoHxrhoGround"]
    sim.scalar["rhoQ"] = (max(sim.hourly["BoHxTAvg"]) - min(sim.hourly["BoHxTAvg"])) * rho * cp/3600

    sim.scalar["BoHxQChar_kW_Tot"] = sim.hourly["BoHxQChar_kW"].sum()
    sim.scalar["BoHxQDischar_kW_Tot"] = sim.hourly["BoHxQDischar_kW"].sum()


    # sim.scalar["pitStoreQLosses_kW_Tot"] = sim.hourly["pitStoreQLosses_kW"].sum()
    sim.scalar["BoHxQ_kW_Tot"] = sim.hourly["BoHxQ_kW"].sum()
    # sim.scalar["pitStoreQ23_kW_Tot"] = sim.hourly["pitStoreQ23_kW"].sum()
    # sim.scalar["pitStoreQ31_kW_Tot"] = sim.hourly["pitStoreQ31_kW"].sum()
    # sim.scalar["pitStoreQAccum_kW_Tot"] = sim.hourly["pitStoreQAccum_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["BoHxT13", "BoHxT23", "BoHxT33",
                                         "BoHxT43", "BoHxT53", "BoHxT63", "BoHxTGro3"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "t-btes-hourly", "btes")

    fig, ax = api.line_plot(sim.hourly, ["BoHxTAvg"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "t-avg-hourly", "btes")

    fig, ax = api.line_plot(sim.hourly, ["BoHxTRT"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "trt-hourly", "btes")

    fig, ax = api.line_plot(sim.hourly, ["BoHxQ_kW"])
    ax.set_ylabel("Heat (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "q-hourly", "btes")

def hp(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["HpQEvap_kW_Tot"] = sim.hourly["HpQEvap_kW"].sum()
    sim.scalar["HpQCond_kW_Tot"] = sim.hourly["HpQCond_kW"].sum()
    sim.scalar["HpPelComp_kW_Tot"] = sim.hourly["HpPelComp_kW"].sum()
    sim.scalar["HpCOP"] = sim.scalar["HpQCond_kW_Tot"] / sim.scalar["HpPelComp_kW_Tot"]

    #### Q vs T ####
    plot_variables = [
        ["HpQEvap_kW", "HpTEvapOut"],
        ["HpQCond_kW", "HpTCondOut"],

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

    # fig, ax = api.line_plot(sim.hourly, ["HpmyIsOn"])
    # ax.set_ylabel("HP activation (-)")
    # _plt.grid()
    # # _plt.show()
    # api.export_plots_in_configured_formats(fig, sim.path, "act-hourly", "hp")

def hx(sim: api.Simulation):

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["HxQ_kW"])
    ax.set_ylabel("Heat (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "q-hourly", "hx")

    fig, ax = api.line_plot(sim.hourly, ["HxEff"])
    ax.set_ylabel("Efficiency (-)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "efficiency-hourly", "hx")

    fig, ax = api.line_plot(sim.hourly, ["HxLMTD"])
    ax.set_ylabel("LMTD (K)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "LMTD-hourly", "hx")

def boiler(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["BolrPOut_kW_Tot"] = sim.hourly["BolrPOut_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["BolrPOut_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "boiler-hourly", "boiler")

def sink(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["QSnkP_kW_Tot"] = sim.hourly["QSnkP_kW"].sum()
    # sim.scalar["QSnkPout_kW_Tot"] = sim.hourly["QSnkPout_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["QSnkP_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "sink-hourly", "sink")

def control(sim: api.Simulation):
    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["ControlBorOnChar", "ControlBorOnDischar"])
    ax.set_ylabel("Activation (-)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "mode-hourly", "control")

def balance(sim: api.Simulation):


    #### Calculations ####
    sim.scalar["QSources"] = sim.scalar["CollP_kW_Tot"] + sim.scalar["BolrPOut_kW_Tot"]  + sim.scalar["HpPelComp_kW_Tot"]
    sim.scalar["QSinks"] = sim.scalar["QSnkP_kW_Tot"]
    sim.scalar["QStore"] = -sim.scalar["BoHxQ_kW_Tot"] + sim.scalar["TesQAcum_Tes1_Tot"]
    sim.scalar["QLosses"] = sim.scalar["TesQLoss_Tes1_Tot"] + sim.scalar["qSysOut_PipeLoss_Tot"]

    sim.scalar["QImb"] = sim.scalar["QSources"] - sim.scalar["QStore"] - sim.scalar["QSinks"] - sim.scalar["QLosses"]

    #### Plots ####
    names_legend = ['$Q_{Coll}$','$P_{Comp}$','$Q_{Boiler}$','$Q_{BTES,Accum}$',
                    '$Q_{Demand}$','$Q_{TES,Accum}$','$Q_{TES,Losses}$','$Q_{District}$']

    fig, ax = api.energy_balance(
        sim.monthly,
        q_in_columns=["CollP_kW_calc", "HpPelComp_kW", "BolrPOut_kW", "BoHxQ_kW"],
        q_out_columns=["QSnkP_kW", "TesQAcum_Tes1", "TesQLoss_Tes1", "qSysOut_dpToFFieldTot"], #, "qSysOut_dpPipeIntTot", "qSysOut_dpSoilIntTot"],
        xlabel="",
        cmap="Paired"
    )
    _plt.legend(names_legend, bbox_to_anchor=(1.05, 1), loc='upper left')
    api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "balance")




def kpi(sim: api.Simulation):


    #### Calculations ####
    sim.scalar["FactorRenewable"] = (sim.scalar["QSnkP_kW_Tot"] - sim.scalar["BolrPOut_kW_Tot"]) / sim.scalar["QSnkP_kW_Tot"]
    5

def to_json(sim: api.Simulation):
    sim.scalar.to_json(sim.path + "\output.json", orient="records", indent=4)
    
if __name__ == "__main__":
    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\BTES\results")
    api.global_settings.reader.force_reread_prt = False
    api.global_settings.reader.read_step_files = False

    processing_steps = [
                        solar,
                        hx,
                        tes,
                        btes,
                        hp,
                        boiler,
                        sink,
                        control,
                        balance,
                        kpi,
                        to_json,
                        ]

    simulation_data = api.process_whole_result_set(
        path_to_sim,
        processing_steps,
    )