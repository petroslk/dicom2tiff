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

# Increase JVM heap size
ENV JAVA_TOOL_OPTIONS: "-Xmx8g"
ENV _JAVA_OPTIONS="-Xmx8g"

# Install necessary dependencies
# Update and install libvips
RUN apt-get update && apt-get install -y \
    libopenjp2-7 \
    libtiff5 \
    gcc \
    openjdk-11-jre

RUN apt-get install -y wget unzip && \
    wget https://downloads.openmicroscopy.org/bio-formats/6.13.0/artifacts/bftools.zip -O /tmp/bftools.zip && \
    unzip /tmp/bftools.zip -d /opt/ && \
    rm /tmp/bftools.zip

# Update conda
RUN conda update -n base -c defaults conda

# Install pyvips
RUN conda install -c conda-forge pyvips

#dd bftools bins to path
ENV PATH="/opt/bftools:${PATH}"

# Clone repo
RUN git clone https://github.com/petroslk/dicom2tiff.git
WORKDIR /dicom2tiff

# Install necessary Python dependencies
RUN pip install .

WORKDIR /app
