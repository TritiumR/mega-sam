name=$1
interval=$2

python video_to_png.py $name $interval

./mono_depth_scripts/run_mono-depth_demo.sh $name

./tools/evaluate_demo.sh $name

./cvd_opt/cvd_opt_demo.sh $name

python visualize_cvd.py --npz_path outputs_cvd/"$name"_sgd_cvd_hr.npz --output_path visualizations/"$name"_"$interval".mp4 --fps 30

python reconstruct_pointcloud.py --npz_path outputs_cvd/"$name"_sgd_cvd_hr.npz --output_path visualizations/"$name"_"$interval".ply --downsample 0.01