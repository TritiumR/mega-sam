name=$1
start_frame=$2
end_frame=$3
interval=$4

# python video_to_png.py ego4d $name $start_frame $end_frame $interval

# cd ../GeoCalib

# conda run --no-capture-output -n geocalib python run.py --name $name

# cd ../mega-sam

# ./mono_depth_scripts/run_mono-depth_demo.sh $name

# ./tools/evaluate_demo.sh $name

# ./cvd_opt/cvd_opt_demo.sh $name

python reconstruct_background.py --name $name

../blender-app/blender -b -P ply2obj_texture.py -- visualizations/"$name"/mesh.ply visualizations/"$name"/mesh.obj

cd ../IsaacLab

conda run --no-capture-output -n env_isaaclab ./isaaclab.sh -p scripts/tools/convert_mesh.py ../mega-sam/visualizations/"$name"/mesh.obj ../mega-sam/visualizations/"$name"/mesh.usd --make-instanceable --collision-approximation convexDecomposition

