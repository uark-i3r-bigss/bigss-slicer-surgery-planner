""" slicer_helper
Author: Henry Phalen

BSD 3-Clause License

Copyright (c) 2020, Henry Phalen
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 """

import slicer
import vtk
import time
import numpy as np
import os

"""The following block of functions are from slicer.util, but are not included in the current 4.10 code base. 
They are quite helpful so I am housing them here until they are returned to the main code
https://github.com/Slicer/Slicer/blob/467c4318a114a9165826ab738e7c34a4753327e0/Base/Python/slicer/util.py#L1399"""


def arrayFromVTKMatrix(vmatrix):
    """Return vtkMatrix4x4 or vtkMatrix3x3 elements as numpy array.
  The returned array is just a copy and so any modification in the array will not affect the input matrix.
  To set VTK matrix from a numpy array, use :py:meth:`vtkMatrixFromArray` or
  :py:meth:`updateVTKMatrixFromArray`.
  """
    from vtk import vtkMatrix4x4
    from vtk import vtkMatrix3x3
    import numpy as np
    if isinstance(vmatrix, vtkMatrix4x4):
        matrixSize = 4
    elif isinstance(vmatrix, vtkMatrix3x3):
        matrixSize = 3
    else:
        raise RuntimeError("Input must be vtk.vtkMatrix3x3 or vtk.vtkMatrix4x4")
    narray = np.eye(matrixSize)
    vmatrix.DeepCopy(narray.ravel(), vmatrix)
    return narray


def vtkMatrixFromArray(narray):
    """Create VTK matrix from a 3x3 or 4x4 numpy array.
  :param narray: input numpy array
  The returned matrix is just a copy and so any modification in the array will not affect the output matrix.
  To set numpy array from VTK matrix, use :py:meth:`arrayFromVTKMatrix`.
  """
    from vtk import vtkMatrix4x4
    from vtk import vtkMatrix3x3
    narrayshape = narray.shape
    if narrayshape == (4, 4):
        vmatrix = vtkMatrix4x4()
        updateVTKMatrixFromArray(vmatrix, narray)
        return vmatrix
    elif narrayshape == (3, 3):
        vmatrix = vtkMatrix3x3()
        updateVTKMatrixFromArray(vmatrix, narray)
        return vmatrix
    else:
        raise RuntimeError("Unsupported numpy array shape: " + str(narrayshape) + " expected (4,4)")


def updateVTKMatrixFromArray(vmatrix, narray):
    """Update VTK matrix values from a numpy array.
  :param vmatrix: VTK matrix (vtkMatrix4x4 or vtkMatrix3x3) that will be update
  :param narray: input numpy array
  To set numpy array from VTK matrix, use :py:meth:`arrayFromVTKMatrix`.
  """
    from vtk import vtkMatrix4x4
    from vtk import vtkMatrix3x3
    if isinstance(vmatrix, vtkMatrix4x4):
        matrixSize = 4
    elif isinstance(vmatrix, vtkMatrix3x3):
        matrixSize = 3
    else:
        raise RuntimeError("Output vmatrix must be vtk.vtkMatrix3x3 or vtk.vtkMatrix4x4")
    if narray.shape != (matrixSize, matrixSize):
        raise RuntimeError("Input narray size must match output vmatrix size ({0}x{0})".format(matrixSize))
    vmatrix.DeepCopy(narray.ravel())


def arrayFromTransformMatrix(transformNode, toWorld=False):
    """Return 4x4 transformation matrix as numpy array.
  :param toWorld: if set to True then the transform to world coordinate system is returned
    (effect of parent transform to the node is applied), otherwise transform to parent transform is returned.
  The returned array is just a copy and so any modification in the array will not affect the transform node.
  To set transformation matrix from a numpy array, use :py:meth:`updateTransformMatrixFromArray`.
  """
    import numpy as np
    from vtk import vtkMatrix4x4
    vmatrix = vtkMatrix4x4()
    if toWorld:
        success = transformNode.GetMatrixTransformToWorld(vmatrix)
    else:
        success = transformNode.GetMatrixTransformToParent(vmatrix)
    if not success:
        raise RuntimeError("Failed to get transformation matrix from node " + transformNode.GetID())
    return arrayFromVTKMatrix(vmatrix)


