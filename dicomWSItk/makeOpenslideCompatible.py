import numpy as np
import os
import glob
import pydicom
import shutil
import argparse
import jpype
import jpype.imports
import sys
import pkg_resources

jar_path = pkg_resources.resource_filename('dicomWSItk', 'pixelmed.jar')

# Start the JVM
jpype.startJVM(classpath=[jar_path])
# Start the JVM
# jpype.startJVM(classpath=[os.path.join(os.path.dirname(__file__),'pixelmed.jar')])

# Import the Java classes to concatenate Dicom
from com.pixelmed.apps import MergeConcatenationInstances

def magnification_from_mpp(mpp):
    """
    Find the magnification from the micron per pixels value.
    /!\ pydicom give the value in minimeter per pixels so you have to multiply by 10**3 to get the mpp.
    """
    return 40*2**(np.round(np.log2(0.2425/mpp)))

def get_info_slide(spath):
    i=1
    #get files name
    list_files = [p for p in glob.glob(os.path.join(spath,"*.dcm")) if not "dcm.graphics" in p]
    list_files_sorted = sorted(list_files, key=os.path.getsize, reverse=True)
    #get magnification and ofset
    files_info = {}
    for fname in list_files_sorted:
        try:
            slide = pydicom.dcmread(fname)
            mag = magnification_from_mpp(slide[0x52009229][0][0x00289110][0][0x00280030].value[0]*10**3)
            if mag < 1:
                files_info.setdefault(-i,[]).append(fname)
                i+=1
            else:
                files_info.setdefault(mag,[]).append(fname)
        except:
            continue
    return files_info

def makeOsCompat(slide_info,spath,sname) -> None:
    i=0
    for m in np.sort(list(slide_info.keys()))[::-1]:
        if len(slide_info[m])>1:
            #copy files with same mag to temp dir
            os.mkdir(os.path.join(spath,"temp"))
            for fpath in slide_info[m]:
                os.rename(fpath,os.path.join(spath,"temp",os.path.basename(fpath)))
            
            #create output dir
            os.mkdir(os.path.join(spath,sname+f"_{i}"))
            
            #concatenate dicom files
            MergeConcatenationInstances.main([os.path.join(spath,"temp"),os.path.join(spath,sname+f"_{i}")])
            
            #move and rename concatenate file
            temp = glob.glob(os.path.join(spath,sname+f"_{i}","**/*.dcm"), recursive=True)[0]
            os.rename(temp,os.path.join(spath,sname+f"_{i}",sname+f"_{i}.dcm"))
            
            #remove temp files
            [shutil.rmtree(p) for p in glob.glob(os.path.join(spath,sname+f"_{i}","*")) if not p.endswith(".dcm")]
            shutil.rmtree(os.path.join(spath,"temp"))
        else:
            #isolate mag
            os.mkdir(os.path.join(spath,sname+f"_{i}"))
            os.rename(slide_info[m][0],os.path.join(spath,sname+f"_{i}",sname+f"_{i}.dcm"))
        i+=1
    for j in range(i):
        #put back all the mag files in place
        os.rename(os.path.join(spath,sname+f"_{j}",sname+f"_{j}.dcm"),os.path.join(spath,sname+f"_{j}.dcm"))
        shutil.rmtree(os.path.join(spath,sname+f"_{j}"))

def get_args():
    """Parsing command line arguments"""
    parser = argparse.ArgumentParser(prog="makeOpenslideCompatible.py", description='make Dicom file openslide compatible by concatenating files with same magnification')
    
    parser.add_argument('dicom_folders',
                        help="input filename pattern.",
                        nargs="+",
                        type=str)
    parser.add_argument('-o', '--outdir',
                        help="output directory, if None then conversion is done inplace",
                        default=None,
                        type=str)

    args = parser.parse_args()

    return args

def makeOpenslideCompatible(spaths,outdir=None) -> None:
    
    #get input files
    if len(spaths)==1:
        #input is a glob pattern
        spaths = glob.glob(spaths[0])
    
    if outdir:
        os.mkdir(outdir) if not os.path.exists(outdir) else None
    
    for spath in spaths:
        spath = os.path.abspath(spath)
        name = os.path.basename(spath)
        
        #if not inplace, copy file to output directory
        if outdir:
            shutil.copytree(spath,os.path.join(outdir,name))
            spath = os.path.join(outdir,os.path.basename(spath))
        
        #remove unneeded files
        toremove = glob.glob(os.path.join(spath,"*.import"))+glob.glob(os.path.join(spath,"*dcm.graphics*"))
        [os.remove(p) for p in toremove]
        
        #get slide info
        slide_info = get_info_slide(spath)
        
        #convert Dicom
        makeOsCompat(slide_info,spath,name)

def rename_slide_files(slide_info, spath, sname, outdir=None):
    i = 0
    for m in np.sort(list(slide_info.keys()))[::-1]:
        if outdir:
            os.makedirs(outdir, exist_ok=True)
            os.mkdir(os.path.join(outdir, sname + f"_{i}"))
            os.rename(slide_info[m][0], os.path.join(outdir, sname + f"_{i}", sname + f"_{i}.dcm"))
        else:
            os.mkdir(os.path.join(spath, sname + f"_{i}"))
            os.rename(slide_info[m][0], os.path.join(spath, sname + f"_{i}", sname + f"_{i}.dcm"))
        i += 1
    for j in range(i):
        if outdir:
            os.rename(os.path.join(outdir, sname + f"_{j}", sname + f"_{j}.dcm"), os.path.join(outdir, sname + f"_{j}.dcm"))
            shutil.rmtree(os.path.join(outdir, sname + f"_{j}"))
        else:
            os.rename(os.path.join(spath, sname + f"_{j}", sname + f"_{j}.dcm"), os.path.join(spath, sname + f"_{j}.dcm"))
            shutil.rmtree(os.path.join(spath, sname + f"_{j}"))


if __name__ == "__main__":
    args = get_args()
    spaths = args.dicom_folders
    outdir = args.outdir
    makeOpenslideCompatible(spaths,outdir)
