from setuptools import setup
from setuptools import find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as rq:
    requirements = rq.readlines()

setup(
    # Library name
    name="dicomWSItk",

    version="1.0.0",

    author="Julien Massonnet, Petros Liakopoulos",

    author_email="liakopoulos.petros@gmail.com",

    description="dicomWSItk is a toolkit for working with DICOM WSI and openslide",

    long_description=long_description,

    long_description_content_type="text/markdown",

    url="https://github.com/petroslk/dicom2tiff.git",

    install_requires=requirements,

    packages=find_packages(),
        package_data={
        'dicomWSItk': ['pixelmed.jar'],
    },

    include_package_data=True,

    python_requires=">=3.10",

    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ["dicomWSItk=dicomWSItk.main:main"],
    },
)
