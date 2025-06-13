import numpy as np
import cv2
import argparse
from pathlib import Path

def visualize_cvd(npz_path, output_video_path, fps=30):
    """
    Visualize the CVD results from npz file and save as video.
    Shows RGB and depth images side by side.
    
    Args:
        npz_path: Path to the npz file
        output_video_path: Path to save the output video
        fps: Frames per second for the output video
    """
    # Load the npz file
    data = np.load(npz_path)
    images = data['images']  # Shape: (N, H, W, 3)
    depths = data['depths']  # Shape: (N, H, W)
    
    # Get video properties
    height, width = images.shape[1:3]
    
    # Create video writer for side-by-side view
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width * 2, height))
    
    # Process each frame
    for i in range(len(images)):
        # Get the image and depth
        img = images[i]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        depth = depths[i]
        
        # Normalize depth to 0-255 for visualization
        depth_normalized = ((depth - depth.min()) / (depth.max() - depth.min()) * 255).astype(np.uint8)
        depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
        
        # Create side-by-side view
        combined_frame = np.hstack((img, depth_colored))
        
        # Write the frame
        video_writer.write(combined_frame)
    
    # Release the video writer
    video_writer.release()
    print(f"Video saved to {output_video_path}")

def main():
    parser = argparse.ArgumentParser(description='Visualize CVD results and save as video')
    parser.add_argument('--npz_path', type=str, required=True, help='Path to the npz file')
    parser.add_argument('--output_path', type=str, required=True, help='Path to save the output video')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second for the output video')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    visualize_cvd(args.npz_path, args.output_path, args.fps)

if __name__ == '__main__':
    main() 