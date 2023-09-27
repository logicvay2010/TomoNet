#!/usr/bin/env python3
import os 
import sys
import sys
import mrcfile
from TomoNet.preprocessing.cubes import create_cube_seeds_new, crop_cubes
from TomoNet.preprocessing.img_processing import normalize
from multiprocessing import Pool
import numpy as np
from TomoNet.util.utils import mkfolder
import imodmodel
import logging
from TomoNet.util.io import log
import subprocess

def inZone(c, d, crop_size):
    #print(c, d)
    if abs(c[0] - d[0]) <= crop_size//2 and abs(c[1] - d[1]) <= crop_size//2 and abs(c[2] - d[2]) <= crop_size//2 :
        return True
    else:
        return False

def getNewCoords(new_centers, old_coords, crop_size):
    new_coords = []
    for coord in old_coords:
        if inZone(new_centers, coord, crop_size):
            new_coords.append([coord[x] - new_centers[x] + (crop_size//2)  for x in range(0,3)])
    #print(new_coords)
    return new_coords

def extract_subtomos_one(tomoName, maskName, coordsFile, data_dir, label_size, numberSubtomo, crop_size, bin, check_folder=True, logger=None):
    '''
    extract subtomo from whole tomogram based on mask
    and feed to generate_first_iter_mrc to generate xx_iter00.xx
    '''
   
    log(logger, "######## Extracting subtomograms from {} ########".format(tomoName))
    baseName = os.path.basename(tomoName.split(".")[0])
    with mrcfile.open(tomoName) as mrcData:
        orig_data = mrcData.data.astype(np.float32)
    
    centers = []
    #print("break0")

    if coordsFile.endswith((".pts", ".coords")):
        with open(coordsFile) as file:
            for line in file:
                #print(line)
                #print(line.split())
                x, y, z = [int(float(i)) for i in line.split()]
                centers.append([x, y, z])
    else:
        df_mod = imodmodel.read(coordsFile)
        centers = np.vstack((df_mod.x, df_mod.y, df_mod.z)).transpose().astype(int)

    #centers = (np.array(centers)/bin).astype(int)
    #print("bin:", bin)
    centers = (np.array(centers)*bin).astype(int)
    #print(centers[0:10])
    if maskName in [None, "None"]:
        sp = orig_data.shape
        #print(sp)
        mask_data = np.zeros(sp)
        #with open(coordsFile) as file:
        for c in centers:
            #print(line)
            #print(line.split())
            #x, y, z = [int(float(i)) for i in line.split()]
            #print(c)
            x, y, z = c
            low_x = x-crop_size//2 if x > crop_size//2 else 1
            low_y = y-crop_size//2 if y > crop_size//2 else 1
            low_z = z-crop_size//2 if z > crop_size//2 else 1
            high_x = x+crop_size//2 if x < (sp[2] - crop_size//2)  else sp[2]
            high_y = y+crop_size//2 if y < (sp[1] - crop_size//2)  else sp[1]
            high_z = z+crop_size//2 if z < (sp[0] - crop_size//2)  else sp[0]
            
            mask_data[low_z:high_z, low_y:high_y, low_x:high_x] = 1

        #with mrcfile.new("mask.mrc", overwrite=True) as output_mrc:
        #    output_mrc.set_data(mask_data.astype(np.float32))
    else:
        with mrcfile.open(maskName) as m:
            mask_data = m.data

    
    #print(orig_data)
    seeds = create_cube_seeds_new(orig_data, numberSubtomo, crop_size, centers, mask=mask_data, logger=logger)
    

    label_coords = []
    for i in range(0, len(seeds[0])):
        newCoords_i = getNewCoords([seeds[2][i], seeds[1][i], seeds[0][i]], centers, crop_size)
        label_coords.append(newCoords_i)
    
    subtomos = crop_cubes(orig_data, seeds, crop_size)

    # save sampled subtomo to {results_dir}/subtomos instead of subtomo_dir (as previously does)
    base_name = os.path.splitext(os.path.basename(tomoName))[0]
    
    dirs_tomake = ['train_x','train_y', 'test_x', 'test_y']
    
    
    if check_folder:
        
        #data_dir = "data"
        mkfolder(data_dir)
        #get_cubes_list(args)
        dirs_tomake = ['train_x','train_y', 'test_x', 'test_y']
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        for d in dirs_tomake:
            folder = '{}/{}'.format(data_dir, d)
            if not os.path.exists(folder):
                os.makedirs(folder)
    #print(label_coords[:100])


    shape = subtomos[0].shape
    for j, s in enumerate(subtomos):
        #im_name = '{}/{}_{:0>6d}.mrc'.format(subtomo_dir, base_name, j)
        x_name = '{}/{}/{}_x_{}.mrc'.format(data_dir, dirs_tomake[0], baseName, j)
        label_name = '{}/{}_{:0>6d}.txt'.format("coords", base_name, j)
        y_name = '{}/{}/{}_y_{}.mrc'.format( data_dir, dirs_tomake[1], baseName, j)
        #print(j)

        #label_size = int(label_size)
        if len(label_coords[j]) > 0:
            #print(shape)
            y_temp = np.zeros(shape, dtype=np.float32)
            #with open(label_name, "w") as outfile:
            for coords in label_coords[j]:
                #mrcfile store image in zyx order
                x = coords[0]-1 if coords[0]>0 else 0
                y = coords[1]-1 if coords[1]>0 else 0
                z = coords[2]-1 if coords[2]>0 else 0
                #Gradient Probability distribution
                
                '''
                p_step = 1/label_size
                for i in range(label_size):
                    j=i+1
                    xmin = x - i if x >= j else 0
                    xmax = x + j if x <= shape[2] -j else shape[2] -1
                    ymin = y - i if y >= j else 0
                    ymax = y + j if y <= shape[1] -j else shape[1] -1
                    zmin = z - i if z >= j else 0
                    zmax = z + j if z <= shape[0] -j else shape[0] -1
                    y_temp[zmin:zmax,ymin:ymax,xmin:xmax] += p_step
                    #y_temp[zmin:zmax,ymin:ymax,xmin:xmax] = 1
                #y_temp[z,y,x] = 1
                '''
                xmin = x - label_size if x >= label_size else 0
                xmax = x + label_size + 1 if x < shape[2] - label_size else shape[2]
                ymin = y - label_size if y >= label_size else 0
                ymax = y + label_size + 1 if y < shape[1] - label_size else shape[1]
                zmin = z - label_size if z >= label_size else 0
                zmax = z + label_size + 1 if z < shape[0] - label_size else shape[0]
                
                #cube labeling
                y_temp[zmin:zmax,ymin:ymax,xmin:xmax] = 1
                #sphere labeling

            for l in range(4):
                x_name = '{}/{}/{}_x_{}_{}.mrc'.format(data_dir, dirs_tomake[0], baseName, j, l)
                y_name = '{}/{}/{}_y_{}_{}.mrc'.format( data_dir, dirs_tomake[1], baseName, j, l)

                if l == 0:
                    rotated_x = s
                    rotated_y = y_temp
                elif l ==1:
                    rotated_x = np.rot90(s, k=2, axes=(0,1))
                    rotated_y = np.rot90(y_temp, k=2, axes=(0,1))
                elif l ==2:
                    rotated_x = np.rot90(s, k=2, axes=(1,2))
                    rotated_y = np.rot90(y_temp, k=2, axes=(1,2))
                elif l ==3:
                    #rotated_x1 = np.rot90(s, k=2, axes=(0,1))
                    rotated_x = np.rot90(s, k=2, axes=(0,2))
                    #rotated_y1 = np.rot90(y_temp, k=2, axes=(0,1))
                    rotated_y = np.rot90(y_temp, k=2, axes=(0,2))

                #print(label_coords[j])
                with mrcfile.new(x_name, overwrite=True) as output_mrc:
                    #output_mrc.set_data(normalize(s*-1))
                    #output_mrc.set_data(normalize(s))
                    output_mrc.set_data(normalize(rotated_x))
                with mrcfile.new(y_name, overwrite=True) as output_mrc:
                    #output_mrc.set_data(y_temp)
                    output_mrc.set_data(rotated_y)
                    #output_mrc.set_data(normalize(y_temp))
            


def split_data(data_dir):    
    batch_size = 4
    ratio = 0.1
    all_path_x = os.listdir(data_dir+'/train_x')
    num_test = int(len(all_path_x) * ratio) 
    num_test = num_test - num_test%batch_size + batch_size
    
    #all_path_y = ['y_'+i.split('_y_')[1] for i in all_path_x ]
    all_path_y = [i.split('_x_')[0]+'_y_'+i.split('_x_')[1] for i in all_path_x ]

    ind = np.random.permutation(len(all_path_x))[0:num_test]
    for i in ind:
        os.rename('{}/train_x/{}'.format(data_dir, all_path_x[i]), '{}/test_x/{}'.format(data_dir, all_path_x[i]) )
        os.rename('{}/train_y/{}'.format(data_dir, all_path_y[i]), '{}/test_y/{}'.format(data_dir, all_path_y[i]) )
            
if __name__ == "__main__":

    import time
    start_time = time.time()
    params = sys.argv    
    input_folder = params[1]
    tomoNameList = params[2].split(",")
    result_dir= params[3]
    continue_from_model = params[4]
    label_size = int(params[5])
    subtomo_num = int(params[6])
    cube_size = int(params[7])
    coords_scale = float(params[8])
    
    ############
    bin = coords_scale
    ############

    
    if len(params) == 10:
        log_file = params[9]
        logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
    else:
        logger = None

    try:
        os.makedirs(result_dir)
    except:
        pass
    data_dir = "{}/data".format(result_dir)
    
    #log(logger, "bin:{}".format(bin))

    num_tomo = len(tomoNameList)


    if not continue_from_model == "None":
        logger.warning("using pretrained model, skip subtomogram extraction")
        data_old = "{}/data".format(os.path.dirname(continue_from_model))
        data_new = data_dir
        if os.path.exists(data_new):
            logger.info("data folder detected!")
        else:
            try:
                cmd = "cd {}; ln -s {} .".format(result_dir, data_old)
                subprocess.run(cmd, shell=True, encoding="utf-8", stdout=subprocess.PIPE)
                logger.info("link data folder to the new result folder")
            except:
                logger.error("data folder not detected from folder {}".format(os.path.dirname(continue_from_model)))
        
        sys.exit()

    mkfolder(data_dir)
    tomoList = []
    coordsList = []
    maskList = []
    for tomo in tomoNameList:
        f = "{}/{}.mrc".format(input_folder,tomo)
        #mask_file = None
        if os.path.exists(f):
            tomoList.append(f)
            mask_file = "{}/{}_mask{}".format(input_folder, tomo, ".mrc")
        else:
            tomoList.append("{}/{}.rec".format(input_folder,tomo))
            mask_file = "{}/{}_mask{}".format(input_folder, tomo, ".rec")
        if os.path.exists(mask_file):
            maskList.append(mask_file)
        else:
            maskList.append(None)
        fc1 = "{}/{}.mod".format(input_folder,tomo)
        fc2 = "{}/{}.pts".format(input_folder,tomo)
        fc3 = "{}/{}.coords".format(input_folder,tomo)
        if os.path.exists(fc1):
            coordsList.append(fc1)
        elif os.path.exists(fc2):
            coordsList.append(fc2)
        else:
            coordsList.append(fc3)
    #coordsList = params[3].split(",")
    log(logger, "Start subtomograms Extraction!")
    extract_subtomos_one(tomoList[0], maskList[0], coordsList[0], data_dir, label_size, subtomo_num, cube_size, logger=logger, bin=bin)
    for i, tomo in enumerate(tomoList[1:]):
        extract_subtomos_one(tomo, maskList[i+1], coordsList[i+1], data_dir, label_size, subtomo_num, cube_size, bin=bin, check_folder=False, logger=logger)
    
    split_data(data_dir)

    log(logger, "Extraction Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))