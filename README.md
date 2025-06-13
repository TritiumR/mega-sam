## Clone

Make sure to clone the repository with the submodules by using:
`git clone --recursive git@github.com:TritiumR/mega-sam.git`

## Instructions for installing dependencies

### Python Environment

The following codebase was successfully run with Python 3.10, CUDA11.8, and
Pytorch2.0.1. We suggest installing the library in a virtual environment such as
Anaconda.

1.  To install main libraries, run: \
    `conda env create -f environment.yml`

2.  To install xformers for UniDepth model, follow the instructions from
    https://github.com/facebookresearch/xformers. If you encounter any
    installation issue, we suggest installing it from a prebuilt file. For
    example, for Python 3.10+Cuda11.8+Pytorch2.0.1, run: \
    `wget https://anaconda.org/xformers/xformers/0.0.22.post7/download/linux-64/xformers-0.0.22.post7-py310_cu11.8.0_pyt2.0.1.tar.bz2`

    `conda install xformers-0.0.22.post7-py310_cu11.8.0_pyt2.0.1.tar.bz2`

3.  Compile the extensions for the camera tracking module: \
    `cd base; python setup.py install`

### Downloading pretrained checkpoints

1.  Download [DepthAnything checkpoint](https://huggingface.co/spaces/LiheYoung/Depth-Anything/blob/main/checkpoints/depth_anything_vitl14.pth) to
    mega-sam/Depth-Anything/checkpoints/depth_anything_vitl14.pth

2.  Download and include [RAFT checkpoint](https://drive.google.com/drive/folders/1sWDsfuZ3Up38EUQt7-JDTT1HcGHuJgvT) at mega-sam/cvd_opt/raft-things.pth

### Running MegaSaM on in-the-wild video

1.  Precompute mono-depth (Please modify img-path in the script):
    `./mono_depth_scripts/run_mono-depth_demo.sh`

2.  Running camera tracking (Please modify DATA_PATH in the script. Add
    argument --opt_focal to enable focal length optimization):
    `./tools/evaluate_demo.sh`

3.  Running consistent video depth optimization given estimated cameras (Please
    modify datapath in the script):
    `./cvd_opt/cvd_opt_demo.sh`

4. [Chuanruo] Visualize the results:
    `visualize_cvd.py --npz_path {path_to_sgd_cvd_hr.npz} --output_path {path_to_output_video} --fps {fps}`


