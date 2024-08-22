#!/usr/bin/env python3
import os,sys
import logging
import shutil
import subprocess
import time
import glob
import mrcfile

import scipy.cluster.hierarchy as hcluster
import numpy as np

from TomoNet.preprocessing.cubes import normalize
from TomoNet.util.io import log
from TomoNet.util.utils import mkfolder

# used for extract sort keys
def natural_keys(text, delimiter='_', index=-2):
    return int(text.split(delimiter)[index])

if __name__ == "__main__":

    start_time = time.time()

    from TomoNet.models.network_isonet_mse import Net
    
    # read parameters
    params = sys.argv
    tomoName = sys.argv[1]
    result_dir = sys.argv[2]
    model_file = sys.argv[3]
    crop_size = int(sys.argv[4])
    cube_size = int(sys.argv[5])
    
    #check whether running using terminal (12) or GUI (13) 
    # if len(params) == 13:
    #     log_file = params[12]
    #     logger = logging.getLogger(__name__)
    #     handler = logging.FileHandler(filename=log_file, mode='a')
    #     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    #     handler.setFormatter(formatter)
    #     formatter.datefmt = "%y-%m-%d %H:%M:%S"
    #     logger.handlers = [handler]
    #     logger.setLevel(logging.INFO)
    # else:
    logger = None

    # mode for output results for each patch (for debuging)
    save_patch_MODE = False


    # create result folder
    if not os.path.exists(result_dir):
        os.mkdir(result_dir)
    
    # data folder storing intermediate subtomograms
    data_dir = "{}/data".format(result_dir)
    mkfolder(data_dir)

    # get the current tomogram base name and read 3D volume
    log(logger, "######## Predicting tomogram {} ########".format(tomoName))
    baseName = tomoName.split('/')[-1].split('.')[0]
    
    # read global input 3D volume
    with mrcfile.open(tomoName) as mrcData:
        orig_data = mrcData.data.astype(np.float32)*-1
    

    sp = np.array(orig_data.shape)

    # margin related to overlaping region (pad_width) when extracting subtomograms
    margin_1 = (crop_size - cube_size)//2
    pad_width = (cube_size - (sp-2*margin_1)%cube_size)%cube_size//2
    
    # padded 3D volume data
    pad_orig_data = np.pad(orig_data, ((pad_width[0], pad_width[0]),(pad_width[1], pad_width[1]),(pad_width[2], pad_width[2])), 'mean')
    orig_data = pad_orig_data
    sp = np.array(orig_data.shape)
    
    # number of cubes (x, y, z axis)
    sidelen = (sp-2*margin_1)//cube_size

    # crop starting coords (origin)
    crop_start = margin_1

    #prepare for extraction (get all subtomograms center locations)
    count = 0
    location_origins = "{}/location_origins.txt".format(result_dir)
    location_origins_list = []
    log(logger, "Calculated subtomos #:{}".format(sidelen[0]*sidelen[1]*sidelen[2]))

    # get subtomograms center coordinates
    for i in range(sidelen[0]):
        for j in range(sidelen[1]):
            for k in range(sidelen[2]):

                # boundaries of the current cube
                z1,z2 = [i*cube_size, i*cube_size+crop_size]
                y1,y2 = [j*cube_size, j*cube_size+crop_size]
                x1,x2 = [k*cube_size, k*cube_size+crop_size]
                
                # extract cube from global map
                cube = orig_data[z1:z2, y1:y2, x1:x2]
                cube = normalize(cube)
                
                # write to disk
                x_name = "{}/x_{}.mrc".format(data_dir, count)
                with mrcfile.new(x_name, overwrite=True) as output_mrc:
                    output_mrc.set_data(cube)
                count+=1
                location_origins_list.append([z1,y1,x1])

    # only cube overlaping with mask will be used    
    log(logger, "Actual used subtomos #:{}".format(count))

    # so, if no cube was detected, stop here 
    if count == 0:
        log(logger, "The crop size = box size + 8 which is {} and it is larger than the dimension of input tomogram: {}.".format(crop_size, np.flip(sp)), level="error")
        sys.exit()

    # read all cube volume into memory
    all_mrc_list = []
    for it in glob.glob("{}/*".format(data_dir)):
        all_mrc_list.append(it)
    
    print(len(all_mrc_list))
    # load trained neural network
    network = Net(filter_base = 64, out_channels=1)
    network.load(model_file)

    # network inference for all the cubes
    pred_dir = "{}/predict".format(result_dir)
    mkfolder(pred_dir)
    
    network.predict(all_mrc_list[:], pred_dir, iter_count=0, inverted=False)

    log(logger,"Subtomogram Predict Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))
    
    # Starting get coordinates info from the seg maps
    start_time = time.time()
    log(logger,"###### Start getting particles locations ######")
    all_mrc_pred_list = []
    for it in glob.glob("{}/*".format(pred_dir)):
        if it.endswith(".mrc"):
            all_mrc_pred_list.append(it)

    # This is important, since the global location info for each cube is encoded in it's filename. Has to place back based on the number in the filename 
    all_mrc_pred_list.sort(key=natural_keys)
    
    #global map initialization
    global_map = np.ones(sp, dtype=np.float32)


    # create result folder for current tomogram ( particle locations )
    tomoName_final = "{}_final".format(baseName)
    tomo_current_dir = "{}/{}".format(result_dir, tomoName_final)
    mkfolder(tomo_current_dir)

    # handling each prediction seg map
    for i in range(len(all_mrc_pred_list)):
        pred = all_mrc_pred_list[i]
        # get global coords of the current prediciton
        ind = int(pred.split("_")[-2])
        z_crop, y_crop, x_crop = location_origins_list[ind]

        # read into memory
        with mrcfile.open(pred) as mrc:
            y_map = mrc.data[0]
        
        # in network.predict, only density with positive value will be considerred related to particles
        #points = np.argwhere(y_map > 0.1)
        # filter based on the # of activated pixels
        
            
        # connected voxels will be clustered into the same particle (a block of voxels)
        #global_map[z_crop:z_crop+crop_size, y_crop:y_crop+crop_size, x_crop:x_crop+crop_size] = 63*y_map+1
        #global_map[z_crop:z_crop+crop_size, y_crop:y_crop+crop_size, x_crop:x_crop+crop_size] = y_map*-1
        global_map[z_crop:z_crop+crop_size, y_crop:y_crop+crop_size, x_crop:x_crop+crop_size] = y_map*-1

    
    global_map_filename = "{}/{}/predict.mrc".format(result_dir, tomoName_final)
    with mrcfile.new(global_map_filename, overwrite=True) as output_mrc:
        output_mrc.set_data(global_map)

    # clean up intermediate results
    # if os.path.exists(pred_dir):
    #     shutil.rmtree(pred_dir)
    # if os.path.exists("{}~".format(pred_dir)):
    #     shutil.rmtree("{}~".format(pred_dir))
    # if os.path.exists(data_dir):
    #     shutil.rmtree(data_dir)
    log(logger, "Particles saved for {} --- {} mins ---".format(baseName, round((time.time() - start_time)/60, 2)))
    
