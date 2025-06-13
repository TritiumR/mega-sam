import cv2
import os

def extract_frames(video_path, output_folder, interval):
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
    name = sys.argv[1]
    interval = int(sys.argv[2])
    video_path = f'data/{name}.mp4'
    output_folder = f'data/{name}'  # Replace with your desired output folder
    print('Extracting frames from video...')
    extract_frames(video_path, output_folder, interval)