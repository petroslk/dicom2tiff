import zarr
import pyvips
import os
import numpy as np
from tqdm import tqdm
import pyvips
import tifffile
import pydicom
import multiprocessing
from functools import partial
import shutil
import itertools
import tifftools

def magnification_from_mpp(mpp): 
    """
    Find the magnification from the micron per pixels value.
    /!\ pydicom give the value in minimeter per pixels so you have to multiply by 10**3 to get the mpp.
    """
    return 40*2**(np.round(np.log2(0.2425/mpp)))

def mpp_from_magnification(mag):
    return 0.2425*2**(np.round(np.log2(40/mag)))

def divide_batch(arr, batch_size):
    # Function to divide an array into batches
    return [arr[i:i + batch_size] for i in range(0, len(arr), batch_size)]

def find_position(offset,j,col):
    #find position of the patch inside the WSI grid
    num = offset + j
    return num//col, num%col

def write_to_zarr(input,offset,color_space,linfo,sinfo,tile_position):
    patch,ind = input
    #load as zarr
    store = tifffile.imread(os.path.join(sinfo['path'],sinfo["name"]+f"_df{int(sinfo['base_mag']/sinfo['mag'])}.tiff"), mode='r+', aszarr=True)
    z = zarr.open(store, mode='r+')

    if tile_position:
        z[tile_position[ind][1]:tile_position[ind][1]+linfo['size_py'],tile_position[ind][0]:tile_position[ind][0]+linfo['size_px']] = convert_to_rgb(patch,color_space)
    else:
        r,c = find_position(offset,ind,linfo['col'])
        z[r*linfo['size_py']:(r+1)*linfo['size_py'],c*linfo['size_px']:(c+1)*linfo['size_px']] = convert_to_rgb(patch,color_space)
    store.close()

def convert_to_rgb(patch,color_space):
    return pydicom.pixel_data_handlers.util.convert_color_space(patch,color_space,'RGB')

def convert_level(list_name_offset,sinfo,n_process,convert_partial):
    #convert a magnification to tiff
    if len(list_name_offset) != 1:
        print("    Dicom slide is not openslide compatible.")
        convert_merge_file(list_name_offset,sinfo,n_process)
    elif convert_partial:
        print("    Slide is dicom compatible.")
        convert_merge_file(list_name_offset,sinfo,n_process)
    else:
        print("Slide is dicom compatible, it will not be converted to tiff.")
        return False
    return True

def create_pyramidal_tiff(sinfo):
    print("|-Creating pyramidal tiff")
    #get name
    sname = sinfo['name']

    #open tiff slide
    image = pyvips.Image.new_from_file(os.path.join(sinfo['path'],sinfo["name"]+f"_df{int(sinfo['base_mag']/sinfo['mag'])}.tiff"),access='sequential')

    #create pyramidal tiff
    image.tiffsave(os.path.join(sinfo['path'],sname+".tif"),compression="jpeg",tile=True,pyramid=True,bigtiff=True)
    
    #write metadata
    tifftools.tiff_set(os.path.join(sinfo['path'],sname+".tif"),overwrite=True,setlist=[("ImageDescription",f"Aperio Fake |AppMag = {sinfo['base_mag']}|MPP = {mpp_from_magnification(sinfo['base_mag'])}")])

    #remove previous tiff
    os.remove(os.path.join(sinfo['path'],sname+f"_df1.tiff"))
    
def convert_single_file(list_name_offset,sinfo):
    #case where a magnification has only one file
    print(f"|- work on level at {sinfo['mag']}x")
    print("    Starting converting to tiff:")
    #copy level in single folder so that openslide can read it
    file_path = list_name_offset[0][0]
    sname = sinfo['name']

    os.mkdir(os.path.join(sinfo['path'],"temp")) if not os.path.exists(os.path.join(sinfo['path'],"temp")) else None
    shutil.copyfile(file_path,os.path.join(sinfo['path'],"temp/"+sname))

    #read with openslide
    image = pyvips.Image.openslideload(os.path.join(sinfo['path'],"temp/"+sname))

    #convert
    image.tiffsave(os.path.join(sinfo['path'],sname+f"_df{int(sinfo['base_mag']/sinfo['mag'])}.tif"),compression="jpeg",tile=True,bigtiff=True)
    
    #remove temp file
    os.remove(os.path.join(sinfo['path'],"temp/"+sname))

