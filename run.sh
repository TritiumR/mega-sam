name=$1
start_frame=$2
end_frame=$3
interval=$4

retargeting_type=position
hand_name=allegro

# python video_to_png.py ego4d $name $start_frame $end_frame $interval

# cd ../GeoCalib

# conda run --no-capture-output -n geocalib python run.py --name $name

# cd ../mega-sam

# cd ../Hamba

# conda run --no-capture-output -n hamba python run.py --img_folder ../mega-sam/data/"$name"/undistorted --out_folder ../mega-sam/visualizations/"$name"/hand_pose/ --full_frame

cd ../hamer

conda run --no-capture-output -n hamer python run.py --img_folder ../mega-sam/data/"$name"/undistorted --out_folder ../mega-sam/visualizations/"$name"/hand_pose/

cd ../mega-sam

python retarget_wrist.py --name $name

# cd ../dex-retargeting/example/retargeting

# conda run --no-capture-output -n dex_retargeting python retarget_from_joint.py --robot-name $hand_name --joint-path ../../../mega-sam/visualizations/"$name"/hand_pose/right_joint_pos.npy --retargeting-type $retargeting_type --hand-type right --output-path ../../../mega-sam/visualizations/"$name"/hand_pose/"$hand_name"_right_joints.pkl --interpolation $interval

# conda run --no-capture-output -n dex_retargeting python render_robot_hand.py --pickle-path ../../../mega-sam/visualizations/"$name"/hand_pose/"$hand_name"_right_joints.pkl --output-video-path ../../../mega-sam/visualizations/"$name"/hand_pose/"$hand_name"_right.mp4 --headless

# conda run --no-capture-output -n dex_retargeting python retarget_from_joint.py --robot-name $hand_name --joint-path ../../../mega-sam/visualizations/"$name"/hand_pose/left_joint_pos.npy --retargeting-type $retargeting_type --hand-type left --output-path ../../../mega-sam/visualizations/"$name"/hand_pose/"$hand_name"_left_joints.pkl --interpolation $interval

# conda run --no-capture-output -n dex_retargeting python render_robot_hand.py --pickle-path ../../../mega-sam/visualizations/"$name"/hand_pose/"$hand_name"_left_joints.pkl --output-video-path ../../../mega-sam/visualizations/"$name"/hand_pose/"$hand_name"_left.mp4 --headless

# cd ../../../mega-sam

# ./mono_depth_scripts/run_mono-depth_demo.sh $name

# ./tools/evaluate_demo.sh $name

# ./cvd_opt/cvd_opt_demo.sh $name

# python reconstruct_background.py --name $name

# ../blender-app/blender -b -P ply2obj_texture.py -- visualizations/"$name"/mesh.ply visualizations/"$name"/mesh.obj

# cd ../IsaacLab

# conda run --no-capture-output -n env_isaaclab ./isaaclab.sh -p scripts/tools/convert_mesh.py ../mega-sam/visualizations/"$name"/mesh.obj ../mega-sam/visualizations/"$name"/mesh.usd --make-instanceable --collision-approximation convexDecomposition

