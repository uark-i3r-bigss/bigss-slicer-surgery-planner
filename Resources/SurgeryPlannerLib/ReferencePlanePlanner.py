import os
import qt
import ctk
import slicer
import vtk
import numpy as np
from datetime import datetime
from .SurgeryPlannerLogic import SurgeryPlannerLogic

try:
    import yaml
except ImportError:
    yaml = None

class ReferencePlanePlannerWidget(qt.QWidget):
    def __init__(self, parent=None, logic=None, module_dir=None):
        super(ReferencePlanePlannerWidget, self).__init__(parent)
        self.logic = logic if logic else SurgeryPlannerLogic()
        self.module_dir = module_dir
        if not self.module_dir:
            self.module_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            
        # Load Config
        self.config = self.load_config()
        self.temp_plane_file = self.config.get('output_plane_file', '/tmp/slicer_surgery_planner_planes.txt')
        
        # Define colors for cycling (R, G, B)
        self.plane_colors = [
            (0, 1, 1),   # Cyan
            (1, 1, 0),   # Yellow
            (0, 1, 0),   # Green
            (1, 0, 1),   # Magenta
            (1, 0.5, 0), # Orange
            (0.5, 0.5, 1), # Light Blue
            (1, 0.8, 0.8)  # Light Red
        ]
        
        self.setup_ui()
        self.setup_scene()
        
    def setup_ui(self):
        self.main_layout = qt.QVBoxLayout(self)
        
        # Actions (Reference Plane)
        planeActionsCollapsibleButton = ctk.ctkCollapsibleButton()
        planeActionsCollapsibleButton.text = "Reference Plane Actions"
        self.main_layout.addWidget(planeActionsCollapsibleButton)
        planeActionsFormLayout = qt.QFormLayout(planeActionsCollapsibleButton)

        self.addPlaneButton = qt.QPushButton("Add Reference Plane")
        self.addPlaneButton.connect('clicked(bool)', self.onAddPlane)
        planeActionsFormLayout.addRow(self.addPlaneButton)

        self.deletePlaneButton = qt.QPushButton("Delete Reference Plane")
        self.deletePlaneButton.connect('clicked(bool)', self.onDeletePlane)
        planeActionsFormLayout.addRow(self.deletePlaneButton)
        
        # Size Controls
        sizeCollapsibleButton = ctk.ctkCollapsibleButton()
        sizeCollapsibleButton.text = "Plane Size"
        self.main_layout.addWidget(sizeCollapsibleButton)
        sizeFormLayout = qt.QFormLayout(sizeCollapsibleButton)
        
        self.widthSpinBox = qt.QDoubleSpinBox()
        self.widthSpinBox.setRange(1.0, 500.0)
        self.widthSpinBox.setValue(150.0) # Default 150mm
        self.widthSpinBox.setSuffix(" mm")
        sizeFormLayout.addRow("Width:", self.widthSpinBox)
        
        self.heightSpinBox = qt.QDoubleSpinBox()
        self.heightSpinBox.setRange(1.0, 500.0)
        self.heightSpinBox.setValue(150.0) # Default 150mm
        self.heightSpinBox.setSuffix(" mm")
        sizeFormLayout.addRow("Height:", self.heightSpinBox)
        
        self.setSizeButton = qt.QPushButton("Set Size")
        self.setSizeButton.connect('clicked(bool)', self.onSetSize)
        sizeFormLayout.addRow(self.setSizeButton)
        
        # Saving Controls
        savingCollapsibleButton = ctk.ctkCollapsibleButton()
        savingCollapsibleButton.text = "Reference Plane Saving"
        self.main_layout.addWidget(savingCollapsibleButton)
        savingFormLayout = qt.QFormLayout(savingCollapsibleButton)
        
        """Destination Folder Selector"""
        default_dir = os.path.expanduser('~/slicer_annotations')
        default_filename = "reference_planes.txt"
        
        self.outputDirSelector = ctk.ctkPathLineEdit()
        self.outputDirSelector.filters = ctk.ctkPathLineEdit.Dirs
        self.outputDirSelector.toolTip = "Select the folder to save the planes output file"
        self.outputDirSelector.currentPath = default_dir
        savingFormLayout.addRow("Destination Folder:", self.outputDirSelector)

        """Destination Filename Box"""
        self.outputFileNameBox = qt.QLineEdit()
        self.outputFileNameBox.text = default_filename
        self.outputFileNameBox.toolTip = "Enter the filename for the planes output file"
        savingFormLayout.addRow("Destination Filename:", self.outputFileNameBox)

        """Manual Save Buttons"""
        self.manualSaveLayout = qt.QHBoxLayout()
        self.saveAsTxtButton = qt.QPushButton("Save as TXT")
        self.saveAsTxtButton.toolTip = "Save current planes to the specified TXT file"
        self.saveAsTxtButton.connect('clicked(bool)', self.onSaveAsTxtButton)
        self.manualSaveLayout.addWidget(self.saveAsTxtButton)
        savingFormLayout.addRow("Manual Save:", self.manualSaveLayout)

        """Auto-Save Info"""
        self.autoSaveLabel = qt.QLabel(self.temp_plane_file)
        self.autoSaveLabel.toolTip = "Location of the continuous auto-save file"
        savingFormLayout.addRow("Auto-Save Location:", self.autoSaveLabel)
        
        self.main_layout.addStretch(1)

    def setup_scene(self):
        # Add observers to existing planes if any (e.g. after reload)
        nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
        for node in nodes:
            self.addPlaneObservers(node)

    def addPlaneObservers(self, node):
        # Observe modification events to trigger auto-save
        if not node.HasObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent):
            node.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.onPlaneModified)
        if not node.HasObserver(slicer.vtkMRMLMarkupsNode.PointEndInteractionEvent):
            node.AddObserver(slicer.vtkMRMLMarkupsNode.PointEndInteractionEvent, self.onPlaneModified)
        if not node.HasObserver(vtk.vtkCommand.ModifiedEvent):
             pass

    def onPlaneModified(self, caller, event):
        self.writePlanesToFile()

    def getNextPlaneIndex(self):
        # Find the next available index X for ReferencePlane_{X}
        nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
        existing_indices = []
        for node in nodes:
            name = node.GetName()
            if name.startswith("ReferencePlane_"):
                try:
                    idx = int(name.split("_")[1])
                    existing_indices.append(idx)
                except ValueError:
                    pass
        
        if not existing_indices:
            return 1
        
        return max(existing_indices) + 1

    def onAddPlane(self):
        print("[ReferencePlanePlanner] onAddPlane called")
        try:
            idx = self.getNextPlaneIndex()
            plane_name = f"ReferencePlane_{idx}"
            center_name = f"ReferencePlane_{idx}_center"
            
            planeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsPlaneNode")
            planeNode.SetName(plane_name)
            print(f"[ReferencePlanePlanner] Created node: {planeNode.GetID()} ({plane_name})")
            
            # Ensure display node exists
            planeNode.CreateDefaultDisplayNodes()
            displayNode = planeNode.GetDisplayNode()
            if displayNode:
                print("[ReferencePlanePlanner] Setting display properties")
                
                # Pick color based on index
                color_idx = (idx - 1) % len(self.plane_colors)
                color = self.plane_colors[color_idx]
                
                displayNode.SetGlyphScale(1.0) 
                displayNode.SetOpacity(0.5)    
                displayNode.SetSelectedColor(color[0], color[1], color[2]) 
                displayNode.SetColor(color[0], color[1], color[2])
                
                # Enable Interaction Handles
                displayNode.SetHandlesInteractive(True)
                displayNode.SetRotationHandleVisibility(True)
                displayNode.SetTranslationHandleVisibility(True)
                
                # Disable Scale Handles to enforce fixed size via UI
                displayNode.SetScaleHandleVisibility(False)
            
            planeNode.RemoveAllControlPoints()
            print(f"[ReferencePlanePlanner] Adding Center control point: {center_name}")
            planeNode.AddControlPoint(0, 0, 0)
            planeNode.SetNthControlPointLabel(0, center_name)
            
            # Set Initial Size
            width = self.widthSpinBox.value
            height = self.heightSpinBox.value
            planeNode.SetSize(width, height)
            
            # Add observers
            self.addPlaneObservers(planeNode)
            
            # Trigger save
            self.writePlanesToFile()
            
            print("[ReferencePlanePlanner] Plane added successfully")
            
        except Exception as e:
            print(f"[ReferencePlanePlanner] Error adding plane: {e}")
            import traceback
            traceback.print_exc()
            qt.QMessageBox.warning(self, "Error", f"Could not create Reference Plane: {e}")

    def onSetSize(self):
        # Update size of the last added plane (or selected if we had a selector)
        nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
        if not nodes:
            print("[ReferencePlanePlanner] No plane to resize")
            return

        # Ideally we'd have a selector, but for now take the last one
        planeNode = nodes[-1]
        width = self.widthSpinBox.value
        height = self.heightSpinBox.value
        
        print(f"[ReferencePlanePlanner] Setting size for {planeNode.GetName()} to {width}x{height}")
        planeNode.SetSize(width, height)
        self.writePlanesToFile()

    def onDeletePlane(self):
        print("[ReferencePlanePlanner] onDeletePlane called")
        # Remove the last added plane node
        nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
        if nodes:
            # Sort by ID or creation time if possible, or just take the last one in the list
            node_to_remove = nodes[-1] 
            slicer.mrmlScene.RemoveNode(node_to_remove)
            print(f"[ReferencePlanePlanner] Removed Reference Plane: {node_to_remove.GetName()}")
            self.writePlanesToFile()
        else:
            print("[ReferencePlanePlanner] No Reference Plane nodes to remove")

    def load_config(self):
        config_path = os.path.join(self.module_dir, 'Resources', 'config.yaml')
        default_config = {
            'output_plane_file': '/tmp/slicer_surgery_planner_planes.txt',
            'coordinate_system': 'RAS',
            'default_width': 150.0,
            'default_height': 150.0
        }
        
        if not os.path.exists(config_path):
            return default_config
            
        try:
            if yaml:
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                    return full_config.get('reference_plane_planning', default_config)
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
                            if line.strip() == 'reference_plane_planning:':
                                in_section = True
                            else:
                                in_section = False
                            continue
                        
                        if in_section and ':' in line:
                            parts = line.split(':', 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.replace('.', '', 1).isdigit():
                                value = float(value)
                                
                            config[key] = value
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def writePlanesToFile(self, output_file=None):
        try:
            if output_file is None:
                output_file = self.temp_plane_file
            
            coord_sys = self.config.get('coordinate_system', 'RAS')
            
            with open(output_file, 'w') as f:
                # Write Header
                f.write(f"# SurgeryPlanner Reference Planes Output\n")
                f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"# CoordinateSystem: {coord_sys}\n")
                f.write("PlaneName,Matrix00,Matrix01,Matrix02,Matrix03,Matrix10,Matrix11,Matrix12,Matrix13,Matrix20,Matrix21,Matrix22,Matrix23,Matrix30,Matrix31,Matrix32,Matrix33,Width,Height\n")
                
                # Write Data
                nodes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
                for node in nodes:
                    name = node.GetName()
                    
                    # Get Object to World Matrix (includes position and rotation)
                    mat = vtk.vtkMatrix4x4()
                    node.GetObjectToWorldMatrix(mat)
                    
                    # Convert to LPS if needed
                    if coord_sys == 'LPS':
                        # M_LPS = T * M_RAS * T where T = diag(-1, -1, 1, 1)
                        # Flip signs of 0,2; 0,3; 1,2; 1,3; 2,0; 2,1; 3,0; 3,1
                        
                        # Row 0 (X)
                        mat.SetElement(0, 2, -mat.GetElement(0, 2))
                        mat.SetElement(0, 3, -mat.GetElement(0, 3))
                        
                        # Row 1 (Y)
                        mat.SetElement(1, 2, -mat.GetElement(1, 2))
                        mat.SetElement(1, 3, -mat.GetElement(1, 3))
                        
                        # Row 2 (Z)
                        mat.SetElement(2, 0, -mat.GetElement(2, 0))
                        mat.SetElement(2, 1, -mat.GetElement(2, 1))
                        
                        # Row 3
                        mat.SetElement(3, 0, -mat.GetElement(3, 0))
                        mat.SetElement(3, 1, -mat.GetElement(3, 1))
                    
                    # Get Size
                    size = node.GetSize()
                    width = size[0]
                    height = size[1]
                    
                    # Flatten matrix
                    mat_str = ""
                    for r in range(4):
                        for c in range(4):
                            mat_str += f"{mat.GetElement(r, c):.4f},"
                    
                    f.write(f"{name},{mat_str}{width:.4f},{height:.4f}\n")
                    
            print(f"[ReferencePlanePlanner] Updated planes in {output_file}")
            
        except Exception as e:
            print(f"[ReferencePlanePlanner] Failed to write planes to file: {e}")

    def onSaveAsTxtButton(self):
        output_dir = self.outputDirSelector.currentPath
        output_filename = self.outputFileNameBox.text
        if not output_dir or not output_filename:
            print("Please specify a valid destination folder and filename.")
            return
        
        output_file = os.path.join(output_dir, output_filename)
        self.writePlanesToFile(output_file)
        print(f"Manually saved Planes TXT to {output_file}")
