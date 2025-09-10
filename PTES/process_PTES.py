import pathlib as _pl
import matplotlib.pyplot as _plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api

def solar(sim: api.Simulation):

    #### Calculations ####
    sim.monthly["CollP_MW"] = sim.monthly["CollP_kW"] / 1000

    sim.scalar["CollP_kW_calc_Tot"] = sim.hourly["CollP_kW_calc"].sum()
    sim.scalar["Q_kW_m2"] = sim.scalar["CollP_kW_calc_Tot"] / sim.scalar["CollAcollAp"]
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

def hx(sim: api.Simulation):

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["HxCollEff", "HxEff", "HxQSrcEff"])
    ax.set_ylabel("Efficiency (-)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "efficiency-hourly", "hx")

    fig, ax = api.line_plot(sim.hourly, ["HxCollLMTD", "HxLMTD", "HxQSrcLMTD"])
    ax.set_ylabel("LMTD (K)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "LMTD-hourly", "hx")

def ptes(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["pitStoreQLosses_kW_Tot"] = sim.hourly["pitStoreQLosses_kW"].sum()
    sim.scalar["pitStoreQ13_kW_Tot"] = sim.hourly["pitStoreQ13_kW"].sum()
    sim.scalar["pitStoreQ23_kW_Tot"] = sim.hourly["pitStoreQ23_kW"].sum()
    sim.scalar["pitStoreQ31_kW_Tot"] = sim.hourly["pitStoreQ31_kW"].sum()
    sim.scalar["pitStoreQAccum_kW_Tot"] = sim.hourly["pitStoreQAccum_kW"].sum()

    sim.scalar["pitStoreQCharge_Tot"] = sim.scalar["pitStoreQ13_kW_Tot"] + sim.scalar["pitStoreQ23_kW_Tot"]
    sim.scalar["pitStoreQDisharge_Tot"] = sim.scalar["pitStoreQ31_kW_Tot"]

    sim.hourly["pitStoreSoc"] = (sim.hourly["pitStoreTAvgTank"]-0)/(95-0)

    ## Energy density calculation
    m = sim.scalar["pitStoreV"]*sim.scalar["pitStoreFlDen"]
    cp = sim.scalar["pitStoreFlSpeHeat"]
    rho = sim.scalar["pitStoreFlDen"]
    sim.scalar["rhoQ"] = (max(sim.hourly["pitStoreTAvgTank"]) - min(sim.hourly["pitStoreTAvgTank"])) * rho * cp/3600

    ## Efficiency calculation
    # sim.scalar["pitStoreEff"] = (sim.scalar["pitStoreQDisharge_Tot"] + max(0,sim.scalar["pitStoreQAccum_kW_Tot"]) + sim.scalar["pitStoreQLosses_kW_Tot"]) / ...
    # (sim.scalar["pitStoreQDisharge_Tot"] + max(0, sim.scalar["pitStoreQAccum_kW_Tot"]))



    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["pitStoreTTherStat1", "pitStoreTTherStat2", "pitStoreTTherStat3"])
    ax.set_ylabel("Temperature (°C)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "t-ptes-hourly", "ptes")

    fig, ax = api.line_plot(sim.hourly, ["pitStoreSoc"])
    ax.set_ylabel("SOC (-)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "soc-hourly", "ptes")

    fig, ax = api.energy_balance(
        sim.monthly,
        q_in_columns=[],
        q_out_columns=["pitStoreQ13_kW", "pitStoreQ23_kW", "pitStoreQ31_kW", "pitStoreQLosses_kW", "pitStoreQAccum_kW"],
        xlabel=""
    )
    api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "ptes")

def hp(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["HpQEvap_kW_Tot"] = sim.hourly["HpQEvap_kW"].sum()
    sim.scalar["HpQCond_kW_Tot"] = sim.hourly["HpQCond_kW"].sum()
    sim.scalar["HpPelComp_kW_Tot"] = sim.hourly["HpPelComp_kW"].sum()
    sim.scalar["HpCOP"] = sim.scalar["HpQCond_kW_Tot"] / sim.scalar["HpPelComp_kW_Tot"]
    sim.step["HpControlFracCond_100"] = sim.step["HpControlFracCond"] * 100

    #### Control ####
    fig, ax = api.line_plot(sim.step, ["HpControlTControlled", "HpControlTSet", "HpControlFracCond_100"])
    _plt.ylim(0, 110)
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "hp-control", "hp")

    fig, ax = api.energy_balance(
        sim.monthly,
        q_in_columns=["HpPelComp_kW", "HpQEvap_kW"],
        q_out_columns=["HpQCond_kW"],
        xlabel=""
    )
    api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "hp")

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
    sim.step["QSnkPreal_kW"] = 0

    #### Plots ####
    fig, ax = api.line_plot(sim.hourly, ["QSnkP_kW"])
    ax.set_ylabel("Power (kW)")
    _plt.grid()
    # _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "sink-hourly", "sink")

def district(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["qSysOut_dpToFFieldTot_Tot"] = sim.hourly["qSysOut_dpToFFieldTot"].sum()
    sim.scalar["qSysOut_dpPipeIntTot_Tot"] = sim.hourly["qSysOut_dpPipeIntTot"].sum()
    sim.scalar["qSysOut_dpSoilIntTot_Tot"] = sim.hourly["qSysOut_dpSoilIntTot"].sum()

    #### Plots ####
    # fig, ax = api.line_plot(sim.hourly, ["TValMix_SCnr", "TSCnr2_QSnk", "TQSnk_SCnr2", "TSCnr_Tee"])
    # ax.set_ylabel("Temperature (°C)")
    # _plt.grid()
    # # _plt.show()
    # api.export_plots_in_configured_formats(fig, sim.path, "temp-hourly", "district")


def balance(sim: api.Simulation):


    #### Calculations ####

    # sim.hourly["QSources"] = sim.hourly["CollP_kW"] + sim.hourly["BolrPOut_kW"] + sim.hourly["QSrcP_kW"] + sim.hourly["HpPelComp_kW"]
    # sim.hourly["QSinks"]   = sim.hourly["QSnkP_kW"]
    # sim.hourly["QStore"]   = sim.hourly["pitStoreQAccum_kW"]
    # sim.hourly["QLosses"]  = sim.hourly["pitStoreQLosses_kW"] + sim.hourly["qSysOut_PipeLoss"]
    #
    # sim.monthly["QSources"] = sim.monthly["CollP_kW"] + sim.monthly["BolrPOut_kW"] + sim.monthly["QSrcP_kW"] + sim.monthly["HpPelComp_kW"]
    # sim.monthly["QSinks"]   = sim.monthly["QSnkP_kW"]
    # sim.monthly["QStore"]   = sim.monthly["pitStoreQAccum_kW"]
    # sim.monthly["QLosses"]  = sim.monthly["pitStoreQLosses_kW"] + sim.monthly["qSysOut_PipeLoss"]

    sim.scalar["QSources"] = sim.scalar["CollP_kW_calc_Tot"] + sim.scalar["BolrPOut_kW_Tot"] + sim.scalar["QSrcP_kW_Tot"] + sim.scalar["HpPelComp_kW_Tot"]
    sim.scalar["QSinks"] = sim.scalar["QSnkP_kW_Tot"]
    sim.scalar["QStore"] = sim.scalar["pitStoreQAccum_kW_Tot"]
    sim.scalar["QLosses"] = sim.scalar["pitStoreQLosses_kW_Tot"]# + sim.scalar["qSysOut_PipeLoss_Tot"] + sim.scalar["qSysOut_dpPipeIntTot_Tot"]

    sim.scalar["QImb"] = sim.scalar["QSources"] - sim.scalar["QStore"] - sim.scalar["QSinks"] - sim.scalar["QLosses"]

    #### Plots ####
    fig, ax = api.energy_balance(
        sim.monthly,
        q_in_columns=["CollP_kW_calc", "HpPelComp_kW", "BolrPOut_kW", "QSrcP_kW"],
        q_out_columns=["QSnkP_kW", "pitStoreQAccum_kW", "pitStoreQLosses_kW"],
    # , "qSysOut_PipeLoss", "qSysOut_dpToFFieldTot", "qSysOut_dpPipeIntTot", "qSysOut_dpSoilIntTot"
        xlabel="",
        cmap = "Paired"
    )
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    api.export_plots_in_configured_formats(fig, sim.path, "balance-monthly", "balance")


def kpi(sim: api.Simulation):

    #### Calculations ####
    sim.scalar["FactorRenewable"] = (sim.scalar["QSnkP_kW_Tot"] - sim.scalar["BolrPOut_kW_Tot"]) / sim.scalar["QSnkP_kW_Tot"]

def to_json(sim: api.Simulation):
    sim.scalar.to_json(sim.path + "\output.json", orient="records", indent=4)
    
if __name__ == "__main__":
    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\PTES\results")
    api.global_settings.reader.force_reread_prt = True
    api.global_settings.reader.read_step_files = True

    processing_steps = [
                        solar,
                        hx,
                        ptes,
                        hp,
                        boiler,
                        source,
                        sink,
                        district,
                        balance,
                        kpi,
                        to_json,
                        ]

    simulation_data = api.process_whole_result_set(
        path_to_sim,
        processing_steps,
    )