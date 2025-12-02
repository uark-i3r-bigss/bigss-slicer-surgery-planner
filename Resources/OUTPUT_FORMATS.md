# Output File Formats

## Trajectory Planner Output
**Default File**: `/tmp/slicer_surgery_planner_points.txt`
**Content**: Landmark coordinates for each trajectory.

- **Header**: `# CoordinateSystem: [RAS|LPS]`
- **Format**: `TrajectoryName, Entry_X, Entry_Y, Entry_Z, Target_X, Target_Y, Target_Z`
- **Example**: `Trajectory_1, 10.5, 20.0, -5.0, 50.0, 50.0, 100.0`

## Reference Plane Planner Output
**Default File**: `/tmp/slicer_surgery_planner_planes.txt`
**Content**: 4x4 Transformation Matrix and dimensions for each plane.

- **Header**: `# CoordinateSystem: [RAS|LPS]`
- **Format**: `PlaneName, M00, M01, ..., M33, Width, Height`
- **Matrix**: Flattened 4x4 Object-to-World matrix (Row-Major).
    - `M00-M02`: Rotation/Scale X
    - `M03`: Position X
    - `M10-M12`: Rotation/Scale Y
    - `M13`: Position Y
    - `M20-M22`: Rotation/Scale Z
    - `M23`: Position Z
- **Example**: `ReferencePlane_1, 1.0, 0.0, ..., 1.0, 150.0, 150.0`
