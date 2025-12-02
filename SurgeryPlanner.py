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
from SurgeryPlannerLib.ReferencePlanePlanner import ReferencePlanePlannerWidget

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
        self.modeSelector.addItem("Trajectory Planning")
        self.modeSelector.addItem("Segmentation Planning")
        self.modeSelector.addItem("Reference Plane Planning")
        self.modeSelector.addItem("Restart Slicer")
        self.modeSelector.currentIndexChanged.connect(self.onModeChanged)
        self.layout.addWidget(self.modeSelector)

        # --- Trajectory Area ---
        self.trajectoryArea = qt.QWidget()
        self.trajectoryLayout = qt.QVBoxLayout(self.trajectoryArea)
        self.layout.addWidget(self.trajectoryArea)
        
        self.trajectoryPlannerWidget = TrajectoryPlannerWidget(self.trajectoryArea, self.logic, self.dir)
        self.trajectoryLayout.addWidget(self.trajectoryPlannerWidget)

        # --- Segmentation Area ---
        self.segmentationArea = qt.QWidget()
        self.segmentationLayout = qt.QVBoxLayout(self.segmentationArea)
        self.layout.addWidget(self.segmentationArea)
        
        self.segmentationPlannerWidget = SegmentationPlannerWidget(self.segmentationArea, self.logic, self.dir)
        self.segmentationLayout.addWidget(self.segmentationPlannerWidget)
        
        # --- Reference Plane Area ---
        self.referencePlaneArea = qt.QWidget()
        self.referencePlaneLayout = qt.QVBoxLayout(self.referencePlaneArea)
        self.layout.addWidget(self.referencePlaneArea)
        
        self.referencePlanePlannerWidget = ReferencePlanePlannerWidget(self.referencePlaneArea, self.logic, self.dir)
        self.referencePlaneLayout.addWidget(self.referencePlanePlannerWidget)

        # Initial State
        self.onModeChanged(0)

    def cleanup(self):
        pass

    def onModeChanged(self, index):
        mode = self.modeSelector.currentText
        
        # Hide all first
        self.trajectoryArea.hide()
        self.segmentationArea.hide()
        self.referencePlaneArea.hide()
        
        if mode == "Trajectory Planning":
            self.trajectoryArea.show()
        elif mode == "Segmentation Planning":
            self.segmentationArea.show()
        elif mode == "Reference Plane Planning":
            self.referencePlaneArea.show()
        elif mode == "Restart Slicer":
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
