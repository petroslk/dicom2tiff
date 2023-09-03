# dicom2tiff
dicom2tiff is a small wrapper tool that combines bfconvert and vips to create a OpenSlide compatible TIFF pyramidal file.

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
conda activate
conda install -c ome bftools
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
dicom2tiff path/to/dicom_dir_patient* --output_dir converted_slides
```

Using the docker:

```
docker run -it -v /path/to/slides/:/app petroslk/dicom2tiff:latest dicom2tiff patient_* --output_dir converted_slides
```

## Caveats

dicom2tiff will take the largest file inside of the WSI-DICOM dir, which should always correspond to the dcm file of the highest available magnification.

Generic pyramidal tiff files do not store microns per pixel (MPP). Nevertheless, these have been added and can be accessed in the "comment" of the OpenSlide properties.

```
import openslide
slide = openslide.OpenSlide("path/to/slide/tiff")
slide.properties["openslide.comment"]
```

When opened on QuPath, these slides will not display MPP values.
