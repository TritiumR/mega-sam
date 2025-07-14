import cv2
import os

def extract_frames(video_path, output_folder, start_frame, end_frame, interval):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Open the video file
    vidcap = cv2.VideoCapture(video_path)
    success, image = vidcap.read()
    count = 0
    id = 0

    save_interval = interval  # Save every 10 frame
    while success:
        # Define the output filename
        frame_filename = os.path.join(output_folder, f"{id:05d}.png")
        if count < start_frame:
            success, image = vidcap.read()
            count += 1
            continue
        if end_frame != -1 and count > end_frame:
            break
        # Save the current frame as a PNG image
        if count % save_interval == 0:
            cv2.imwrite(frame_filename, image)
            id += 1
        # Read the next frame from the video
        success, image = vidcap.read()
        count += 1

    vidcap.release()
    print(f"Extracted {id} frames to '{output_folder}'")

# take two arguments: video_path and output_folder from the command line
if __name__ == '__main__':
    import sys
    path = sys.argv[1]
    name = sys.argv[2]
    start_frame = int(sys.argv[3])
    end_frame = int(sys.argv[4])
    interval = int(sys.argv[5])
    
    # Check for video file with different extensions
    video_extensions = ['.mp4', '.webm']
    video_path = None
    
    for ext in video_extensions:
        potential_path = f'data/{path}/{name}{ext}'
        if os.path.exists(potential_path):
            video_path = potential_path
            break
    
    if video_path is None:
        print(f"Error: No video file found for '{name}' with extensions {video_extensions}")
        print(f"Looked in: data/{name}.mp4, data/{name}.webm")
        sys.exit(1)
    
    output_folder = f'data/{name}'  # Replace with your desired output folder
    print(f'Extracting frames from video: {video_path}')
    extract_frames(video_path, output_folder, start_frame, end_frame, interval)