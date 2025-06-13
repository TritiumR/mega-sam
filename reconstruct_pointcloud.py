import numpy as np
import open3d as o3d
from pathlib import Path
import argparse

def create_point_cloud(depth, intrinsic, cam_c2w, rgb=None):
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

    # # remove points that are near the image boundary
    # threshold = 0.01
    # print(points[:, 0].min(), points[:, 0].max())
    # valid_mask = valid_mask & (points[:, 0] > threshold) & (points[:, 0] < w - threshold) & (points[:, 1] > threshold) & (points[:, 1] < h - threshold)

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

def main():
    parser = argparse.ArgumentParser(description='Reconstruct point cloud from NPZ file')
    parser.add_argument('--npz_path', type=str, required=True, help='Path to the npz file')
    parser.add_argument('--output_path', type=str, required=True, help='Path to save the point cloud')
    parser.add_argument('--downsample', type=float, default=0.01, help='Downsample voxel size (0 to disable)')
    parser.add_argument('--frame_idx', type=int, default=None, help='Process only a specific frame (for debugging)')
    
    args = parser.parse_args()
    
    # Load data
    data = np.load(args.npz_path)
    images = data['images']  # (N, H, W, 3)
    depths = data['depths']  # (N, H, W)
    intrinsic = data['intrinsic']  # (3, 3)
    cam_c2w = data['cam_c2w']  # (N, 4, 4)
    
    # Create output directory
    output_dir = Path(args.output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process frames
    if args.frame_idx is not None:
        # Process only one frame for debugging
        frame_indices = [args.frame_idx]
    else:
        frame_indices = range(len(images))
    
    all_points = []
    all_colors = []
    
    for i in frame_indices:
        print(f"Processing frame {i+1}/{len(images)}")
        pcd = create_point_cloud(depths[i], intrinsic, cam_c2w[i], images[i])
        
        # Downsample if requested
        if args.downsample > 0:
            pcd = pcd.voxel_down_sample(args.downsample)
        
        all_points.append(np.asarray(pcd.points))
        all_colors.append(np.asarray(pcd.colors))
    
    # Combine all points
    combined_pcd = o3d.geometry.PointCloud()
    combined_pcd.points = o3d.utility.Vector3dVector(np.vstack(all_points))
    combined_pcd.colors = o3d.utility.Vector3dVector(np.vstack(all_colors))
    
    # Save point cloud
    o3d.io.write_point_cloud(args.output_path, combined_pcd)
    print(f"Point cloud saved to {args.output_path}")
    
    # Visualize
    o3d.visualization.draw_geometries([combined_pcd])

if __name__ == '__main__':
    main() 