def updateTransformMatrixFromArray(transformNode, narray, toWorld=False):
    """Set transformation matrix from a numpy array of size 4x4 (toParent).
  :param world: if set to True then the transform will be set so that transform
    to world matrix will be equal to narray; otherwise transform to parent will be
    set as narray.
  """
    import numpy as np
    from vtk import vtkMatrix4x4
    narrayshape = narray.shape
    if narrayshape != (4, 4):
        raise RuntimeError("Unsupported numpy array shape: " + str(narrayshape) + " expected (4,4)")
    if toWorld and transformNode.GetParentTransformNode():
        # thisToParent = worldToParent * thisToWorld = inv(parentToWorld) * toWorld
        narrayParentToWorld = arrayFromTransformMatrix(transformNode.GetParentTransformNode())
        thisToParent = np.dot(np.linalg.inv(narrayParentToWorld), narray)
        updateTransformMatrixFromArray(transformNode, thisToParent, toWorld=False)
    else:
        vmatrix = vtkMatrix4x4()
        updateVTKMatrixFromArray(vmatrix, narray)
        transformNode.SetMatrixTransformToParent(vmatrix)


"""My custom code below"""


def make_igtl_node(ip, port, name):
    """ Creates an IGT_link node in Slicer that can be used to communicate with e.g. ROS
    INPUT: ip   [str]  - IP address, (accepts 'localhost')
           port [int]  - Port number
           name [str]  - Connector name
    OUPUT: igtl_connector [vtkMRMLIGTLConnectorNode] """
    igtl_connector = slicer.vtkMRMLIGTLConnectorNode()
    slicer.mrmlScene.AddNode(igtl_connector)
    igtl_connector.SetName(name)
    igtl_connector.SetTypeClient(ip, port)
    igtl_connector.Start()
    return igtl_connector


def get_markup_node_pos_from_fcsv(filename):
    f = open(filename, "r")
    f.readline()
    f.readline()
    f.readline()
    data = f.readline()
    print(data)
    data = data.split(',')
    pos = np.array([float(data[1]), float(data[2]), float(data[3])])
    return pos

def copy_fcsv_to_new_line(name, write_file):
    f = open(name, 'r')
    f.readline()
    f.readline()
    f.readline()
    data = f.readline()
    data = data.split(',')
    data = data[1:]
    newline = 'vtkMRMLMarkupsFiducialNode_1,' + ','.join(data)
    write_file.write(newline)
    f.close()

def collapse_traj_markups_to_single_fcsv(data_dir,new_name):
    dir_list = [x[0] for x in os.walk(data_dir)]
    if len(dir_list) > 1:
        print(dir_list)
        dir_list = dir_list[1:]  # skip 0th (self) entry if a dir of dirs  # TODO: could clean up implementation
    f_write = open(data_dir + '/' + new_name + '.fcsv', 'w')
    f_write.write('# Markups fiducial file version = 4.10 \n# CoordinateSystem = 0\n# columns = id,x,y,z,ow,ox,oy,oz,vis,sel,lock,label,desc,associatedNodeID\n')
    for traj_dir in dir_list:
        copy_fcsv_to_new_line(traj_dir + '/Entry.fcsv', f_write)
        copy_fcsv_to_new_line(traj_dir + '/Target.fcsv', f_write)
    f_write.close()





class SlicerVolumeModel:
    """ Takes a volume (nrrd, perhaps others), imports it into Slicer as segment. Allows for voxel manipulation from np
    array """

    def __init__(self, volume_filename):
        """INPUT: volume_filename  [str] - filename with given mesh - accepts .stl and .dae """
        _, self.label_volumeNode = slicer.util.loadLabelVolume(volume_filename, returnNode=True)
        # This is adapted from https://www.slicer.org/wiki/Documentation/4.3/Modules/VolumeRendering
        # The effect is that the volume rendering changes when the segmentation array changes
        slicer_logic = slicer.modules.volumerendering.logic()
        self.displayNode = slicer_logic.CreateVolumeRenderingDisplayNode()
        slicer.mrmlScene.AddNode(self.displayNode)
        self.displayNode.UnRegister(slicer_logic)
        slicer_logic.UpdateDisplayNodeFromVolumeNode(self.displayNode, self.label_volumeNode)
        self.label_volumeNode.AddAndObserveDisplayNodeID(self.displayNode.GetID())
        self.voxel_array = slicer.util.arrayFromVolume(self.label_volumeNode)
        self.imageData=volumeNode.GetImageData()
        self.voxel_extent = self.imageData.GetExtent()

    def register_visual_change(self):
        """ Method to call after changing self.voxel_array so that the visualizations update """
        self.label_volumeNode.Modified()  # Updates the visualizations
        self.displayNode.Modified()


