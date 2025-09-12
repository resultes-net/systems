import pathlib as _pl
import matplotlib.pyplot as _plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api


# def evaluate_sims(sims_data: api.SimulationsData):
#     tank_condition = sims_data.scalar["TKMfrTOut_ratio"] > 0.90
#     wort_condition = sims_data.scalar["MfrWortSr_ratio"] > 0.90
#     renewable_condition = sims_data.scalar["renewableSystem"] > 0.0
#     sims_data.scalar["tankCondition"] = tank_condition
#     sims_data.scalar["wortCondition"] = wort_condition
#     sims_data.scalar["acceptableSimulation"] = tank_condition & wort_condition & renewable_condition
#
#     base_consumption = sims_data.scalar.loc["brewery_2-AdCHsizeHpUsed_kW_new50-HVFPAcollAp_new400-renewableSystem_new0", "AmCHPelCoolComp_kW_Tot"]
#     consumption_reduction = 1-sims_data.scalar["AmCHPelCoolComp_kW_Tot"]/base_consumption
#     sims_data.scalar["consumptionReduction"] = consumption_reduction


def compare_plot(sims_data: api.SimulationsData):


    # filtered_scalar = sims_data.scalar[sims_data.scalar['acceptableSimulation']]
    #
    # fig, ax = api.scatter_plot(
    #     filtered_scalar,
    #     "HVFPAcollAp",
    #     "AmCHPelCoolComp_kW_Tot",
    #     group_by_color="AdCHsizeHpUsed_kW",
    # )
    # ax.grid(True)
    # # _plt.show()
    # api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "p_comp", "../comparison")

    # RENEWABLE FACTOR
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "szVperDemand_m3_per_MWh",
        "FactorRenewable",
        group_by_color="HpAct",
    )
    names_legend = ['HP OFF', 'HP ON']
    ax.grid(True)
    ax.legend(names_legend, bbox_to_anchor=(1.05, 1), loc='upper left')
    # _plt.show()
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "factor", "../comparison")

    # SOLAR
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "szVperDemand_m3_per_MWh",
        "Q_kW_m2",
        group_by_color="HpAct",
    )

    ax.grid(True)
    # ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    # _plt.show()
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "solar_density", "../comparison")

    # PTES
    fig, ax = api.scalar_compare_plot(
        sims_data.scalar,
        "szVperDemand_m3_per_MWh",
        "rhoQ",
        group_by_color="HpAct",
    )

    ax.grid(True)
    # ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    # _plt.show()
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "ptes", "../comparison")


    # fig, ax = api.scatter_plot(
    #     filtered_scalar,
    #     "AdCHsizeHpUsed_kW",
    #     "LCOE",
    #     # group_by_marker="HVFPAcollAp",
    #     group_by_color="HVFPAcollAp"
    # )
    # ax.grid(True)
    # ax.axhline(y=0.0062, color='r', linestyle='--', label='Base case')
    # ax.set_xlabel('$Q_{nom, AdCh}$ (kW)')
    # ax.set_ylabel('$LCOE$ (EUR/kWh)')
    # api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe", "../comparison")



def compare_plot_own(sims_data: api.SimulationsData):

    filtered_scalar = sims_data.scalar[sims_data.scalar['acceptableSimulation']]
    filtered_scalar['HVFPAcollAp'] = filtered_scalar['HVFPAcollAp'].round().astype(int)

    # LCOE BIS
    fig, ax = _plt.subplots()

    for category, group in filtered_scalar.groupby('HVFPAcollAp'):
        group = group.sort_values('AdCHsizeHpUsed_kW')
        ax.plot(group['AdCHsizeHpUsed_kW'], group['LCOE'], label=category, marker="x")


    _plt.xlabel('$Q_{nom, AdCh}~(kW)$')
    _plt.ylabel('$LCOE~(EUR/kWh)$')
    _plt.legend(title='$A_{coll}~(m^2)$')
    ax.axhline(y=0.0079915032, color='r', linestyle='--', label='Base case')
    ax.grid(True)
    # _plt.show()
    api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe_bis", "../comparison")
#
#
#     # LCOE
#     fig, ax = _plt.subplots()
#
#     for category, group in filtered_scalar.groupby('AdCHsizeHpUsed_kW'):
#         group = group.sort_values('HVFPAcollAp')
#         ax.plot(group['HVFPAcollAp'], group['LCOE'], label=category, marker="x")
#
#
#     _plt.xlabel('$A_{coll}~(m^2)$')
#     _plt.ylabel('$LCOE~(EUR/kWh)$')
#     _plt.legend(title='$Q_{nom, AdCh}~(kW)$')
#     ax.axhline(y=0.0079915032, color='r', linestyle='--', label='Base case')
#     ax.grid(True)
#     # _plt.show()
#     api.export_plots_in_configured_formats(fig.figure, sims_data.path_to_simulations, "lcoe", "../comparison")




# def compare_temp(sims_data: api.SimulationsData):
#     plot_variables = [
#         ["TKMfrTOut ", "TKTOut"]
#     ]
#
#     included_simulations = ['brewery_2-AdCHsizeHpUsed_kW_new50-HVFPAcollAp_new120',
#                             'brewery_2-AdCHsizeHpUsed_kW_new50-HVFPAcollAp_new5000']
#
#     dataframes = []
#     _plt.figure()
#
#     for sim_name, sim in sims_data.simulations.items():
#         if sim_name not in included_simulations:
#             continue
#
#         df = pd.DataFrame({
#             'mfr': sim.hourly["TKMfrHotW"],
#             't': sim.hourly["TKTOut"]
#         })
#
#         df = df.sort_values(by='t')
#         df['mfr'] = -np.cumsum(df['mfr'])
#         dataframes.append(df)
#
#         fig = _plt.plot(df['t'], df['mfr'], label=sim_name)  # , linestyle='-', color='blue', label='Q_cum')
#
#
#     _plt.xlabel('Temperature [°C]')
#     _plt.ylabel('Cumulative MFR [kg/h]')
#     _plt.grid()
#     _plt.legend()
#     # _plt.show()
#     api.export_plots_in_configured_formats(fig[0].figure, sims_data.path_to_simulations, "mfr_t", "../comparison")


if __name__ == "__main__":

    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\PTES\results")
    api.global_settings.reader.force_reread_prt = False
    # simulations_data = api.process_whole_result_set(path_to_sim, [])
    comparison_steps = [
                        compare_plot,
    ]
    api.do_comparison(comparison_steps,results_folder=path_to_sim)