def write_in_tiff(list_name_offset,sinfo,linfo,n_process,file_num):
    #gather data
    
    #open file
    slide = pydicom.dcmread(list_name_offset[file_num][0])
    
    tile_full = True
    tile_position = []
    if slide.get('PerFrameFunctionalGroupsSequence'):
        tile_full = False
        # position written in (x,y) pixels coordinate
        for data in slide['PerFrameFunctionalGroupsSequence']:
            tile_position.append((data[0x0048021a][0][0x0048021e].value-1,data[0x0048021a][0][0x0048021f].value-1))
    
    #get array (pydicom load the whole array)
    arr = slide.pixel_array
        
    #get offset
    offset = np.array(list_name_offset)[file_num,1].astype(int)
        
    #make args for multiprocessing
    args_list = [(arr[j],j) for j in range(arr.shape[0])]

    pool = multiprocessing.Pool(n_process)

    tqdm(pool.imap(partial(write_to_zarr, offset = offset, color_space = slide[0x00280004].value, linfo = linfo, sinfo = sinfo, tile_position = tile_position), args_list),desc="pooling",leave=False)
    
    # Close the pool to prevent any new tasks from being submitted.
    pool.close()

    # Wait for all of the tasks to finish.
    pool.join()

    del arr,args_list,slide

    return tile_full

def fill_patch(coord,sinfo,linfo):
    r,c = coord
    store = tifffile.imread(os.path.join(sinfo['path'],sinfo["name"]+f"_df{int(sinfo['base_mag']/sinfo['mag'])}.tiff"), mode='r+', aszarr=True)
    z = zarr.open(store, mode='r+')
    patch = z[r*linfo['size_py']:(r+1)*linfo['size_py'],c*linfo['size_px']:(c+1)*linfo['size_px']]
    if np.all(patch == 0):
        z[r*linfo['size_py']:(r+1)*linfo['size_py'],c*linfo['size_px']:(c+1)*linfo['size_px']] = 255
    store.close()

def fill_background(sinfo,linfo,n_process):
    
    print("|- fill sparse background")

    rc_pairs = list(itertools.product(range(linfo['row']), range(linfo['col'])))

    pool = multiprocessing.Pool(n_process)

    tqdm(pool.imap(partial(fill_patch, linfo = linfo, sinfo = sinfo), rc_pairs),desc="fill_background",leave=False)
    
    # Close the pool to prevent any new tasks from being submitted.
    pool.close()

    # Wait for all of the tasks to finish.
    pool.join()

def convert_merge_file(list_name_offset,sinfo,n_process):
    #case where a magnification has multiple files
    print(f"|- work on level at {sinfo['mag']}x")
    offsets = np.array(list_name_offset)[:,1].astype(int)
    indx_ordr = np.argsort(offsets)

    #open one level
    slide = pydicom.dcmread(list_name_offset[indx_ordr[0]][0])
    
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

    #create tiff
    print("    creating temp tif:")
    tifffile.imwrite(os.path.join(sinfo['path'],sinfo["name"]+f"_df{int(sinfo['base_mag']/sinfo['mag'])}.tiff"),shape=(height,width,3),dtype='uint8',photometric='rgb',tile=(size_py,size_px))

    print("    Starting to merge and convert to tiff:")
    tile_full = True
    for file_num in tqdm(indx_ordr, desc="outer" , leave=False):
        tile_full &= write_in_tiff(list_name_offset,sinfo,linfo,n_process,file_num)
    
    if not tile_full:
        fill_background(sinfo,linfo,n_process)
    