class SlicerTrajectoryModel:
    """Makes a line object as a vtkMRMLModelNode"""

    def __init__(self, trajNum, sharedMarkupNode, p_entry=np.array([0.0, 0.0, 0.0]), p_target=np.array([100.0, 100.0, 100.0])):
        self.trajNum = trajNum
        self.selected_bool = True
        self.line = vtk.vtkLineSource()
        modelsLogic = slicer.modules.models.logic()
        self.lineModelNode = modelsLogic.AddModel(self.line.GetOutput())
        self.lineModelNode.GetDisplayNode().SetVisibility2D(True)
        self.lineModelNode.GetDisplayNode().SetLineWidth(3)
        self.lineModelNode.GetDisplayNode().SetSliceDisplayModeToProjection()
        self.lineModelNode.GetDisplayNode().SetColor(0, 1, 1)
        self.lineModelNode.SetName('Trajectory ' + str(trajNum))

        self.sharedMarkupNode = sharedMarkupNode
        
        # Add Target Point
        n = self.sharedMarkupNode.AddControlPoint(p_target[0], p_target[1], p_target[2])
        self.sharedMarkupNode.SetNthControlPointLabel(n, "Target_" + str((trajNum)))
        self.targetFiducialID = self.sharedMarkupNode.GetNthControlPointID(n)

        # Add Entry Point
        n = self.sharedMarkupNode.AddControlPoint(p_entry[0], p_entry[1], p_entry[2])
        self.sharedMarkupNode.SetNthControlPointLabel(n, "Entry_" + str(trajNum))
        self.EntryFiducialID = self.sharedMarkupNode.GetNthControlPointID(n)

        # Observers
        self.sharedMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
                                          self.markupModifiedCallback)
        

        # Initial update
        self.updateLine()


    def select(self):
        self.lineModelNode.GetDisplayNode().SetVisibility2D(True)
        self.selected_bool = True
        # Locking individual points in a shared list is tricky, usually we lock the whole list or specific points
        # For now, we will assume the shared list is unlocked or managed externally

    def deselect(self):
        self.lineModelNode.GetDisplayNode().SetVisibility2D(False)
        self.selected_bool = False

    def markupModifiedCallback(self, caller, event):
        # Check if the modified point is one of ours
        # Note: PointModifiedEvent passes the node as caller. We need to check which point changed if possible,
        # but vtkMRMLMarkupsNode.PointModifiedEvent doesn't always give easy access to WHICH point changed in python easily without checking all.
        # However, for simple line update, we can just update.
        self.updateLine()
        

    def updateLine(self):
        pos1 = [0.0, 0.0, 0.0]
        pos2 = [0.0, 0.0, 0.0]
        
        idx1 = self.sharedMarkupNode.GetControlPointIndexByID(self.targetFiducialID)
        idx2 = self.sharedMarkupNode.GetControlPointIndexByID(self.EntryFiducialID)
        
        if idx1 >= 0 and idx2 >= 0:
            self.sharedMarkupNode.GetNthControlPointPosition(idx1, pos1)
            self.sharedMarkupNode.GetNthControlPointPosition(idx2, pos2)
            
            self.line.SetPoint1(pos1)
            self.line.SetPoint2(pos2)
            self.line.Update()

    def UpdateTransforms(self):
        pass
        # entry_transform = np.eye(4)
        # entry_transform[0:3, 0] = x_vec
        # entry_transform[0:3, 1] = y_vec
        # entry_transform[0:3, 2] = z_vec
        # entry_transform[0:3, 3] = entry_pos
        #
        # sh.updateTransformMatrixFromArray(self.entry_transform_node, entry_transform)
        #
        # robot_ee_target_transform = np.matmul(np.linalg.inv(hand_eye_transform), transform)
        # sh.updateTransformMatrixFromArray(self.robot_ee_target, robot_ee_target_transform)
        #
        # robot_ee_entry_transform = np.matmul(np.linalg.inv(hand_eye_transform), entry_transform)
        # sh.updateTransformMatrixFromArray(self.robot_ee_entry, robot_ee_entry_transform)


    def deleteNodes(self):
        slicer.mrmlScene.RemoveNode(self.lineModelNode)
        # Remove points from shared node
        idx1 = self.sharedMarkupNode.GetControlPointIndexByID(self.targetFiducialID)
        if idx1 >= 0:
            self.sharedMarkupNode.RemoveNthControlPoint(idx1)
            
        # Note: removing one changes indices, so get ID again or be careful. 
        # IDs are stable.
        idx2 = self.sharedMarkupNode.GetControlPointIndexByID(self.EntryFiducialID)
        if idx2 >= 0:
            self.sharedMarkupNode.RemoveNthControlPoint(idx2)

