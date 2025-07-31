import numpy as np
import open3d as o3d
import argparse
import os
import torch
import json
import matplotlib.pyplot as plt
import cv2

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


def reconstruct_wrist_position(depth, intrinsic, cam_c2w, wrist_2d):
    """
    reconstruct 3d wrist position from depth map and camera parameters.
    
    Args:
        depth: Depth map (H, W)
        intrinsic: Camera intrinsic matrix (3, 3)
        cam_c2w: Camera to world transformation matrix (4, 4)
        wrist_2d: normalized 2d wrist position (x, y)
    
    Returns:
        3d wrist position (x, y, z)
    """
    H, W = depth.shape
    
    # Convert normalized coordinates to pixel coordinates
    u = int(wrist_2d[0] * W)
    v = int(wrist_2d[1] * H)
    
    # Clamp to image boundaries
    u = max(0, min(u, W - 1))
    v = max(0, min(v, H - 1))
    
    # Get depth value at wrist position
    z_cam = depth[v, u]
    
    # Convert to camera coordinates using intrinsic matrix
    # (u, v, 1) = intrinsic @ (x_cam/z_cam, y_cam/z_cam, 1)
    # So: (x_cam, y_cam, z_cam) = z_cam * intrinsic^(-1) @ (u, v, 1)
    intrinsic_inv = np.linalg.inv(intrinsic)
    pixel_coords = np.array([u, v, 1.0])
    cam_coords = z_cam * (intrinsic_inv @ pixel_coords)
    
    # Convert to homogeneous coordinates
    cam_coords_homo = np.array([cam_coords[0], cam_coords[1], cam_coords[2], 1.0])
    
    # Transform to world coordinates
    world_coords_homo = cam_c2w @ cam_coords_homo
    
    # Return 3D world coordinates
    return world_coords_homo[:3].tolist()


def main():
    parser = argparse.ArgumentParser(description='Reconstruct point cloud from NPZ file')
    parser.add_argument('--name', type=str, required=True, help='Path to the npz file')
    
    args = parser.parse_args()

    # Load data
    data = np.load(f'outputs_cvd/{args.name}_sgd_cvd_hr.npz')
    images = data['images']  # (N, H, W, 3)
    depths = data['depths']  # (N, H, W)
    intrinsic = data['intrinsic']  # (3, 3)
    cam_c2w = data['cam_c2w']  # (N, 4, 4)

    # Load hand pose
    right_hand_pose = json.load(open(os.path.join('visualizations', args.name, 'hand_pose', 'all_right_results.json')))
    left_hand_pose = json.load(open(os.path.join('visualizations', args.name, 'hand_pose', 'all_left_results.json')))

    # Create output directory
    output_dir = os.path.join('visualizations', args.name)
    os.makedirs(output_dir, exist_ok=True)

    # load calibration to align with gravity direction
    with open(os.path.join(output_dir, 'calibration.json'), 'r') as f:
        calibration = json.load(f)
        img_name = calibration['img_name']
        img_id = int(img_name.split('.')[0])
        # print(f"img_id: {img_id}")
        roll = calibration['roll']
        pitch = calibration['pitch']
        # print(f"roll: {roll}, pitch: {pitch}")
        ori_cam_c2w = cam_c2w[img_id]

        # print(f"ori_cam_c2w: {ori_cam_c2w}")

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
        
        # print(f"Original camera rotation:\n{R_orig}")
        # print(f"Calibration rotation (current orientation):\n{R_calib}")
        # print(f"Alignment rotation:\n{R_align}")
        
        # Apply to all c2w matrices
        for i in range(cam_c2w.shape[0]):
            cam_c2w[i] = T_align @ cam_c2w[i]

    frame_indices = range(len(images))

    output_dir = os.path.join(output_dir, 'hand_pose')
    os.makedirs(output_dir, exist_ok=True)

    # visualize the wrist 2d position
    for i in range(len(images)):
        if 'wrist_2d_normalized' not in right_hand_pose[f'{i:05d}']:
            continue
        normalized_wrist_2d = right_hand_pose[f'{i:05d}']['wrist_2d_normalized']
        pixel_wrist_2d = normalized_wrist_2d * np.array([images[i].shape[1], images[i].shape[0]])
        vis_image = images[i].copy()
        vis_image = cv2.circle(vis_image, (int(pixel_wrist_2d[0]), int(pixel_wrist_2d[1])), 5, (0, 0, 255), -1)
        plt.imsave(f'{output_dir}/{i:05d}_right_wrist.png', vis_image)
    
    for i in frame_indices:
        print(f"Processing frame {i+1}/{len(images)}")
        if 'wrist_2d_normalized' in right_hand_pose[f'{i:05d}']:
            right_waypoint = reconstruct_wrist_position(depths[i], intrinsic, cam_c2w[i], right_hand_pose[f'{i:05d}']['wrist_2d_normalized'])
            right_hand_pose[f'{i:05d}']['wrist_3d'] = right_waypoint
        if 'wrist_2d_normalized' in left_hand_pose[f'{i:05d}']:
            left_waypoint = reconstruct_wrist_position(depths[i], intrinsic, cam_c2w[i], left_hand_pose[f'{i:05d}']['wrist_2d_normalized'])
            left_hand_pose[f'{i:05d}']['wrist_3d'] = left_waypoint
        
    # save the waypoints in the json file
    with open(os.path.join(output_dir, 'all_right_results.json'), 'w') as f:
        json.dump(right_hand_pose, f, indent=4)
    with open(os.path.join(output_dir, 'all_left_results.json'), 'w') as f:
        json.dump(left_hand_pose, f, indent=4)

if __name__ == '__main__':
    main() 