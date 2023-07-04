import glob
import os
import argparse
import subprocess
import pyvips
from tqdm import tqdm
import datetime

def convert_dicom_to_tiff(input_file, output_dir):

    # Step 1: Convert DICOM to single layer TIFF using bfconvert
    base_filename, _ = os.path.splitext(os.path.basename(input_file))
    intermediate_file = os.path.join(output_dir, f"{base_filename}.tiff")
    output_file = os.path.join(output_dir, f"{base_filename}_converted.tiff")
    print(f"Launching bfconvert for :{base_filename}")
    bfconvert_command = ["bfconvert", "-compression","LZW", "-bigtiff", input_file, intermediate_file]
    subprocess.run(bfconvert_command, check=True)

    # Step 2: Load the single layer TIFF into pyvips
    image = pyvips.Image.new_from_file(intermediate_file, access="sequential")

    # Compute microns per pixel using the resolution
    mpp_x = 1000 / image.get('xres')  # Converting from cm^-1 to µm per pixel
    mpp_y = 1000 / image.get('yres')  # Converting from cm^-1 to µm per pixel

    # Extracting existing comment and appending MPP information
    comment = image.get("image-description")
    comment += f"\nMPP: {mpp_x}, {mpp_y}"
    image.set("image-description", comment)

    print(f"Saving pyramid for :{base_filename}")
    # Step 3: Convert TIFF to pyramid using pyvips and populate metadata
    image.tiffsave(output_file, compression = "jpeg", tile=True, pyramid=True)

    # Step 4: Remove the intermediate file
    os.remove(intermediate_file)

def find_largest_file(directory):
    list_of_files = glob.glob(directory + '/*')
    largest_file = max(list_of_files, key=os.path.getsize)
    return largest_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert DICOM to pyramid TIFF.")
    parser.add_argument("directories", type=str, nargs='+', help="Directories containing the DICOM files.")
    parser.add_argument("--output_dir", type=str, default="converted_slides", help="Output directory for TIFF files.")
    args = parser.parse_args()

    
    # Find the largest file in each directory
    files_to_process = [find_largest_file(dir) for dir in args.directories]
    print(f"Processing the following files with dicom2tiff: {[os.path.basename(file) for file in files_to_process]}")
    for file in tqdm(files_to_process):
        convert_dicom_to_tiff(file, args.output_dir)


if __name__ == "__main__":
    main()    

    
