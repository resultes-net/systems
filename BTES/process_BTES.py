import pathlib as _pl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api

import sys
import os

dir_project = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
dir_common = carpeta_a_path = os.path.join(dir_project, 'common')
sys.path.append(dir_common)


def filter(sim: api.Simulation):
    sim.monthly.index = pd.to_datetime(sim.monthly.index)

    last_year = sim.monthly.index.year[-1]

    sim.monthly = sim.monthly[sim.monthly.index.year == last_year]

    sim.hourly.index = pd.to_datetime(sim.hourly.index)
    sim.hourly = sim.hourly[sim.hourly.index.year == last_year]


def solar(sim: api.Simulation):
    #### Calculations ####
    sim.monthly["CollP_MW"] = sim.monthly["CollP_kW"] / 1000

    sim.scalar["CollP_kW_calc_Tot"] = sim.hourly["CollP_kW_calc"].sum()
    sim.scalar["CollIT_kW_Tot"] = sim.hourly["CollIT_kW"].sum()

    sim.scalar["Q_kW_m2"] = sim.scalar["CollP_kW_calc_Tot"] / sim.scalar["CollAcollAp"]
    sim.scalar["IT_kW_m2"] = sim.scalar["CollIT_kW_Tot"] / sim.scalar["CollAcollAp"]
    sim.scalar["qSysOut_PipeLoss_Tot"] = sim.hourly["qSysOut_PipeLoss"].sum()

    # Q_vs_T preparation
    df = pd.DataFrame(
        {"T": sim.hourly["CollTOut"], "Q": sim.hourly["CollP_kW_calc"] / 1000}
    )

    df = df.sort_values(by="T")
    df["Q_cum"] = np.cumsum(df["Q"])

    # Stagnation
    sim.hourly["SolarControlStagDays"] = (
            sim.hourly["SolarControlStagDays"] - sim.hourly["SolarControlStagDays"].iloc[1]
    )
    sim.scalar["SolarControlStagDays"] = sim.hourly["SolarControlStagDays"].iloc[-1]

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["CollP_kW"])
    ax.set_ylabel("Power (kW)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "solar-hourly", "solar")

    fig, ax = api.bar_chart(sim.monthly, ["CollP_kW"])
    ax.set_ylabel("Power (kW)")
    ax.legend()
    ax.legend_ = None
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "solar-monthly", "solar")

    fig, ax = api.line_plot(sim.hourly, ["CollTIn", "CollTOut"])
    ax.set_ylabel("Temperature (°C)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "temp-hourly", "solar")

    fig, ax = api.line_plot(sim.hourly, ["SolarControlStag"])
    ax.set_ylabel("Stagnation ON (-)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "stagnation-hourly", "solar")

    plt.figure()
    fig = plt.plot(
        df["T"], df["Q_cum"]
    )  # , linestyle='-', color='blue', label='Q_cum')
    plt.xlabel("$T_{coll,out}$ [°C]")
    plt.ylabel("$Q_{coll,cum}$ [MWh]")
    plt.tight_layout()
    plt.grid()
    # plt.show()
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
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "tes-temps", "tes")

    plt.figure()
    fig = plt.plot(df["T"], df["Q_cum"])  # , linestyle='-', color='blue', label='Q_cum')
    plt.xlabel('$T_{dem}$ [°C]')
    plt.ylabel('$Q_{coll}$ [MWh]')
    plt.tight_layout()
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig[0].figure, sim.path, "q_t", "tes")


