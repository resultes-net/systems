# pylint: skip-file
# type: ignore

# -*- coding: utf-8 -*-
"""
Created on Fri Sep 30 10:06:47 2016

@author: dcarbone, mbattagl
"""

import os

from pytrnsys.rsim import runParallelTrnsys as runTrnsys
from pytrnsys.utils import log as log

if __name__ == "__main__":
    logger = log.getOrCreateCustomLogger("root", "INFO")

    logger.info("Running config file %s...", "run_only_hp_lorenz")

    nameDeck = "run_only_hp_lorenz"
    pathBase = os.getcwd()

    runTool = runTrnsys.RunParallelTrnsys(pathBase, nameDeck)

    runTool.readConfig(pathBase, "run_only_hp_lorenz.config")
    runTool.getConfig()
    runTool.runConfig()
    runTool.runParallel()

    logger.info("...DONE (%s).", "run_only_hp_lorenz")