import os
import vtk
import qt
import ctk
import slicer
import numpy as np
from datetime import datetime
import SurgeryPlannerLib.surgery_planner_helper as sh
from .SurgeryPlannerLogic import SurgeryPlannerLogic, setSlicePoseFromSliceNormalAndPosition

try:
    import yaml
except ImportError:
    yaml = None

class TrajectoryPlannerWidget(qt.QWidget):
    def __init__(self, parent=None, logic=None, module_dir=None):
        super(TrajectoryPlannerWidget, self).__init__(parent)
        self.logic = logic if logic else SurgeryPlannerLogic()
        self.module_dir = module_dir
        if not self.module_dir:
            # Fallback if not provided, assuming standard structure
            # This file is in Resources/SurgeryPlannerLib/
            # We want SurgeryPlanner/
            self.module_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

        # Initialize state variables
        self.redSliceNode = slicer.util.getNode('vtkMRMLSliceNodeRed')
        self.selectedTraj = None
        self.trajList = np.array([])
        self.downAxisBool = False
        self.session_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Load Config
        self.config = self.load_config()
        self.temp_landmark_file = self.config.get('output_file', '/tmp/slicer_surgery_planner_points.txt')

        self.setup_ui()
        self.setup_scene()

    def setup_ui(self):
        self.main_layout = qt.QVBoxLayout(self)
        
        # Actions (Trajectory)
        actionsCollapsibleButton = ctk.ctkCollapsibleButton()
        actionsCollapsibleButton.text = "Actions"
        self.main_layout.addWidget(actionsCollapsibleButton)
        actionsFormLayout = qt.QFormLayout(actionsCollapsibleButton)

        # Visualization (Trajectory)
        vizCollapsibleButton = ctk.ctkCollapsibleButton()
        vizCollapsibleButton.text = "Visualization and Control"
        self.main_layout.addWidget(vizCollapsibleButton)
        vizCollapsibleButton.setChecked(False)
        vizFormLayout = qt.QFormLayout(vizCollapsibleButton)

        # Parameters (Trajectory)
        trajParametersCollapsibleButton = ctk.ctkCollapsibleButton()
        trajParametersCollapsibleButton.text = "Landmark Saving"
        self.main_layout.addWidget(trajParametersCollapsibleButton)
        trajParametersCollapsibleButton.setChecked(True)
        trajParametersFormLayout = qt.QFormLayout(trajParametersCollapsibleButton)

        # Loading (Trajectory)
        loadingCollapsibleButton = ctk.ctkCollapsibleButton()
        loadingCollapsibleButton.text = "Landmark Loading"
        self.main_layout.addWidget(loadingCollapsibleButton)
        loadingCollapsibleButton.setChecked(False)
        loadingFormLayout = qt.QFormLayout(loadingCollapsibleButton)

        # --- Shared/General Area ---
        # Slice Viz (Shared)
        slicevizCollapsibleButton = ctk.ctkCollapsibleButton()
        slicevizCollapsibleButton.text = "Toggle Slice Display"
        self.main_layout.addWidget(slicevizCollapsibleButton)
        slicevizCollapsibleButton.setChecked(False)
        slicevizFormLayout = qt.QFormLayout(slicevizCollapsibleButton)

        # Parameter Layout Buttons
        """Toggle Slice Intersections Button"""
        self.toggleSliceIntersectionButton = qt.QPushButton("Toggle Slice Intersections")
        self.toggleSliceIntersectionButton.toolTip = "Turn on / off colored lines representing slice planes"
        self.toggleSliceIntersectionButton.enabled = True
        slicevizFormLayout.addRow(self.toggleSliceIntersectionButton)
        # Default Slice Intersection to ON
        sliceDisplayNodes = slicer.util.getNodesByClass('vtkMRMLSliceDisplayNode')
        for sliceDisplayNode in sliceDisplayNodes:
            sliceDisplayNode.SetIntersectingSlicesVisibility(1)

        """Destination Folder Selector"""
        default_output_path = self.config.get('output_file', '/tmp/slicer_surgery_planner_points.txt')
        default_dir = os.path.expanduser('~/slicer_annotations')
        default_filename = os.path.basename(default_output_path)
        
        self.outputDirSelector = ctk.ctkPathLineEdit()
        self.outputDirSelector.filters = ctk.ctkPathLineEdit.Dirs
        self.outputDirSelector.toolTip = "Select the folder to save the landmarks output file"
        self.outputDirSelector.currentPath = default_dir
        trajParametersFormLayout.addRow("Destination Folder:", self.outputDirSelector)

        """Destination Filename Box"""
        self.outputFileNameBox = qt.QLineEdit()
        self.outputFileNameBox.text = default_filename
        self.outputFileNameBox.toolTip = "Enter the filename for the landmarks output file"
        trajParametersFormLayout.addRow("Destination Filename:", self.outputFileNameBox)

        """Manual Save Buttons"""
        self.manualSaveLayout = qt.QHBoxLayout()
        self.saveAsTxtButton = qt.QPushButton("Save as TXT")
        self.saveAsTxtButton.toolTip = "Save current landmarks to the specified TXT file"
        self.saveAsTxtButton.connect('clicked(bool)', self.onSaveAsTxtButton)
        self.manualSaveLayout.addWidget(self.saveAsTxtButton)

        self.saveAsFcsvButton = qt.QPushButton("Save as FCSV")
        self.saveAsFcsvButton.toolTip = "Save current landmarks to the specified FCSV file"
        self.saveAsFcsvButton.connect('clicked(bool)', self.onSaveAsFcsvButton)
        self.manualSaveLayout.addWidget(self.saveAsFcsvButton)
        trajParametersFormLayout.addRow("Manual Save:", self.manualSaveLayout)

        """Auto-Save Info"""
        self.autoSaveLabel = qt.QLabel(self.temp_landmark_file)
        self.autoSaveLabel.toolTip = "Location of the continuous auto-save file"
        trajParametersFormLayout.addRow("Auto-Save Location:", self.autoSaveLabel)

        """Landmark Loading UI"""
        self.loadingDirSelector = ctk.ctkPathLineEdit()
        self.loadingDirSelector.filters = ctk.ctkPathLineEdit.Dirs
        self.loadingDirSelector.toolTip = "Select the folder to load landmarks from"
        self.loadingDirSelector.currentPath = default_dir
        loadingFormLayout.addRow("Landmark Folder:", self.loadingDirSelector)

        self.loadingFileNameBox = qt.QLineEdit()
        self.loadingFileNameBox.toolTip = "Enter the filename to load"
        loadingFormLayout.addRow("Landmark Filename:", self.loadingFileNameBox)

        self.manualLoadLayout = qt.QHBoxLayout()
        self.loadTxtButton = qt.QPushButton("Load from TXT")
        self.loadTxtButton.toolTip = "Load landmarks from the specified TXT file (Replaces current scene)"
        self.loadTxtButton.connect('clicked(bool)', self.onLoadFromTxtButton)
        self.manualLoadLayout.addWidget(self.loadTxtButton)
        loadingFormLayout.addRow("Manual Load:", self.manualLoadLayout)

        # Visualization Layout Buttons
        """Toggle Slice Visualization Button"""
        self.toggleSliceVisibilityButtonLayout = qt.QHBoxLayout()
        self.toggleRedSliceVisibilityButton = qt.QPushButton("RED")
        self.toggleRedSliceVisibilityButton.toolTip = "Turn on/off Red Slice Visualization in 3D Rendering"
        self.toggleYellowSliceVisibilityButton = qt.QPushButton("YELLOW")
        self.toggleYellowSliceVisibilityButton.toolTip = "Turn on/off Yellow Slice Visualization in 3D Rendering"
        self.toggleGreenSliceVisibilityButton = qt.QPushButton("GREEN")
        self.toggleGreenSliceVisibilityButton.toolTip = "Turn on/off Green Slice Visualization in 3D Rendering"
        self.toggleSliceVisibilityButtonLayout.addWidget(self.toggleRedSliceVisibilityButton)
        self.toggleSliceVisibilityButtonLayout.addWidget(self.toggleYellowSliceVisibilityButton)
        self.toggleSliceVisibilityButtonLayout.addWidget(self.toggleGreenSliceVisibilityButton)
        slicevizFormLayout.addRow(self.toggleSliceVisibilityButtonLayout)

        # Actions Layout Buttons        
        """Instruction Text"""
        x = qt.QLabel()
        x.setText("Helpful Controls:\n"
                  " - Hold SHIFT while hovering mouse to change slice intersection\n"
                  " - Right click and drag for zoom\n"
                  " - Left click and drag for image settings\n"
                  " - Click and drag points to move (only selected trajectory)\n"
                  " - Mouse scroll between slices\n")
        x.setWordWrap(True)

        actionsFormLayout.addRow(x)

        """Select Trajectory"""
        self.trajSelector = qt.QComboBox()
        self.trajSelector.addItem("Trajectory 1")
        self.trajSelector.currentIndexChanged.connect(self.onTrajSelectionChange)
        actionsFormLayout.addRow("Select Trajectory to Edit: ", self.trajSelector)

        """Add Trajectory Button"""
        self.addTrajectoryButton = qt.QPushButton("Add New Trajectory")
        actionsFormLayout.addRow(self.addTrajectoryButton)

        """Delete Trajectory Button"""
        self.deleteTrajectoryButton = qt.QPushButton("Delete Current Trajectory")
        actionsFormLayout.addRow(self.deleteTrajectoryButton)

        """Set Point Layout"""
        self.movePointsButtonLayout = qt.QHBoxLayout()
        self.movePointsLabelsLayout = qt.QHBoxLayout()
        """Set Target Point Button"""
        self.moveTargetToIntersectionButton = qt.QPushButton("CHANGE Target Point")
        self.moveTargetToIntersectionButton.toolTip = "Align slice intersections (hover while pressing shift may " \
                                                      "help). Click button to move target point here"
        self.moveTargetToIntersectionButton.enabled = True
        setTargetIcon = qt.QIcon(os.path.join(self.module_dir, 'Resources/Icons/setTarget.png'))
        self.moveTargetToIntersectionButton.setIcon(setTargetIcon)
        self.moveTargetToIntersectionButton.setIconSize(qt.QSize(50,50))
        self.movePointsButtonLayout.addWidget(self.moveTargetToIntersectionButton)

        """Set Entry Point Button"""
        self.moveEntryToIntersectionButton = qt.QPushButton("CHANGE Entry Point")
        self.moveEntryToIntersectionButton.toolTip = "Align slice intersections (hover while pressing shift may " \
                                                     "help). Click button to move target point here"
        self.moveEntryToIntersectionButton.enabled = True
        setEntryIcon = qt.QIcon(os.path.join(self.module_dir, 'Resources/Icons/setEntry.png'))
        self.moveEntryToIntersectionButton.setIcon(setEntryIcon)
        self.moveEntryToIntersectionButton.setIconSize(qt.QSize(50,50))
        x = qt.QLabel()
        x.setWordWrap(True)
        x.setText("Buttons below change the Target/Entry Point to the current slice intersection point. Hold SHIFT while hovering mouse to change slice itersection")
        self.movePointsLabelsLayout.addWidget(x)
        self.movePointsButtonLayout.addWidget(self.moveEntryToIntersectionButton)

        vizFormLayout.addRow(self.movePointsLabelsLayout)
        vizFormLayout.addRow(self.movePointsButtonLayout)

        self.jumpVizLabelsLayout = qt.QHBoxLayout()
        self.jumpVizButtonsLayout = qt.QHBoxLayout()

        x = qt.QLabel()
        x.setWordWrap(True)
        x.setText("Buttons below switch view to center on Target/Entry Point:")
        self.jumpVizLabelsLayout.addWidget(x)

        """Jump To Target Point Button"""
        self.jumpToTargetButton = qt.QPushButton("View Target Point")
        self.jumpToTargetButton.toolTip = "Press to see the target point in all slices"
        moveToTargetIcon = qt.QIcon(os.path.join(self.module_dir, 'Resources/Icons/moveToTarget.png'))
        self.jumpToTargetButton.setIcon(moveToTargetIcon)
        self.jumpToTargetButton.setIconSize(qt.QSize(50,50))
        self.jumpVizButtonsLayout.addWidget(self.jumpToTargetButton)

        """Jump To Entry Point Button"""
        self.jumpToEntryButton = qt.QPushButton("View Entry Point")
        self.jumpToEntryButton.toolTip = "Press to see the Entry point in all slices"
        moveToEntryIcon = qt.QIcon(os.path.join(self.module_dir, 'Resources/Icons/moveToEntry.png'))
        self.jumpToEntryButton.setIcon(moveToEntryIcon)
        self.jumpToEntryButton.setIconSize(qt.QSize(50,50))
        self.jumpVizButtonsLayout.addWidget(self.jumpToEntryButton)

        vizFormLayout.addRow(self.jumpVizLabelsLayout)
        vizFormLayout.addRow(self.jumpVizButtonsLayout)

        self.sliceVizLabelsLayout = qt.QHBoxLayout()
        self.sliceVizButtonsLayout = qt.QHBoxLayout()
        x = qt.QLabel()
        x.setWordWrap(True)
        x.setText("Buttons below change Slice Views:")
        self.sliceVizLabelsLayout.addWidget(x)

        """Standard View Button"""
        self.alignAxesToASCButton = qt.QPushButton("Standard")
        self.alignAxesToASCButton.toolTip = "Returns to default axial, sagittal, coronal slice views"

        standardViewIcon = qt.QIcon(os.path.join(self.module_dir, 'Resources/Icons/standard.png'))
        self.alignAxesToASCButton.setIcon(standardViewIcon)
        self.alignAxesToASCButton.setIconSize(qt.QSize(50, 50))
        self.sliceVizButtonsLayout.addWidget(self.alignAxesToASCButton)

        """Look Down Trajectory Button"""
        self.alignAxesToTrajectoryButton = qt.QPushButton("Down Trajectory")
        self.alignAxesToTrajectoryButton.toolTip = "Axial view switches to down-trajectory view. " \
                                                   "Other planes rotate by same amount to remain orthogonal"

        downTrajIcon = qt.QIcon(os.path.join(self.module_dir, 'Resources/Icons/downTraj.png'))
        self.alignAxesToTrajectoryButton.setIcon(downTrajIcon)
        self.alignAxesToTrajectoryButton.setIconSize(qt.QSize(50, 50))
        self.sliceVizButtonsLayout.addWidget(self.alignAxesToTrajectoryButton)

        vizFormLayout.addRow(self.sliceVizLabelsLayout)
        vizFormLayout.addRow(self.sliceVizButtonsLayout)

        self.crosshairNode = slicer.util.getNode('Crosshair')  # Make sure exists
        self.crosshairPos = self.crosshairNode.SetCrosshairRAS(0, 0, 0) # center the view

        # Connect buttons to callbacks
        self.moveTargetToIntersectionButton.connect('clicked(bool)', self.onMoveTargetToIntersectionButton)
        self.moveEntryToIntersectionButton.connect('clicked(bool)', self.onMoveEntryToIntersectionButton)
        self.jumpToTargetButton.connect('clicked(bool)', self.onJumpToTargetButton)
        self.jumpToEntryButton.connect('clicked(bool)', self.onJumpToEntryButton)

        self.alignAxesToTrajectoryButton.connect('clicked(bool)', self.onAlignAxesToTrajectoryButton)
        self.alignAxesToASCButton.connect('clicked(bool)', self.onAlignAxesToASCButton)

        self.toggleRedSliceVisibilityButton.connect('clicked(bool)', self.onToggleRedSliceVisibilityButton)
        self.toggleYellowSliceVisibilityButton.connect('clicked(bool)', self.onToggleYellowSliceVisibilityButton)
        self.toggleGreenSliceVisibilityButton.connect('clicked(bool)', self.onToggleGreenSliceVisibilityButton)

        self.addTrajectoryButton.connect('clicked(bool)', self.onAddTrajectoryButton)
        self.deleteTrajectoryButton.connect('clicked(bool)', self.onDeleteTrajectoryButton)

        self.toggleSliceIntersectionButton.connect('clicked(bool)', self.onToggleSliceIntersectionButton)
        
        self.main_layout.addStretch(1)

    def setup_scene(self):
        """Trajectory Line"""
        # Create or Get Shared Markup Node
        self.sharedMarkupNode = slicer.mrmlScene.GetFirstNodeByName("SurgeryPlannerLandmarks")
        if self.sharedMarkupNode:
            print("[TrajectoryPlanner] Found existing SurgeryPlannerLandmarks node")
            self.addSharedNodeObservers()
        else:
            print("[TrajectoryPlanner] SurgeryPlannerLandmarks node not found (will be created when needed)")
        
        self.trajList = np.array([]) # Initialize empty
        self.selectedTraj = None
        self.SelectedTrajObservers = []
        
        # Clear selector
        self.trajSelector.clear()

        self.redSliceNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.redSliceModifiedCallback)

    def ensureSharedMarkupNodeExists(self):
        if not self.sharedMarkupNode:
            self.sharedMarkupNode = slicer.mrmlScene.GetFirstNodeByName("SurgeryPlannerLandmarks")
        
        if not self.sharedMarkupNode:
            print("[TrajectoryPlanner] Creating new SurgeryPlannerLandmarks node")
            self.sharedMarkupNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
            self.sharedMarkupNode.SetName("SurgeryPlannerLandmarks")
            self.addSharedNodeObservers()
            
    def onAddTrajectoryButton(self):
        self.ensureSharedMarkupNodeExists()
        ep = np.array([100.0,100.0,100.0])
        tp = np.array([0.0,0.0,0.0])
        if self.trajSelector.count > 0:  # account for case when all traj deleted and add new one
            self.onAlignAxesToASCButton()
            if self.selectedTraj:
                old_ep = [0.0,0.0,0.0]
                old_tp = [0.0,0.0,0.0]
                
                idx_entry = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.EntryFiducialID)
                idx_target = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.targetFiducialID)
                
                if idx_entry >= 0:
                    self.sharedMarkupNode.GetNthControlPointPosition(idx_entry, old_ep)
                if idx_target >= 0:
                    self.sharedMarkupNode.GetNthControlPointPosition(idx_target, old_tp)
                    
                ep = old_ep + np.array([5.0,5.0,5.0])
                tp = old_tp + np.array([5.0,5.0,5.0])
      
        # Find lowest available ID
        used_ids = sorted([t.trajNum for t in self.trajList])
        new_id = 1
        for id in used_ids:
            if id == new_id:
                new_id += 1
            else:
                break

        newTraj = sh.SlicerTrajectoryModel(new_id, self.sharedMarkupNode, p_entry=np.array(ep), p_target=np.array(tp))
        self.trajList = np.append(self.trajList, newTraj)
        self.trajSelector.addItem("Trajectory " + str(new_id))
        self.trajSelector.setCurrentIndex(self.trajSelector.count-1)
        self.writeLandmarksToFile()

    def onDeleteTrajectoryButton(self):
        if self.trajSelector.count:  # don't do anything if no trajectories
            del_index = self.trajSelector.currentIndex
            self.trajList[del_index].deleteNodes()
            self.trajList = np.delete(self.trajList, del_index)
            self.selectedTraj = None
            self.trajSelector.removeItem(del_index)
            self.writeLandmarksToFile()

    def onToggleSliceIntersectionButton(self):
        self.logic.toggleSliceIntersection()

    def onToggleRedSliceVisibilityButton(self):
        self.logic.toggleSliceVisibility('Red')

    def onToggleYellowSliceVisibilityButton(self):
        self.logic.toggleSliceVisibility('Yellow')

    def onToggleGreenSliceVisibilityButton(self):
        self.logic.toggleSliceVisibility('Green')

    def onMoveTargetToIntersectionButton(self):
        if self.selectedTraj:
            idx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.targetFiducialID)
            if idx >= 0:
                self.logic.moveTargetToIntersectionButton(self.sharedMarkupNode, idx)

    def onMoveEntryToIntersectionButton(self):
        if self.selectedTraj:
            idx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.EntryFiducialID)
            if idx >= 0:
                self.logic.moveEntryToIntersectionButton(self.sharedMarkupNode, idx)

    def onJumpToTargetButton(self):
        if self.selectedTraj:
            idx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.targetFiducialID)
            if idx >= 0:
                self.logic.jumpToMarkup(self.sharedMarkupNode, idx)

    def onJumpToEntryButton(self):
        if self.selectedTraj:
            idx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.EntryFiducialID)
            if idx >= 0:
                self.logic.jumpToMarkup(self.sharedMarkupNode, idx)

    def onAlignAxesToTrajectoryButton(self):
        if self.selectedTraj:
            targetIdx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.targetFiducialID)
            entryIdx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.EntryFiducialID)
            if targetIdx >= 0 and entryIdx >= 0:
                self.logic.alignAxesWithTrajectory(self.sharedMarkupNode, targetIdx, self.sharedMarkupNode, entryIdx)
                self.onJumpToTargetButton()  # return crosshair to target point
                layoutManager = slicer.app.layoutManager()
                threeDWidget = layoutManager.threeDWidget(0)
                threeDView = threeDWidget.threeDView()
                threeDView.resetFocalPoint()
                self.downAxisBool = True

    def onAlignAxesToASCButton(self):
        if self.selectedTraj:
            idx = self.sharedMarkupNode.GetControlPointIndexByID(self.selectedTraj.targetFiducialID)
            if idx >= 0:
                self.logic.resetAxesToASC(self.sharedMarkupNode, idx)
                self.onJumpToTargetButton()  # return crosshair to target point
        
        self.downAxisBool = False

    def onTrajSelectionChange(self, index):
        if self.selectedTraj:  # skips for delete case
            self.onAlignAxesToASCButton()
            self.selectedTraj.deselect()
        # Observers are now global on the shared node, so we don't need to remove/add them per trajectory
        if index >= 0:
            self.selectedTraj = self.trajList[index]
            self.addSelectedTrajObservers(self.selectedTraj)
            self.selectedTraj.select()
            self.onJumpToTargetButton()

    def redSliceModifiedCallback(self, caller, event):
        pass

    def addSelectedTrajObservers(self, traj):
        # We now observe the shared node for all interactions
        # But we might want to know when the specific points of THIS trajectory are modified
        # For now, we rely on the shared node observer added in setup or assume global handling
        pass
        
    def addSharedNodeObservers(self):
        # Add observer to shared node for end interaction events
        if self.sharedMarkupNode:
            self.sharedMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointEndInteractionEvent,
                                              self.onLandmarkEndInteraction)
            self.sharedMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
                                              self.onLandmarkModified)

    def onLandmarkEndInteraction(self, caller, event):
        self.writeLandmarksToFile()
        
        # TODO: Handle "Look Down Trajectory" logic here if needed
        # This requires identifying which point was moved and if it belongs to the selected trajectory
        # For now, we skip the complex "Look Down" update on interaction end for simplicity in this refactor
        # unless we can easily get the point ID.
        
    def onLandmarkModified(self, caller, event):
        # Handle real-time updates if needed
        pass
    
    def load_config(self):
        config_path = os.path.join(self.module_dir, 'Resources', 'config.yaml')
        default_config = {
            'output_file': '/tmp/slicer_surgery_planner_points.txt',
            'write_frequency_hz': 10,
            'coordinate_system': 'RAS',
            'landmarks': ['Entry_1', 'Target_1']
        }
        
        if not os.path.exists(config_path):
            print(f"Config file not found at {config_path}, using defaults")
            return default_config
            
        try:
            if yaml:
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                    print(f"Loaded config from {config_path}")
                    return full_config.get('trajectory_planner', default_config)
            else:
                # Simple manual parser for nested structure
                config = default_config.copy()
                in_section = False
                with open(config_path, 'r') as f:
                    for line in f:
                        line = line.rstrip()
                        if not line or line.strip().startswith('#'): continue
                        
                        # Check for section headers (no indentation)
                        if not line.startswith(' ') and line.endswith(':'):
                            if line.strip() == 'trajectory_planner:':
                                in_section = True
                            else:
                                in_section = False
                            continue
                        
                        if in_section and ':' in line:
                            parts = line.split(':', 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            
                            # Handle simple types
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.isdigit():
                                value = int(value)
                            
                            config[key] = value
                                
                print(f"Loaded config using simple parser from {config_path}")
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def writeLandmarksToFile(self, output_file=None):
        try:
            if output_file is None:
                output_file = self.temp_landmark_file
            coord_sys = self.config.get('coordinate_system', 'RAS')
            
            with open(output_file, 'w') as f:
                # Write Header
                f.write(f"# SurgeryPlanner Landmarks Output\n")
                f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"# CoordinateSystem: {coord_sys}\n")
                f.write("Trajectory,Landmark,X,Y,Z\n")
                
                # Write Data from Shared Node
                if self.sharedMarkupNode:
                    n = self.sharedMarkupNode.GetNumberOfControlPoints()
                    for i in range(n):
                        label = self.sharedMarkupNode.GetNthControlPointLabel(i)
                        
                        # Parse trajectory name from label (e.g. Target_1 -> traj_1)
                        traj_name = "unknown"
                        if "_" in label:
                            parts = label.split("_")
                            if len(parts) > 1:
                                traj_name = "traj_" + parts[-1]
                        
                        pos = np.array([0.0, 0.0, 0.0])
                        self.sharedMarkupNode.GetNthControlPointPosition(i, pos)
                        f.write(f"{traj_name},{label},{pos[0]:.4f},{pos[1]:.4f},{pos[2]:.4f}\n")
                    
            print(f"Updated landmarks in {output_file}")
            
        except Exception as e:
            print(f"Failed to write landmarks to file: {e}")

    def onSaveAsTxtButton(self):
        output_dir = self.outputDirSelector.currentPath
        output_filename = self.outputFileNameBox.text
        if not output_dir or not output_filename:
            print("Please specify a valid destination folder and filename.")
            return
        
        output_file = os.path.join(output_dir, output_filename)
        self.writeLandmarksToFile(output_file)
        print(f"Manually saved TXT to {output_file}")

    def onSaveAsFcsvButton(self):
        output_dir = self.outputDirSelector.currentPath
        output_filename = self.outputFileNameBox.text
        if not output_dir or not output_filename:
            print("Please specify a valid destination folder and filename.")
            return
            
        # Ensure extension is .fcsv
        base, ext = os.path.splitext(output_filename)
        if ext.lower() != '.fcsv':
            output_filename = base + '.fcsv'
            
        output_file = os.path.join(output_dir, output_filename)
        
        if self.sharedMarkupNode:
            slicer.util.saveNode(self.sharedMarkupNode, output_file)
            print(f"Manually saved FCSV to {output_file}")
        else:
            print("No landmarks to save.")

    def clearAllTrajectories(self):
        # Remove all trajectories
        while self.trajSelector.count > 0:
             self.onDeleteTrajectoryButton()

    def onLoadFromTxtButton(self):
        self.ensureSharedMarkupNodeExists()
        output_dir = self.loadingDirSelector.currentPath
        output_filename = self.loadingFileNameBox.text
        if not output_dir or not output_filename:
            print("Please specify a valid loading folder and filename.")
            return
        
        filepath = os.path.join(output_dir, output_filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return

        ret = qt.QMessageBox.warning(None, "Load Landmarks", 
                                     "This will remove all current landmarks in the scene. Do you want to proceed?",
                                     qt.QMessageBox.Yes | qt.QMessageBox.No)
        if ret == qt.QMessageBox.No:
            return

        self.clearAllTrajectories()

        try:
            traj_data = {} # id -> {label: pos}
            with open(filepath, 'r') as f:
                for line in f:
                    if line.startswith('#') or "Trajectory,Landmark,X,Y,Z" in line:
                        continue
                    parts = line.strip().split(',')
                    if len(parts) >= 5:
                        traj_name = parts[0] # traj_1
                        label = parts[1] # Target_1
                        x, y, z = float(parts[2]), float(parts[3]), float(parts[4])
                        
                        # Extract ID
                        if "_" in traj_name:
                            tid = int(traj_name.split('_')[-1])
                            if tid not in traj_data:
                                traj_data[tid] = {}
                            traj_data[tid][label] = [x, y, z]

            # Reconstruct
            for tid in sorted(traj_data.keys()):
                self.onAddTrajectoryButton() # Will create ID 1, then 2, etc. if we cleared everything
                
                current_traj = self.trajList[-1] # The one we just added
                points = traj_data[tid]
                
                idx_target = self.sharedMarkupNode.GetControlPointIndexByID(current_traj.targetFiducialID)
                idx_entry = self.sharedMarkupNode.GetControlPointIndexByID(current_traj.EntryFiducialID)
                
                target_pos = None
                entry_pos = None
                
                for lbl, pos in points.items():
                    if "Target" in lbl:
                        target_pos = pos
                    elif "Entry" in lbl:
                        entry_pos = pos
                
                if target_pos and idx_target >= 0:
                    self.sharedMarkupNode.SetNthControlPointPosition(idx_target, target_pos[0], target_pos[1], target_pos[2])
                if entry_pos and idx_entry >= 0:
                    self.sharedMarkupNode.SetNthControlPointPosition(idx_entry, entry_pos[0], entry_pos[1], entry_pos[2])
            
            print(f"Loaded landmarks from {filepath}")

        except Exception as e:
            print(f"Failed to load landmarks: {e}")