def btes(sim: api.Simulation):
    #### Calculations ####
    sim.scalar["BoHxQLoss_kW_Tot"] = sim.hourly["BoHxQLoss_kW"].sum()
    sim.scalar["BoHxQLossTop_kW_Tot"] = sim.hourly["BoHxQLossTop_kW"].sum()
    sim.scalar["BoHxQLossSide_kW_Tot"] = sim.hourly["BoHxQLossSide_kW"].sum()
    sim.scalar["BoHxQLossBot_kW_Tot"] = sim.hourly["BoHxQLossBot_kW"].sum()
    sim.hourly["BoHxQChar_kW"] = abs(sim.hourly['BoHxQCalc_kW'].where(sim.hourly['BoHxQCalc_kW'] < 0,
                                                                      0))  # sim.hourly.loc[sim.hourly["BoHxQAve_kW"] > 0, "BoHxQAve_kW"]
    sim.hourly["BoHxQDischar_kW"] = abs(sim.hourly['BoHxQCalc_kW'].where(sim.hourly['BoHxQCalc_kW'] > 0,
                                                                         0))  # abs(sim.hourly["BoHxQCalc_kW"]) * sim.hourly["ControlBorOnDischar"]
    sim.scalar["BoHxQAccum_kW_Tot"] = sim.hourly["BoHxQAccum_kW"].sum()

    sim.scalar["BoHxQChar_kW_Tot"] = sim.hourly["BoHxQChar_kW"].sum()
    sim.scalar["BoHxQDischar_kW_Tot"] = sim.hourly["BoHxQDischar_kW"].sum()

    sim.scalar["BoHxQAve_kW_Tot"] = sim.hourly["BoHxQAve_kW"].sum()

    sim.scalar["BoHxQMax"] = (
            sim.scalar["BoHxV"]
            * sim.scalar["BoHxCpLayer"]
            * (sim.scalar["SolarControlTTesMax"] - 0)
            / 3600
    )
    sim.scalar["BoHxNCycles"] = (
            sim.scalar["BoHxQChar_kW_Tot"] / sim.scalar["BoHxQMax"]
    )

    sim.scalar["BoHxEff"] = abs(
        sim.scalar["BoHxQDischar_kW_Tot"] / sim.scalar["BoHxQChar_kW_Tot"]
    )

    sim.hourly["BoHxSoc"] = (sim.hourly["BoHxTAve"] - 0) / (95 - 0)

    ## Energy density calculation
    cp = sim.scalar["BoHxCpLayer"]
    sim.scalar["rhoQ"] = (
            (max(sim.hourly["BoHxTAve"]) - min(sim.hourly["BoHxTAve"]))
            * cp
            / 3600
    )

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["BoHxTAveField"])
    ax.set_ylabel("Temperature (°C)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "t-avg-field-hourly", "btes")

    fig, ax = api.line_plot(sim.hourly, ["BoHxTAve"])
    ax.set_ylabel("Temperature (°C)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "t-avg-hourly", "btes")

    fig, ax = api.line_plot(sim.hourly, ["BoHxQAve_kW"])
    ax.set_ylabel("Heat (kW)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "q-hourly", "btes")


def hp(sim: api.Simulation):
    #### Calculations ####
    sim.scalar["HpQEvap_kW_Tot"] = sim.hourly["HpQEvap_kW"].sum()
    sim.scalar["HpQCond_kW_Tot"] = sim.hourly["HpQCond_kW"].sum()
    sim.scalar["HpPelComp_kW_Tot"] = sim.hourly["HpPelComp_kW"].sum()
    sim.scalar["HpCOP"] = sim.scalar["HpQCond_kW_Tot"] / sim.scalar["HpPelComp_kW_Tot"]

    fig, ax = api.energy_balance(
        sim.monthly,
        q_in_columns=["HpPelComp_kW", "HpQEvap_kW"],
        q_out_columns=["HpQCond_kW"],
        xlabel="",
    )
    api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "hp")

    #### Q vs T ####
    plot_variables = [
        ["HpQEvap_kW", "HpTEvapOut"],
        ["HpQCond_kW", "HpTCondOut"],

    ]

    dataframes = []

    plt.figure()

    for q, t in plot_variables:
        a = sim.hourly[q]
        b = sim.hourly[t]
        df = pd.DataFrame({q: a, t: b})

        df = df.sort_values(by=t)
        df[q] = np.cumsum(df[q])
        dataframes.append(df)

        fig = plt.plot(df[t], df[q], label=q + "____" + t)  # , linestyle='-', color='blue', label='Q_cum')

    #     plt.ion()
    #
    #
    # plt.ioff()  # Desactivar modo interactivo
    plt.xlabel('Temperature [°C]')
    plt.ylabel('Cumulative energy [kWh]')
    plt.grid()
    plt.legend()
    # plt.show()
    api.export_plots_in_configured_formats(fig[0].figure, sim.path, "q_t", "hp")

    # #### Evap, discharge difference
    # sim.hourly["DeltaQ"] = sim.hourly["HpQEvap_kW"] - sim.hourly["BoHxQDischar_kW"]
    #
    #
    #
    # fig, ax = api.line_plot(sim.hourly, ["HpQEvap_kW", "BoHxQDischar_kW", "DeltaQ"])
    # ax.set_ylabel("Power kW (-)")
    # plt.grid()
    # plt.show()
    # api.export_plots_in_configured_formats(fig, sim.path, "q-evap-hourly", "hp")
    #
    # fig, ax = api.line_plot(sim.hourly, ["HpTEvapIn", "HpTEvapOut", "BoHxTIn", "BoHxTout" ])
    # ax.set_ylabel("Temperature (-)")
    # plt.grid()
    # plt.show()
    # api.export_plots_in_configured_formats(fig, sim.path, "t-evap-hourly", "hp")
    #
    # fig, ax = api.line_plot(sim.hourly, ["BoHxM", "HpMfrEvapIn"])
    # ax.set_ylabel("Mfr (-)")
    # plt.grid()
    # plt.show()
    # api.export_plots_in_configured_formats(fig, sim.path, "mfr-evap-hourly", "hp")


def hx(sim: api.Simulation):
    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["HxQ_kW"])
    ax.set_ylabel("Heat (kW)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "q-hourly", "hx")

    fig, ax = api.line_plot(sim.hourly, ["HxEff"])
    ax.set_ylabel("Efficiency (-)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "efficiency-hourly", "hx")

    fig, ax = api.line_plot(sim.hourly, ["HxLMTD"])
    ax.set_ylabel("LMTD (K)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "LMTD-hourly", "hx")


def boiler(sim: api.Simulation):
    #### Calculations ####
    sim.scalar["BolrPOut_kW_Tot"] = sim.hourly["BolrPOut_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["BolrPOut_kW"])
    ax.set_ylabel("Power (kW)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "boiler-hourly", "boiler")


def demand(sim: api.Simulation):
    #### Calculations ####
    sim.scalar["QSnkP_kW_Tot"] = sim.hourly["QSnkP_kW"].sum()
    sim.scalar["QSnkTIn_Avg"] = sim.hourly["QSnkTIn"].mean()
    sim.scalar["QSnkTOut_Avg"] = sim.hourly["QSnkTOut"].mean()
    sim.step["QSnkPreal_kW"] = 0
    # Losses
    sim.scalar["qSysOut_dpToFFieldTot_Tot"] = sim.hourly["qSysOut_dpToFFieldTot"].sum()
    sim.scalar["qSysOut_dpPipeIntTot_Tot"] = sim.hourly["qSysOut_dpPipeIntTot"].sum()
    sim.scalar["qSysOut_dpSoilIntTot_Tot"] = sim.hourly["qSysOut_dpSoilIntTot"].sum()

    sim.monthly["QDistrict"] = (
            sim.monthly["qSysOut_dpToFFieldTot"]
            + sim.monthly["qSysOut_dpPipeIntTot"]
            + sim.monthly["qSysOut_dpSoilIntTot"]
    )

    sim.monthly["QDemand_kW"] = sim.monthly["QSnkP_kW"] + sim.monthly["QDistrict"]
    sim.scalar["QDemand_kW_Tot"] = sim.monthly["QDemand_kW"].sum()

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["QSnkP_kW"])
    ax.set_ylabel("Power (kW)")
    ax.legend_.remove()
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "sink-hourly", "sink")


def control(sim: api.Simulation):
    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["ControlBorOnChar", "ControlBorOnDischar"])
    ax.set_ylabel("Activation (-)")
    plt.grid()
    # plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "mode-hourly", "control")


def balance(sim: api.Simulation):
    #### Calculations ####
    sim.scalar["QSources"] = sim.scalar["CollP_kW_calc_Tot"] + sim.scalar["BolrPOut_kW_Tot"] + sim.scalar[
        "HpPelComp_kW_Tot"]
    sim.scalar["QSinks"] = sim.scalar["QSnkP_kW_Tot"]
    sim.scalar["QStore"] = sim.scalar["BoHxQAve_kW_Tot"] + sim.scalar["TesQAcum_Tes1_Tot"]
    sim.scalar["QLosses"] = sim.scalar["TesQLoss_Tes1_Tot"] + sim.scalar["qSysOut_PipeLoss_Tot"]

    sim.monthly["QDistrict_MW"] = sim.monthly["QDistrict"] / 1000
    sim.scalar["QDistrict_MW"] = sim.monthly["QDistrict_MW"].sum()

    sim.scalar["QImb"] = sim.scalar["QSources"] - sim.scalar["QStore"] - sim.scalar["QSinks"] - sim.scalar["QLosses"]

    #### Plots ####
    names_legend = ['$Q_{Coll}$', '$P_{Comp}$', '$Q_{Boiler}$', '$Q_{BTES,Accum}$',
                    '$Q_{Demand}$', '$Q_{TES,Accum}$', '$Q_{TES,Losses}$', '$Q_{District}$']

    fig, ax = api.energy_balance(
        sim.monthly,
        q_in_columns=["CollP_kW_calc", "HpPelComp_kW", "BolrPOut_kW"],
        q_out_columns=["BoHxQAve_kW", "QSnkP_kW", "TesQAcum_Tes1", "TesQLoss_Tes1", "qSysOut_dpToFFieldTot"],
        # , "qSysOut_dpPipeIntTot", "qSysOut_dpSoilIntTot"],
        xlabel="",
        cmap="Paired"
    )
    plt.legend(names_legend, bbox_to_anchor=(1.05, 1), loc='upper left')
    api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "balance")


def kpi(sim: api.Simulation):
    ### Calculations ###
    sim.scalar["FactorRenewable"] = (sim.scalar["QSnkP_kW_Tot"] - sim.scalar["BolrPOut_kW_Tot"]) / sim.scalar[
        "QSnkP_kW_Tot"]

    ### Create dataframe with Solites KPIs ###
    sim.scalar["zero"] = 0

    data = [
        sim.scalar["IT_kW_m2"],  # 14
        sim.scalar["CollP_kW_calc_Tot"] / 1000,  # 15
        sim.scalar["Q_kW_m2"],  # 16
        sim.scalar["zero"] / 1000,  # 17
        sim.scalar["BoHxQChar_kW_Tot"] / 1000,  # 18
        sim.scalar["BoHxQDischar_kW_Tot"] / 1000,  # 19
        sim.scalar["BoHxQLoss_kW_Tot"] / 1000,  # 20
        sim.scalar["BoHxQLossTop_kW_Tot"] / 1000,  # 21
        sim.scalar["BoHxQLossSide_kW_Tot"] / 1000,  # 22
        sim.scalar["BoHxQLossBot_kW_Tot"] / 1000,  # 23
        sim.scalar["QDistrict_MW"],  # 24
        sim.scalar["BoHxQAccum_kW_Tot"] / 1000,  # 25
        sim.scalar["HpQEvap_kW_Tot"] / 1000,  # 26
        sim.scalar["HpQCond_kW_Tot"] / 1000,  # 27
        sim.scalar["HpPelComp_kW_Tot"] / 1000,  # 28
        sim.scalar["BolrPOut_kW_Tot"] / 1000,  # 29
        sim.scalar["QDemand_kW_Tot"] / 1000,  # 30
        sim.scalar["zero"],  # 31
        sim.scalar["SolarControlStagDays"],  # 32
        sim.scalar["HpCOP"],  # 33
        sim.scalar["BoHxEff"],  # 34
        sim.scalar["BoHxNCycles"],  # 35
        sim.scalar["QSnkTIn_Avg"],  # 36
        sim.scalar["QSnkTOut_Avg"],  # 37
    ]
    df = pd.DataFrame(data)
    df.to_csv(sim.path + "\\data.csv", header=False, index=False)


def to_json(sim: api.Simulation):
    sim.scalar.to_json(sim.path + "\output.json", orient="records", indent=4)


if __name__ == "__main__":
    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\BTES\results_more_power")
    api.global_settings.reader.force_reread_prt = True
    api.global_settings.reader.read_step_files = False

    processing_steps = [
        filter,
        solar,
        hx,
        tes,
        btes,
        hp,
        boiler,
        demand,
        control,
        balance,
        kpi,
        to_json,
    ]

    simulation_data = api.process_whole_result_set(
        path_to_sim,
        processing_steps,
    )