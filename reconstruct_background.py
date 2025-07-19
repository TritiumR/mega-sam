import numpy as np
import open3d as o3d
import argparse
import os
import torch
import json
import matplotlib.pyplot as plt


def geocalib_to_matrix(roll, pitch):
    """
    Convert GeoCalib calibration to rotation matrix.
    
    Args:
        roll: Roll angle in degrees
        pitch: Pitch angle in degrees  
    
    Returns:
        3x3 rotation matrix
    """
    # Convert degrees to radians
    roll = np.deg2rad(roll)
    pitch = np.deg2rad(pitch)
    
    # Rotation matrices
    # Rx = np.array([
    #     [1, 0, 0],
    #     [0, np.cos(roll), -np.sin(roll)],
    #     [0, np.sin(roll), np.cos(roll)]
    # ])
    # Ry = np.array([
    #     [np.cos(pitch), 0, np.sin(pitch)],
    #     [0, 1, 0],
    #     [-np.sin(pitch), 0, np.cos(pitch)]
    # ])
    Rz = np.array([
        [np.cos(roll), -np.sin(roll), 0],
        [np.sin(roll), np.cos(roll), 0],
        [0, 0, 1]
    ])
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(pitch), -np.sin(pitch)],
        [0, np.sin(pitch), np.cos(pitch)]
    ])
    
    # Combined rotation: R = Rz * Rx
    return Rz @ Rx


def create_point_cloud(depth, intrinsic, cam_c2w, rgb=None, mot_prob=None):
    """
    Create point cloud from depth map and camera parameters.
    
    Args:
        depth: Depth map (H, W)
        intrinsic: Camera intrinsic matrix (3, 3)
        cam_c2w: Camera to world transformation matrix (4, 4)
        rgb: RGB image (H, W, 3), optional
    
    Returns:
        open3d.geometry.PointCloud
    """
    # Create pixel grid
    h, w = depth.shape
    y, x = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    
    # Back-project pixels to 3D points
    fx, fy = intrinsic[0, 0], intrinsic[1, 1]
    cx, cy = intrinsic[0, 2], intrinsic[1, 2]
    
    # Convert to camera coordinates
    z = depth
    x = (x - cx) * z / fx
    y = (y - cy) * z / fy
    
    # Stack coordinates
    points = np.stack([x, y, z], axis=-1)
    
    # Reshape to (N, 3)
    points = points.reshape(-1, 3)
    
    # Remove invalid points (where depth is 0 or inf)
    valid_mask = (points[:, 2] > 0) & (points[:, 2] < np.inf)

    # remove points that are not in the mot_prob
    valid_mask = valid_mask * mot_prob.reshape(-1).astype(bool)

    points = points[valid_mask]
    
    # Transform to world coordinates
    points_homogeneous = np.concatenate([points, np.ones((points.shape[0], 1))], axis=1)
    points_world = (cam_c2w @ points_homogeneous.T).T[:, :3]
    
    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_world)
    
    # Add colors if RGB is provided
    if rgb is not None:
        # Reshape RGB to match the points
        colors = rgb.reshape(-1, 3)
        # Apply the same mask to colors as we did to points
        colors = colors[valid_mask]
        # Normalize colors to [0, 1] range if they're in [0, 255]
        if colors.max() > 1.0:
            colors = colors / 255.0
        pcd.colors = o3d.utility.Vector3dVector(colors)
    
    return pcd


def filter_points_by_density(pcd, radius, min_points):
    """
    Filter points based on local density.
    
    Args:
        pcd: Open3D point cloud
        radius: Radius to search for neighboring points
        min_points: Minimum number of points required within radius
    
    Returns:
        Filtered Open3D point cloud
    """
    # Use Open3D's radius outlier removal
    filtered_pcd, _ = pcd.remove_radius_outlier(nb_points=min_points, radius=radius)
    
    return filtered_pcd


def estimate_normals(pcd, radius=0.1, max_nn=30):
    """
    Estimate normals for the point cloud.
    
    Args:
        pcd: Open3D point cloud
        radius: Radius to search for neighboring points
        max_nn: Maximum number of neighbors to consider
    
    Returns:
        Point cloud with estimated normals
    """
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
    )
    pcd.orient_normals_consistent_tangent_plane(k=max_nn)
    return pcd


