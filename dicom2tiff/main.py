import argparse
import openslide
import glob
import pydicom
import numpy as np
import tifffile
from sklearn.neighbors import KDTree
import multiprocessing
import os
from PIL import Image
import logging
import datetime
import zarr
from functools import partial
import pyvips
import tifftools

def get_args():
    parser = argparse.ArgumentParser(prog="dicom2tiff.py", description='convert dicom files to pyramidal tiff from base magnificaiton')
    parser.add_argument('dicom_folder',
                        help="input filename pattern leading to the folder where the dicom layers are stored.",
                        nargs="+",
                        type=str)
    parser.add_argument('-o', '--outdir',
                        help="outputdir, default ./output/",
                        default="./output/",
                        type=str)
    parser.add_argument('-n', '--n_process',
                        help="number of worker for multiprocessing, default is os.cpu_count()",
                        default=os.cpu_count(),
                        type=int)
    parser.add_argument('-a', '--annonimize',
                        help="rename file",
                        action="store_true")
    args = parser.parse_args()
    return args

def magnification_from_mpp(mpp):
    """
    Find the magnification from the micron per pixels value.
    /!\ pydicom give the value in minimeter per pixels so you have to multiply by 10**3 to get the mpp.
    """
    return 40*2**(np.round(np.log2(0.2425/mpp)))

def mpp_from_magnification(mag):
    return 0.2425*2**(np.round(np.log2(40/mag)))

def multiproc(function,arg_list,n_process,output=True):
    pool = multiprocessing.Pool(n_process)
    out = list(pool.imap(function,arg_list))
    pool.close()
    pool.join()
    if not output:
        return
    return sum(out,[]) if isinstance(out[0],list) else out

def divide_batch(l, n): 
    for i in range(0, len(l), n):  
        yield l[i:i + n]

def get_positions(sname):
    slide = pydicom.dcmread(sname)
    tile_position = []
    if slide.get('PerFrameFunctionalGroupsSequence'):
        # position written in (x,y) pixels coordinate
        for data in slide['PerFrameFunctionalGroupsSequence']:
            tile_position.append((data[0x0048021a][0][0x0048021e].value-1,data[0x0048021a][0][0x0048021f].value-1))
        return KDTree(tile_position)
    return None

def find_position(offset,j,col):
    #find position of the patch inside the WSI grid
    num = offset + j
    return num//col, num%col

def rgba2rgb(img):
    bg_color = "#" + "ffffff"
    thumb = Image.new("RGB", img.size, bg_color)
    thumb.paste(img, None, img)
    return thumb

def write_tiles(list_index,offset,linfo,sinfo,tree, level):
    osh = openslide.open_slide(sinfo['osh'])
    store = tifffile.imread(os.path.join(sinfo['path'],sinfo["scname"]+f"_temp.tiff"), mode='r+', aszarr=True)
    z = zarr.open(store, mode='r+')
    for index in list_index:
        write_tile(index,offset,osh,z,linfo,tree, level)
    store.close()

def write_tile(index,offset,osh,z,linfo,tree, level):
    r,c = find_position(0,index,linfo['col'])
    pos = (c*linfo['size_px'],r*linfo['size_py'])
    r,c = find_position(offset,index,linfo['col'])
    pos_offset = (c*linfo['size_px'],r*linfo['size_py'])
    if tree:
        if tree.query([pos_offset])[0].squeeze() == 0:
            region = np.array(rgba2rgb(osh.read_region(pos,level,(linfo['size_px'],linfo['size_py']))))
        else:
            region = np.full((linfo['size_px'],linfo['size_py'],3),255)
    else:
        region = np.array(rgba2rgb(osh.read_region(pos,level,(linfo['size_px'],linfo['size_py']))))
    z[r*linfo['size_py']:(r+1)*linfo['size_py'],c*linfo['size_px']:(c+1)*linfo['size_px']] = region

