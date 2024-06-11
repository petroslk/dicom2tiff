import os
import glob
import numpy as np
import pydicom
import argparse
import logging
import datetime
from .utils import magnification_from_mpp, convert_level, create_pyramidal_tiff

def main():
    parser = argparse.ArgumentParser(prog="dicom2tiff", description='Convert DICOM files to pyramidal TIFF from base magnification')
    parser.add_argument('dicom_folder',
                        help="Input filename pattern leading to the folder where the DICOM layers are stored.",
                        nargs="+",
                        type=str)
    parser.add_argument('-o', '--outdir',
                        help="Output directory, default ./output/",
                        default="./output/",
                        type=str)
    parser.add_argument('-c', '--convert_partial',
                        help="Only convert non openslide compatible DICOM directories",
                        action="store_false")
    parser.add_argument('-n', '--n_process',
                        help="Number of workers for multiprocessing, default is os.cpu_count()",
                        default=None,
                        type=int)
    args = parser.parse_args()

    # Configure logger
    now = datetime.datetime.now()
    logger = logging.getLogger("dicom2tiff_" + f"{now.year}_{now.month}_{now.hour}_{now.minute}")

    f_handler = logging.FileHandler("dicom2tiff_" + f"{now.year}_{now.month}_{now.hour}_{now.minute}.txt")
    c_handler = logging.StreamHandler()

    c_handler.setLevel(logging.WARNING)
    f_handler.setLevel(logging.ERROR)

    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    # Get args
    slide_dirs = args.dicom_folder
    out_dir = args.outdir
    convert_partial = args.convert_partial
    n_process = args.n_process

    os.makedirs(out_dir, exist_ok=True)

    fail = []
    for slide_dir in slide_dirs:
        slide_name = os.path.basename(os.path.dirname(slide_dir))
        print(f"- Working on {slide_name}")
        # Get files name
        list_files = glob.glob(slide_dir + "/*")

        # Get magnification and offset
        slides_names = {}
        for names in list_files:
            slide = pydicom.dcmread(names)
            offset = slide.get((0x0020, 0x9228), 0)
            if offset != 0:
                offset = offset.value
            slides_names.setdefault(magnification_from_mpp(slide[0x52009229][0][0x00289110][0][0x00280030].value[0] * 10 ** 3), []).append([names, offset])

        # Find base magnification
        base_mag = np.max(list(slides_names.keys()))
        mag = base_mag

        # Get file at base magnification
        list_name_offset = slides_names[base_mag]

        sinfo = {
            "name": slide_name,
            "base_mag": base_mag,
            "mag": mag,
            'path': out_dir
        }

        # Convert and create a pyramidal TIFF
        try:
            if convert_level(list_name_offset, sinfo, n_process, convert_partial):
                create_pyramidal_tiff(sinfo)
        except Exception as e:
            logger.error(f"File {slide_name} failed: {e}", exc_info=True)
            fail.append(slide_name)

    for sname in fail:
        print(f"o Slide {sname} failed to convert")

if __name__ == "__main__":
    main()