def reconstruct_mesh_poisson(pcd, depth=8, width=0, scale=1.1, linear_fit=False):
    """
    Reconstruct mesh using Poisson surface reconstruction.
    
    Args:
        pcd: Open3D point cloud with normals
        depth: Depth of the octree used for reconstruction
        width: Width parameter for the reconstruction
        scale: Scale parameter for the reconstruction
        linear_fit: Whether to use linear fitting
    
    Returns:
        Open3D mesh
    """
    print(f"Reconstructing mesh using Poisson surface reconstruction (depth={depth})")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=depth, width=width, scale=scale, linear_fit=linear_fit
    )
    
    # Remove low density vertices
    vertices_to_remove = densities < np.quantile(densities, 0.1)
    mesh.remove_vertices_by_mask(vertices_to_remove)
    
    return mesh


def clean_mesh(mesh, remove_duplicated_vertices=True, remove_duplicated_triangles=True, 
               remove_degenerate_triangles=True, remove_unreferenced_vertices=True):
    """
    Clean the reconstructed mesh by removing various artifacts.
    
    Args:
        mesh: Open3D mesh to clean
        remove_duplicated_vertices: Whether to remove duplicated vertices
        remove_duplicated_triangles: Whether to remove duplicated triangles
        remove_degenerate_triangles: Whether to remove degenerate triangles
        remove_unreferenced_vertices: Whether to remove unreferenced vertices
    
    Returns:
        Cleaned Open3D mesh
    """
    print("Cleaning mesh...")
    mesh = mesh.remove_duplicated_vertices() if remove_duplicated_vertices else mesh
    mesh = mesh.remove_duplicated_triangles() if remove_duplicated_triangles else mesh
    mesh = mesh.remove_degenerate_triangles() if remove_degenerate_triangles else mesh
    mesh = mesh.remove_unreferenced_vertices() if remove_unreferenced_vertices else mesh
    
    print(f"Cleaned mesh has {len(mesh.vertices)} vertices and {len(mesh.triangles)} triangles")
    return mesh


