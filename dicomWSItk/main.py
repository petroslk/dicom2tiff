import os
import numpy as np
import argparse
import logging
import datetime
import sys
import csv
import shutil
import pyvips
import tifftools
from .makeOpenslideCompatible import get_info_slide,makeOsCompat, rename_slide_files
from . import __version__

def mpp_from_magnification(mag):
    return 0.2425*2**(np.round(np.log2(40/mag)))

def main():

    parser = argparse.ArgumentParser(prog="dicomWSItk", description='A small toolkit for anonymizing and making DICOM WSI files openslide compatible',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', action='version', version=f'dicomWSItk {__version__}')
    subparsers = parser.add_subparsers(title="tools", help="dicomWSItk subtools: merge_layers", dest='tools')


    merge_layers_parser = subparsers.add_parser("merge_layers", help="Make DICOM WSI directory openslide compatible by concatenating dicom files for each magnification")

    merge_layers_parser.add_argument('dicom_directories',
                        help="Input filename pattern leading to the folder where the DICOM layers are stored.",
                        nargs="+",
                        type=str)
    merge_layers_parser.add_argument('-o', '--outdir',
                        help="output directory, if None then conversion is done inplace",
                        default=None,
                        type=str)


    dicom2tiff_parser = subparsers.add_parser("dicom2tiff", help='Convert DICOM files to pyramidal TIFF from base magnification')
    
    dicom2tiff_parser.add_argument('dicom_directories',
                        help="Input filename pattern leading to the folder where the DICOM layers are stored.",
                        nargs="+",
                        type=str)
    dicom2tiff_parser.add_argument('-o', '--outdir',
                        help="output directory, if None then conversion is done inplace",
                        default=None,
                        type=str)
    dicom2tiff_parser.add_argument('-a', '--anonymize',
                        help="Rename files for anonymization",
                        action="store_true",
                        default=False)
    dicom2tiff_parser.add_argument('-p', '--project_name',
                        help="Name of project for anonymization file names (only used in case of anonymization)",
                        default="PROJ",
                        type=str)
    dicom2tiff_parser.add_argument('-c', '--csv_path',
                        help="Path to directory of csv with file name and anonymized file name correspondence",
                        default="./",
                        type=str)
    args = parser.parse_args()
    

    if args.tools =="merge_layers":
        slide_dirs = args.dicom_directories
        outdir = args.outdir
        if outdir:
            os.makedirs(outdir, exist_ok=True)

        # Configure logger
        log_filename = f"dicomwsitk_log_"+datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
        logger = logging.getLogger(log_filename)

        f_handler = logging.FileHandler(os.path.join(log_filename+".log"))
        c_handler = logging.StreamHandler()

        c_handler.setLevel(logging.WARNING)
        f_handler.setLevel(logging.ERROR)

        # Create formatters and add it to handlers
        c_format = logging.Formatter('%(name)s - %(levellevel)s - %(message)s')
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

        fail = []
        for spath in slide_dirs:
            spath = os.path.abspath(spath)
            sname = os.path.basename(spath)
            
            print(f"- Working on {sname}")

            
            slide_info = get_info_slide(spath)
            base_mag = np.max(list(slide_info.keys()))
            
            if np.max([len(v) for v in slide_info.values()])!=1:
                if outdir:
                    shutil.copytree(spath,os.path.join(outdir,sname))
                    spath = os.path.join(outdir,sname)
                    for m in slide_info:
                        for i in range(len(slide_info[m])):
                            slide_info[m][i] = os.path.join(spath,os.path.basename(slide_info[m][i]))
                makeOsCompat(slide_info,spath,sname)
                basefile = os.path.join(spath,sname+"_0.dcm")
            else:
                rename_slide_files(slide_info, spath, sname, outdir)
                basefile = slide_info[base_mag]
                


    elif args.tools =="dicom2tiff":

        # Get args
        slide_dirs = args.dicom_directories
        outdir = args.outdir
        anon = args.anonymize
        proj_name = args.project_name
        csv_path = os.path.abspath(args.csv_path)

        os.makedirs(outdir, exist_ok=True)
        os.makedirs(csv_path, exist_ok=True)

        # Configure logger
        log_filename = f"{outdir}/dicomwsitk_log_"+datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
        logger = logging.getLogger(log_filename)

        f_handler = logging.FileHandler(os.path.join(log_filename+".log"))
        c_handler = logging.StreamHandler()

        c_handler.setLevel(logging.WARNING)
        f_handler.setLevel(logging.ERROR)

        # Create formatters and add it to handlers
        c_format = logging.Formatter('%(name)s - %(levellevel)s - %(message)s')
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

        if anon:
            anonymization_data = []

            # If CSV file exists, load existing data
            if os.path.exists(os.path.join(csv_path,f"anonymization_table_{proj_name}.csv")):
                try:
                    with open(csv_path, mode='r', newline='') as infile:
                        reader = csv.DictReader(infile)
                        anonymization_data.extend(reader)
                except Exception as e:
                    logger.error(f"Error reading the CSV file: {e}")
                    sys.exit(1)

            anon_index = len(anonymization_data)

        fail = []
        for spath in slide_dirs:
            spath = os.path.abspath(spath)
            sname = os.path.basename(spath)
            
            print(f"- Working on {sname}")

            if anon:
                anon_index += 1
                anonymized_name = f"ANON_{proj_name}_{anon_index:08d}.tiff"
                anonymization_data.append({
                    "original_filename": sname,
                    "anonymized_filename": anonymized_name
                })
                print(f"- Renaming {sname} to {anonymized_name}")
                # Rename the file or handle the file processing here
            else:
                anonymized_name = sname
            
            slide_info = get_info_slide(spath)
            base_mag = np.max(list(slide_info.keys()))
            
            if np.max([len(v) for v in slide_info.values()])!=1:
                if outdir:
                    shutil.copytree(spath,os.path.join(outdir,sname))
                    spath = os.path.join(outdir,sname)
                    for m in slide_info:
                        for i in range(len(slide_info[m])):
                            slide_info[m][i] = os.path.join(spath,os.path.basename(slide_info[m][i]))
                makeOsCompat(slide_info,spath,sname)
                basefile = os.path.join(spath,sname+"_0.dcm")
            else:
                basefile = slide_info[base_mag]
                outdir = os.path.dirname(spath)
            
            image = pyvips.Image.openslideload(basefile)
            image.tiffsave(os.path.join(outdir,anonymized_name+".tiff"),compression="jpeg",tile=True,bigtiff=True)

            #write metadata
            tifftools.tiff_set(os.path.join(outdir,anonymized_name+".tiff"),overwrite=True,setlist=[("ImageDescription",f"Aperio Fake |AppMag = {base_mag}|MPP = {mpp_from_magnification(base_mag)}")])

            if os.path.exists(os.path.join(outdir,sname)):
                shutil.rmtree(os.path.join(outdir,sname))

        if anon:
            # Save or update the CSV file
            output_csv = os.path.join(outdir, f"anonymization_table_{proj_name}.csv")

            with open(output_csv, mode='w', newline='') as outfile:
                fieldnames = ['original_filename', 'anonymized_filename']
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(anonymization_data)

            print(f"Anonymization table saved to {output_csv}")
    else:
        raise ValueError("Please pick one of the following options: merge_layers, dicom2tiff")

    for sname in fail:
        print(f"o Slide {sname} failed to convert")
        
    if os.stat(os.path.join(log_filename+".log")).st_size == 0:
        os.remove(os.path.join(log_filename+".log"))
        print(f"No error detected, Empty log deleted.")

if __name__ == "__main__":
    main()
