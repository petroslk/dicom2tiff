from setuptools import setup
from setuptools import find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as rq:
    requirements = rq.readlines()

setup(
    # Library name
    name="dicom2tiff",

    version="1.0.0",

    author="Your Name",

    author_email="your.email@gmail.com",

    description="dicom2tiff is a tool for converting DICOM-WSI files to pyramid TIFF files",

    long_description=long_description,

    long_description_content_type="text/markdown",

    url="https://github.com/petroslk/dicom2tiff.git",

    install_requires=requirements,

    packages=find_packages(),

    include_package_data=True,

    python_requires=">=3.10",

    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ["dicom2tiff=dicom2tiff.main:main"],
    },
)
