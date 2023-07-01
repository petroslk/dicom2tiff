# Start from a conda based Python image
FROM continuumio/miniconda3

# Metadata
LABEL base.image="continuumio/miniconda3"
LABEL version="1"
LABEL software="DICOM to TIFF conversion"
LABEL software.version="0.0.1"
LABEL description="This image provides a tool to convert WSI-DICOM files to TIFF format"
LABEL website="https://github.com/petroslk"
LABEL maintainer="Petros Liakopoulos"


# Install necessary dependencies
# Update and install libvips
RUN apt-get update && apt-get install -y \
    libopenjp2-7 \
    libtiff5 \
    libvips

# Update conda
RUN conda update -n base -c defaults conda

# Install Bio-Formats command line tools with conda
RUN conda install -c bioconda bftools

# Clone repo
RUN git clone https://github.com/petroslk/dicom2tiff.git
WORKDIR /dicom2tiff

# Install necessary Python dependencies
RUN pip install .

WORKDIR /app
