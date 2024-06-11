# dicom2tiff
dicom2tiff is a tool for converting DICOM Whole Slide Images to generic pyramidal TIF files.
Since currently not all DICOM flavors are supported by OpenSlide, this tool should help you convert some of them to an openslide compatible format.

## Installation

Use of conda is recommended for installation and usage

First install the [libvips](https://github.com/libvips/libvips):

For debian/ubuntu 
```
sudo apt-get install libvips
```

Then, install dependencies using conda
```
conda create -n dicom2tiff python=3.10
conda activate dicom2tiff
```

Finally, install dicom2tiff:

```
pip install .
```

## Docker

You can also directly pull the docker container from dockerhub

```
docker pull petroslk/dicom2tiff:latest
```

## Usage

Provide one directory or a glob pattern of WSI-DICOM directories

```
dicom2tiff path/to/dicom_dir_patient*/ -o converted_slides
```

Using the docker:

```
docker run -it -v /path/to/slides/:/app petroslk/dicom2tiff:latest dicom2tiff dicom_dirs*/ -o converted_slides
```

## Important info

dicom2tiff will write a temporary file which can be quite large, so make sure you have enough space on your disk.