def main():
    parser = argparse.ArgumentParser(description='Reconstruct point cloud from NPZ file')
    parser.add_argument('--name', type=str, required=True, help='Path to the npz file')
    parser.add_argument('--downsample', type=float, default=0.01, help='Downsample voxel size (0 to disable)')
    parser.add_argument('--frame_idx', type=int, default=None, help='Process only a specific frame (for debugging)')
    parser.add_argument('--density_radius', type=float, default=0.01, help='Radius for density-based filtering')
    parser.add_argument('--min_points', type=int, default=30, help='Minimum number of points required within radius for density filtering')
    
    args = parser.parse_args()

    # Load data
    data = np.load(f'outputs_cvd/{args.name}_sgd_cvd_hr.npz')
    images = data['images']  # (N, H, W, 3)
    depths = data['depths']  # (N, H, W)
    intrinsic = data['intrinsic']  # (3, 3)
    cam_c2w = data['cam_c2w']  # (N, 4, 4)
    
    mot_prob = np.load(os.path.join('reconstructions', args.name, 'motion_prob.npy'))

    # Create output directory
    output_dir = os.path.join('visualizations', args.name)
    os.makedirs(output_dir, exist_ok=True)

    # interpolate mot_prob to the same resolution as the images
    mot_prob = torch.nn.functional.interpolate(
      torch.from_numpy(mot_prob).unsqueeze(0),
      scale_factor=(images.shape[2] / mot_prob.shape[2], images.shape[1] / mot_prob.shape[1]),
      mode="bilinear",
    )
    mot_prob = mot_prob.squeeze(0).numpy()

    mot_prob[mot_prob >= 0.8] = 1
    mot_prob[mot_prob < 0.8] = 0

    # load calibration to align with gravity direction
    with open(os.path.join(output_dir, 'calibration.json'), 'r') as f:
        calibration = json.load(f)
        img_name = calibration['img_name']
        img_id = int(img_name.split('.')[0])
        print(f"img_id: {img_id}")
        roll = calibration['roll']
        pitch = calibration['pitch']
        print(f"roll: {roll}, pitch: {pitch}")
        ori_cam_c2w = cam_c2w[img_id]

        print(f"ori_cam_c2w: {ori_cam_c2w}")

        # # save the image to debug
        # image = images[img_id]
        # image = image.astype(np.uint8)
        # plt.imsave(f'{output_dir}/image.png', image)

        # align with gravity direction
        # The calibration angles are in camera coordinates
        # We want to align the camera so that gravity points in the -Z direction of the camera
        
        # Get the original rotation (3x3) from the reference c2w
        R_orig = ori_cam_c2w[:3, :3]
        
        # The calibration angles represent the CURRENT camera orientation relative to gravity
        # To align with gravity, we need to INVERT this rotation
        R_calib = geocalib_to_matrix(roll, pitch)
        
        # The transformation we need is: R_align = R_calib^T * R_orig^T
        # This removes the calibration rotation and aligns with gravity
        R_align = R_calib @ R_orig.T
        
        # Build a 4x4 transformation matrix
        T_align = np.eye(4)
        T_align[:3, :3] = R_align
        
        print(f"Original camera rotation:\n{R_orig}")
        print(f"Calibration rotation (current orientation):\n{R_calib}")
        print(f"Alignment rotation:\n{R_align}")
        
        # Apply to all c2w matrices
        for i in range(cam_c2w.shape[0]):
            cam_c2w[i] = T_align @ cam_c2w[i]


    # # visualize mot_prob on images
    # os.makedirs(os.path.join(output_dir, 'mot_prob'), exist_ok=True)
    # for i in range(images.shape[0]):
    #     image = images[i]
    #     mot_prob_image = mot_prob[i]
    #     image = image * mot_prob_image[..., None]
    #     vis_image = image.astype(np.uint8)
    #     plt.imsave(f'{output_dir}/mot_prob/{i}.png', vis_image)
    
    # # Process frames
    # if args.frame_idx is not None:
    #     # Process only one frame for debugging
    #     frame_indices = [args.frame_idx]
    # else:
    frame_indices = range(len(images))
    
    all_points = []
    all_colors = []
    
    for i in frame_indices:
        print(f"Processing frame {i+1}/{len(images)}")
        pcd = create_point_cloud(depths[i], intrinsic, cam_c2w[i], images[i], mot_prob[i])
        
        if args.downsample > 0:
            pcd = pcd.voxel_down_sample(args.downsample)
        
        all_points.append(np.asarray(pcd.points))
        all_colors.append(np.asarray(pcd.colors))
    
    # Combine all points
    combined_pcd = o3d.geometry.PointCloud()
    combined_pcd.points = o3d.utility.Vector3dVector(np.vstack(all_points))
    combined_pcd.colors = o3d.utility.Vector3dVector(np.vstack(all_colors))

    print(f"Combined point cloud has {len(combined_pcd.points)} points")

    # Apply density-based filtering if requested
    if args.density_radius is not None:
        print(f"Applying density filtering with radius={args.density_radius}, min_points={args.min_points}")
        original_count = len(combined_pcd.points)
        combined_pcd = filter_points_by_density(combined_pcd, args.density_radius, args.min_points)
        filtered_count = len(combined_pcd.points)
        print(f"Density filtering removed {original_count - filtered_count} points ({filtered_count}/{original_count} remaining)")
    
    # downsample if requested
    if args.downsample > 0:
        combined_pcd = combined_pcd.voxel_down_sample(args.downsample)
    
    # Save point cloud as obj with colors
    o3d.io.write_point_cloud(os.path.join(output_dir, 'pointcloud.ply'), combined_pcd)
    print(f"Point cloud saved to {os.path.join(output_dir, 'pointcloud.ply')}")

    # Reconstruct mesh
    point_cloud_with_normals = estimate_normals(combined_pcd)
    mesh = reconstruct_mesh_poisson(point_cloud_with_normals)
    mesh = clean_mesh(mesh)
    
    # Save mesh as ply
    o3d.io.write_triangle_mesh(os.path.join(output_dir, 'mesh.ply'), mesh)
    print(f"Mesh saved to {os.path.join(output_dir, 'mesh.ply')}")


if __name__ == '__main__':
    main() 