import pathlib as _pl
import matplotlib.pyplot as _plt
import numpy as np
import pandas as pd
from datetime import datetime
from pytrnsys_process import api

def control(sim:api.Simulation):
    sim.step["HpControlFracCond_100"] = sim.step["HpControlFracCond"] * 100

    fig, ax = api.line_plot(sim.step, ["HpControlTControlled", "HpControlTSet", "HpControlFracCond_100"])
    _plt.ylim(0, 110)
    _plt.grid()
    _plt.show()
    api.export_plots_in_configured_formats(fig, sim.path, "hp-control", "hp")

    
if __name__ == "__main__":
    path_to_sim = _pl.Path(r"C:\Daten\GIT\systems\only_hp_lorenz\results")
    api.global_settings.reader.force_reread_prt = True
    api.global_settings.reader.read_step_files = True

    processing_steps = [
                        control,
                        ]

    simulation_data = api.process_whole_result_set(
        path_to_sim,
        processing_steps,
    )