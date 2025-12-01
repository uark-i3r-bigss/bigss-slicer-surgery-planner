import os
import unittest
import vtk
import qt
import ctk
import slicer
from slicer.ScriptedLoadableModule import *
import logging
import sys

# Ensure Resources is in path for module imports
resources_path = os.path.join(os.path.dirname(__file__), 'Resources')
if resources_path not in sys.path:
    sys.path.append(resources_path)

from SurgeryPlannerLib import surgery_planner_helper as sh
from SurgeryPlannerLib.SurgeryPlannerLogic import SurgeryPlannerLogic, setSlicePoseFromSliceNormalAndPosition
from SurgeryPlannerLib.TrajectoryPlanner import TrajectoryPlannerWidget
from SurgeryPlannerLib.SegmentationPlanner import SegmentationPlannerWidget

# SurgeryPlanner
class SurgeryPlanner(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Surgery Planner" 
        self.parent.categories = ["Planning"]
        self.parent.dependencies = []
        self.parent.contributors = ["Ping-Cheng Ku, Henry Phalen (Johns Hopkins University)"] 
        self.parent.helpText = """
This module can be used to plan surgery trajectories/segmetnations on 3D volumes / images.
"""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """
This module was developed by Ping-Cheng Ku and Henry Phalen.
"""

# noinspection PyAttributeOutsideInit,PyMethodMayBeStatic
class SurgeryPlannerWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.dir = os.path.dirname(__file__)
        self.logic = SurgeryPlannerLogic()

        # Mode Selector
        self.layout.addWidget(qt.QLabel("Select Action:"))
        self.modeSelector = qt.QComboBox()
        self.modeSelector.addItem("Create Trajectory")
        self.modeSelector.addItem("Create Segmentation")
        self.modeSelector.addItem("Restart Slicer")
        self.modeSelector.currentIndexChanged.connect(self.onModeChanged)
        self.layout.addWidget(self.modeSelector)

        # Instantiate Sub-Planners
        # We pass self.dir as module_dir so they can find resources
        self.trajectoryPlanner = TrajectoryPlannerWidget(parent=None, logic=self.logic, module_dir=self.dir)
        self.layout.addWidget(self.trajectoryPlanner)
        
        self.segmentationPlanner = SegmentationPlannerWidget(parent=None, logic=self.logic)
        self.layout.addWidget(self.segmentationPlanner)
        self.segmentationPlanner.hide() # Hidden by default

        # Add vertical spacer
        self.layout.addStretch(1)

    def cleanup(self):
        pass

    def onModeChanged(self, index):
        if index == 0: # Create Trajectory
            self.trajectoryPlanner.show()
            self.segmentationPlanner.hide()
        elif index == 1: # Create Segmentation
            self.trajectoryPlanner.hide()
            self.segmentationPlanner.show()
        elif index == 2: # Restart Slicer
            slicer.util.restart()

class SurgeryPlannerTest(ScriptedLoadableModuleTest):
    """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

    def setUp(self):
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        self.setUp()
        self.test_SurgeryPlanner1()

    def test_SurgeryPlanner1(self):
        self.delayDisplay("Starting the test:")
        self.delayDisplay("No tests for now!")
        self.delayDisplay('Test passed!')