# class SlicerDrillTip:
#     def __init__(self, volume_model, radius):
#         self.volume_model = volume_model
#         self.radius = radius
#         self.drillTipMarkupNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
#         self.drillTipMarkupNode.SetName('Drill Tip')
#         n = slicer.modules.markups.logic().AddFiducial()
#         self.drillTipMarkupNode.SetNthFiducialLabel(0, "Drill Tip")
#         # each markup is given a unique id which can be accessed from the superclass level
#         self.drillTipFiducialID = self.drillTipMarkupNode.GetNthMarkupID(n)
#         self.drillTipMarkupNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent, self.drill_tip_callback)
#         self.cartesian_to_voxel_transform = vtk.vtkMatrix4x4()  # Slicer calls this RAS to IJK coordinates
#         self.volume_model.label_volumeNode.GetRASToIJKMatrix(self.cartesian_to_voxel_transform)
#         v_rad = [self.radius, 0, 0, 1]
#         self.voxel_radius = np.linalg.norm(self.cartesian_to_voxel_transform.MultiplyPoint(v_rad))
#
#     def get_drill_tip_pos(self):
#         pos = np.array([0.0, 0.0, 0.0])
#         self.drillTipMarkupNode.GetNthFiducialPosition(0, pos)
#         return pos
#
#     def drill_tip_callback(self):
#         cartesian_position = np.append(self.get_drill_tip_pos(), 1.0)
#         voxel_position = self.cartesian_to_voxel_transform.MultiplyPoint(cartesian_position)
#
#     def remove_material(self, bone, shape, prev_state, dim_scales):
#         """
#         Creates a mask based on the intersection of the drill and bone
#         drill: mlab volume created in the run_mayavi function
#         bone: mlab volume created from the voxels of the input nrrd
#         shape: dimensions of the voxel data
#         preve_state: mlab state stack created in the run_mayavi function
#         dim_scales: list of dimensional scales based on voxel resolution
#         dim_scales: list of dimensional scales based on voxel resolution
#         """
#         # setup voxel scales
#         x_scale, y_scale, z_scale = dim_scales
#         x_voxel, y_voxel, z_voxel = shared_vars.radius_voxel / x_scale, \
#                                     shared_vars.radius_voxel / y_scale, \
#                                     shared_vars.radius_voxel / z_scale
#
#         # rescale x, y, z positions
#         x, y, z = drill.mlab_source.points[0, 0] / x_scale, \
#                   drill.mlab_source.points[0, 1] / y_scale, \
#                   drill.mlab_source.points[0, 2] / z_scale
#
#         if 0 <= x < shape[0] and 0 <= y < shape[1] and 0 <= z < shape[2]:
#             # start = time.time()
#             # set spherical mask based on the dimension of the drill
#             x_range, y_range, z_range = np.arange(x - x_voxel, x + x_voxel), \
#                                         np.arange(y - y_voxel, y + y_voxel), \
#                                         np.arange(z - z_voxel, z + z_voxel)
#
#             mask = ((x_range[:, np.newaxis, np.newaxis] - x) * x_scale) ** 2 + \
#                    ((y_range[np.newaxis, :, np.newaxis] - y) * y_scale) ** 2 + \
#                    ((z_range[np.newaxis, np.newaxis, :] - z) * z_scale) ** 2 < shared_vars.radius_voxel ** 2
#             x_idx, y_idx, z_idx = np.where(mask) + np.array([x - x_voxel, y - y_voxel, z - z_voxel]).astype(int)[:,
#                                                    None]
#             valid_idx = (0 <= x_idx) & (x_idx < shape[0]) & (0 <= y_idx) & (y_idx < shape[1]) & (0 <= z_idx) & (
#                         z_idx < shape[2])
#             x_idx = x_idx[valid_idx]
#             y_idx = y_idx[valid_idx]
#             z_idx = z_idx[valid_idx]
#             prev_state['volume'] = bone.mlab_source.scalars[x_idx, y_idx, z_idx]  # record volume
#             prev_state['index'] = [x_idx, y_idx, z_idx]  # record index
#
#             # Check if drill has come in contact with a segment
#             if np.any(bone.mlab_source.scalars[x_idx, y_idx, z_idx]):
#                 shared_vars.drill_contact = True
#             else:
#                 shared_vars.drill_contact = False
#
#             # Mask voxels intersecting with the drill
#             bone.mlab_source.scalars[x_idx, y_idx, z_idx] = 0
#             # print("Compute Mask:",time.time()-start)
#             return True
#         else:
#             shared_vars.drill_contact = False
#             return False
#
#
# volumeNode=slicer.util.getNode('MRHead')
# ijkToRas = vtk.vtkMatrix4x4()
# volumeNode.GetIJKToRASMatrix(ijkToRas)
#
# for k in range(extent[4], extent[5]+1):
#   for j in range(extent[2], extent[3]+1):
#     for i in range(extent[0], extent[1]+1):
#       position_Ijk=[i, j, k, 1]
#       position_Ras=ijkToRas.MultiplyPoint(position_Ijk)
#       r=position_Ras[0]
#       a=position_Ras[1]
#       s=position_Ras[2]
#       functionValue=(r-10)*(r-10)+(a+15)*(a+15)+s*s
#       imageData.SetScalarComponentFromDouble(i,j,k,0,functionValue)
# imageData.Modified()
#
#
#
# >>>
# >>> volumeNode.GetRASToIJKMatrix(rasToijk)
# >>> rasToijk
# (vtkCommonMathPython.vtkMatrix4x4)0x7fa1c167a940
# >>> X = get_drill_position()
# >>> X
# array([  98.03942743,   54.84340186, -709.32807135])
# >>> rasToijk.MultiplyPoint(X)
# Traceback (most recent call last):
#   File "<console>", line 1, in <module>
# TypeError: MultiplyPoint argument 1: expected a sequence of 4 values, got 3 values
# >>> rasToijk.MultiplyPoint(X.append(1))
# Traceback (most recent call last):
#   File "<console>", line 1, in <module>
# AttributeError: 'numpy.ndarray' object has no attribute 'append'
# >>> [X,1]
# [array([  98.03942743,   54.84340186, -709.32807135]), 1]
# >>> X.append(1)
# Traceback (most recent call last):
#   File "<console>", line 1, in <module>
# AttributeError: 'numpy.ndarray' object has no attribute 'append'
# >>>  Y = np.append(X,1)
#   File "<console>", line 1
#     Y = np.append(X,1)
#     ^
# IndentationError: unexpected indent
# >>> Y = np.append(X,1)
# >>> rasToijk.MultiplyPoint(Y)
# (0.6970177888870239, 387.1557312011719, 376.3438720703125, 1.0)
# >>> O = volumeNode.GetOrigin()
# >>> np.append(O,1)
# array([  98.30761719,  203.80761719, -897.5       ,    1.        ])
# >>> rasToijk.MultiplyPoint(O)
# Traceback (most recent call last):
#   File "<console>", line 1, in <module>
# TypeError: MultiplyPoint argument 1: expected a sequence of 4 values, got 3 values
# >>> O = np.append(O,1)
# >>> rasToijk.MultiplyPoint(O)
# (0.0, 2.2737367544323206e-13, -2.2737367544323206e-13, 1.0)
# >>>
