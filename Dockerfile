FROM ubuntu:jammy

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
        build-essential \
        software-properties-common \
        ninja-build \
        python3-pip \
        pkg-config \
        wget 

RUN apt-get install -y vim
RUN apt-get install -y git ninja-build 
RUN apt-get install -y glib-2.0-dev libcairo2-dev libgdk-pixbuf-2.0-dev libjpeg-turbo8-dev
RUN apt-get install -y libopenjp2-7-dev zlib1g-dev libtiff-dev libxml2-dev libpng-dev libsqlite3-dev 
RUN pip install meson

# needed for DICOM WSI in openslide
ARG DICOM_VERSION=1.1.0
ARG DICOM_URL=https://github.com/ImagingDataCommons/libdicom/releases/download/

RUN wget ${DICOM_URL}/v${DICOM_VERSION}/libdicom-${DICOM_VERSION}.tar.xz

RUN tar xfJ libdicom-${DICOM_VERSION}.tar.xz \
        && cd libdicom-${DICOM_VERSION} \
        && meson setup --libdir=lib --buildtype=release builddir \
        && meson compile -C builddir \
        && meson install -C builddir

ARG OPENSLIDE_VERSION=4.0.0
ARG OPENSLIDE_URL=https://github.com/openslide/openslide/releases/download

RUN wget ${OPENSLIDE_URL}/v${OPENSLIDE_VERSION}/openslide-${OPENSLIDE_VERSION}.tar.xz

RUN tar xfJ openslide-${OPENSLIDE_VERSION}.tar.xz \
        && cd openslide-${OPENSLIDE_VERSION} \
        && meson setup --libdir=lib --buildtype=release builddir \
        && meson compile -C builddir \
        && meson install -C builddir

RUN apt-get install -y \
        libexpat-dev \
        librsvg2-dev \
        libarchive-dev \
        libexif-dev \
        liblcms2-dev \
        libheif-dev \
        libhwy-dev

# build the head of the stable 8.15 branch
ARG VIPS_BRANCH=8.15
ARG VIPS_URL=https://github.com/libvips/libvips/tarball

RUN mkdir libvips-${VIPS_BRANCH} \
        && cd libvips-${VIPS_BRANCH} \
        && wget ${VIPS_URL}/${VIPS_BRANCH} -O - | \
                tar xfz - --strip-components 1

# "--libdir lib" makes it put the library in /usr/local/lib
# we don't need GOI
RUN cd libvips-${VIPS_BRANCH} \
        && rm -rf build \
        && meson setup build --libdir lib -Dintrospection=disabled \
        && cd build \
        && ninja \
        && ninja test \
        && ninja install

RUN apt-get install -y default-jre
RUN pip3 install pyvips numpy pydicom tifftools JPype1
COPY ./ /dicomWSItk
WORKDIR /dicomWSItk
RUN pip install .
WORKDIR /app
