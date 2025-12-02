import qt
import ctk
import slicer
from .SurgeryPlannerLogic import SurgeryPlannerLogic

class SegmentationPlannerWidget(qt.QWidget):
    def __init__(self, parent=None, logic=None, module_dir=None):
        super(SegmentationPlannerWidget, self).__init__(parent)
        self.logic = logic if logic else SurgeryPlannerLogic()
        self.module_dir = module_dir
        
        self.setup_ui()
        
    def setup_ui(self):
        self.main_layout = qt.QVBoxLayout(self)
        
        # Actions (Segmentation)
        segActionsCollapsibleButton = ctk.ctkCollapsibleButton()
        segActionsCollapsibleButton.text = "Segmentation Actions"
        self.main_layout.addWidget(segActionsCollapsibleButton)
        segActionsFormLayout = qt.QFormLayout(segActionsCollapsibleButton)

        self.addSegmentationButton = qt.QPushButton("Add Segmentation")
        self.addSegmentationButton.connect('clicked(bool)', self.onAddSegmentation)
        segActionsFormLayout.addRow(self.addSegmentationButton)

        self.removeSegmentationButton = qt.QPushButton("Remove Segmentation")
        self.removeSegmentationButton.connect('clicked(bool)', self.onRemoveSegmentation)
        segActionsFormLayout.addRow(self.removeSegmentationButton)
        
        self.main_layout.addStretch(1)

    def onAddSegmentation(self):
        # Create a new segmentation node
        segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentationNode.CreateDefaultDisplayNodes() # Needed for display
        segmentationNode.SetName("SurgeryPlannerSegmentation")
        print("Added new segmentation node")

    def onRemoveSegmentation(self):
        # Remove the last added segmentation node (simple logic for now)
        # In a real app, we might want a selector like for trajectories
        nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        # Filter for nodes we likely created or just take the last one
        if nodes:
            # Sort by ID or creation time if possible, or just take the last one in the list
            # Slicer usually appends new nodes
            node_to_remove = nodes[-1] 
            slicer.mrmlScene.RemoveNode(node_to_remove)
            print(f"Removed segmentation node: {node_to_remove.GetName()}")
        else:
            print("No segmentation nodes to remove")