def slide_conversion(sinfo,files_info,n_process):
    offsets = np.array(files_info)[:,1].astype(int)
    indx_ordr = np.argsort(offsets)
    slide = pydicom.dcmread(files_info[0][0])
    #gather data
    size_py = slide[0x00280010].value
    size_px = slide[0x00280011].value

    row = int(np.ceil(slide[0x00480007].value/size_py))
    col = int(np.ceil(slide[0x00480006].value/size_px))

    height = int(row * size_py)
    width = int(col * size_px)

    linfo={}
    linfo['size_px'] = size_px
    linfo['size_py'] = size_py

    linfo['row'] = row
    linfo['col'] = col

    linfo['height'] = height
    linfo['width'] = width

    #create temp tiff
    print("|- temp tiff creation")
    tifffile.imwrite(os.path.join(sinfo['path'],sinfo["scname"]+f"_temp.tiff"),shape=(height,width,3),dtype='uint8',photometric='rgb',tile=(size_py,size_px))
    
    print("|- fill temp tiff")
    trees = multiproc(get_positions,np.array(files_info)[:,0][indx_ordr],os.cpu_count())
    for level in range(len(indx_ordr)):
        if level == indx_ordr[-1]:
            n = row*col - offsets[indx_ordr][level]
        else:
            n = offsets[indx_ordr][level+1]-offsets[indx_ordr][level]
        multiproc(partial(write_tiles,offset = offsets[indx_ordr][level], linfo = linfo, sinfo = sinfo, tree = trees[level], level = level),list(divide_batch(range(n),int(np.ceil(n/n_process)))),n_process)
    
    print("|- pyramidal tiff creation")
    image = pyvips.Image.new_from_file(os.path.join(sinfo['path'],sinfo["scname"]+f"_temp.tiff"),access='sequential')
    image.tiffsave(os.path.join(sinfo['path'],sinfo["scname"]+".tiff"),compression="jpeg",tile=True,pyramid=True,bigtiff=True)
    #write metadata
    tifftools.tiff_set(os.path.join(sinfo['path'],sinfo["scname"]+".tiff"),overwrite=True,setlist=[("ImageDescription",f"Aperio Fake |AppMag = {sinfo['mag']}|MPP = {mpp_from_magnification(sinfo['mag'])}")])
    #remove previous tiff
    os.remove(os.path.join(sinfo['path'],sinfo["scname"]+f"_temp.tiff"))

def main(args) -> None:
    outdir = args.outdir
    slidedirs = args.dicom_folder
    n_process = args.n_process
    annonimize = args.annonimize
    os.mkdir(outdir) if not os.path.exists(outdir) else None
    log_filename = f"{outdir}/conversion_log_"+datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
    #config logger
    logger = logging.getLogger(f"{outdir}/conversion_log_"+datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M"))

    f_handler = logging.FileHandler(f"{outdir}/conversion_log_"+datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")+".log")
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

    
    already = glob.glob(os.path.join(outdir,"*.tiff"))

    if annonimize:
        c=1
    for slidedir in slidedirs:
        sname = os.path.basename(os.path.abspath(slidedir))
        if annonimize:
            scname = "DP"+"{:04d}".format(c)
            c+=1
        else:
            scname = sname
        if os.path.join(outdir,scname+".tiff") in already:
            continue
        print(f"- Working on {sname}")
        #get files name
        list_files = glob.glob(os.path.join(slidedir,"*.dcm"))
        #get magnification and ofset
        files_info = {}
        for fname in list_files:
            try:
                slide = pydicom.dcmread(fname)
                offset = slide.get([0x0020,0x9228],0)
                if offset != 0:
                    offset = offset.value
                files_info.setdefault(magnification_from_mpp(slide[0x52009229][0][0x00289110][0][0x00280030].value[0]*10**3),[]).append([fname,offset])
            except:
                continue
        #find base magnification
        mag = np.max(list(files_info.keys()))
        files_info = files_info[mag]
        sinfo = {}
        sinfo["name"] = sname
        sinfo["scname"] = scname
        sinfo["mag"] = mag
        sinfo['path'] = outdir
        sinfo['osh'] = files_info[0][0]

        try:
            slide_conversion(sinfo,files_info,n_process)
        except Exception as e:
            logger.error(f"Slide {sname} failed: {e}", exc_info=True)

    if os.stat(os.path.join(log_filename+".log")).st_size == 0:
            os.remove(os.path.join(log_filename+".log"))
            print(f"No error detected, Empty log deleted.")

if __name__ == "__main__":
    args = get_args()
    main(args)
