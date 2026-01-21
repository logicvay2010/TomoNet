#!/usr/bin/env python3
import os, sys, logging, subprocess
import mrcfile
import imodmodel
import numpy as np

from TomoNet.util.io import log
from TomoNet.util.utils import mkfolder
from TomoNet.preprocessing.cubes import create_cube_seeds_new, crop_cubes, normalize
from TomoNet.util.searchParam import SearchParam 

# check if coord d is inside the cube with center c
def inZone(c, d, crop_size):
    if abs(c[0] - d[0]) <= crop_size//2 and abs(c[1] - d[1]) <= crop_size//2 and abs(c[2] - d[2]) <= crop_size//2 :
        return True
    else:
        return False

# check if the new coords is valid
def getNewCoords(new_centers, old_coords, crop_size):
    new_coords = []
    for coord in old_coords:
        if inZone(new_centers, coord, crop_size):
            new_coords.append([coord[x] - new_centers[x] + (crop_size//2)  for x in range(0,3)])
    return new_coords

# subtomogram extraction for one tomogram
def extract_subtomos_one(tomoName, maskName, coordsFile, data_dir, label_size, numberSubtomo, crop_size, bin, check_folder=True, logger=None):

    log(logger, "######## Extracting subtomograms from {} ########".format(tomoName))
    # read 3D volume
    # if tomoName.startswith('.'):
    #     baseName = os.path.basename(tomoName.split(".")[1])
    # else:
    baseName = os.path.basename(tomoName).split(".")[0]

    with mrcfile.open(tomoName) as mrcData:
        orig_data = mrcData.data.astype(np.float32)
    
    # centers of subtomograms
    centers = []

    # read coordinates info
    if coordsFile.endswith((".pts", ".coords")):
        with open(coordsFile) as file:
            for line in file:
                x, y, z = [int(float(i)) for i in line.split()]
                centers.append([x, y, z])
    else:
        df_mod = imodmodel.read(coordsFile)
        centers = np.vstack((df_mod.x, df_mod.y, df_mod.z)).transpose().astype(int)

    # scale coords
    centers = (np.array(centers)*bin).astype(int)
        
    # handling mask
    if maskName in [None, "None"]:
        sp = orig_data.shape
        mask_data = np.zeros(sp)

        # generating mask near density with particles
        for c in centers:
            x, y, z = c

            low_x = x-crop_size//2 if x > crop_size//2 else 1
            low_y = y-crop_size//2 if y > crop_size//2 else 1
            low_z = z-crop_size//2 if z > crop_size//2 else 1
            high_x = x+crop_size//2 if x < (sp[2] - crop_size//2)  else sp[2]
            high_y = y+crop_size//2 if y < (sp[1] - crop_size//2)  else sp[1]
            high_z = z+crop_size//2 if z < (sp[0] - crop_size//2)  else sp[0]
            
            mask_data[low_z:high_z, low_y:high_y, low_x:high_x] = 1

        #check mask using density map
        #with mrcfile.new("mask.mrc", overwrite=True) as output_mrc:
        #    output_mrc.set_data(mask_data.astype(np.float32))
    else:
        with mrcfile.open(maskName) as m:
            mask_data = m.data

    # generating seeds(centers) locations for subtomograms
    seeds = create_cube_seeds_new(orig_data, numberSubtomo, crop_size, centers, mask=mask_data, logger=logger)
    if seeds == None:
        return
    # check if all seeds locations are valid and they will be used for labeling volume generation
    label_coords = []
    for i in range(0, len(seeds[0])):
        newCoords_i = getNewCoords([seeds[2][i], seeds[1][i], seeds[0][i]], centers, crop_size)
        label_coords.append(newCoords_i)
    
    # crop from the global volume and save to individual subtomogram on disk
    subtomos = crop_cubes(orig_data, seeds, crop_size)

    # if the extraction folder was not generated, then make one, all subtomograms will be saved to train and test subsets
    #base_name = os.path.splitext(os.path.basename(tomoName))[0]
    dirs_tomake = ['train_x','train_y', 'test_x', 'test_y']
    if check_folder:        
        mkfolder(data_dir)
        dirs_tomake = ['train_x','train_y', 'test_x', 'test_y']
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        for d in dirs_tomake:
            folder = '{}/{}'.format(data_dir, d)
            if not os.path.exists(folder):
                os.makedirs(folder)

    shape = subtomos[0].shape
    for j, s in enumerate(subtomos):
        x_name = '{}/{}/{}_x_{}.mrc'.format(data_dir, dirs_tomake[0], baseName, j)
        y_name = '{}/{}/{}_y_{}.mrc'.format( data_dir, dirs_tomake[1], baseName, j)

        if len(label_coords[j]) > 0:
            y_temp = np.zeros(shape, dtype=np.float32)
            random_indices_x = np.random.choice(y_temp.shape[2], int(y_temp.shape[2]))
            random_indices_y = np.random.choice(y_temp.shape[1], int(y_temp.shape[1]))
            random_indices_z = np.random.choice(y_temp.shape[0], int(y_temp.shape[0]))
            random_indices = list(zip(random_indices_z, random_indices_y, random_indices_x))
            for ind in random_indices:
                z, y, x = ind
                xmin = x - label_size if x >= label_size else 0
                xmax = x + label_size + 1 if x < shape[2] - label_size else shape[2]
                ymin = y - label_size if y >= label_size else 0
                ymax = y + label_size + 1 if y < shape[1] - label_size else shape[1]
                zmin = z - label_size if z >= label_size else 0
                zmax = z + label_size + 1 if z < shape[0] - label_size else shape[0] 
                for z_i in range(zmin,zmax):
                    for y_i in range(ymin,ymax):
                        for x_i in range(xmin,xmax):
                            if abs(z-z_i) + abs(y-y_i) + abs(x-x_i) <= label_size:
                                y_temp[z_i,y_i,x_i] = -0.5

            for coords in label_coords[j]:
                #mrcfile store image in zyx order
                x = coords[0]-1 if coords[0]>0 else 0
                y = coords[1]-1 if coords[1]>0 else 0
                z = coords[2]-1 if coords[2]>0 else 0
                
                
                #Gradient Probability distribution (Option 1)
                # p_step = 1/label_size
                # for i in range(label_size):
                #     j=i+1
                #     xmin = x - i if x >= j else 0
                #     xmax = x + j if x <= shape[2] -j else shape[2] -1
                #     ymin = y - i if y >= j else 0
                #     ymax = y + j if y <= shape[1] -j else shape[1] -1
                #     zmin = z - i if z >= j else 0
                #     zmax = z + j if z <= shape[0] -j else shape[0] -1
                #     y_temp[zmin:zmax,ymin:ymax,xmin:xmax] += p_step
                #     #y_temp[zmin:zmax,ymin:ymax,xmin:xmax] = 1
                # #y_temp[z,y,x] = 1
                
                # defining boundary for the current subtomogram
                xmin = x - label_size if x >= label_size else 0
                xmax = x + label_size + 1 if x < shape[2] - label_size else shape[2]
                ymin = y - label_size if y >= label_size else 0
                ymax = y + label_size + 1 if y < shape[1] - label_size else shape[1]
                zmin = z - label_size if z >= label_size else 0
                zmax = z + label_size + 1 if z < shape[0] - label_size else shape[0]
                
                #Option 2 (cubic labeling)
                #y_temp[zmin:zmax,ymin:ymax,xmin:xmax] = 1
                #labeling (psedo sphere)
                #radius_label = label_size
                #tuple_x, tuple_y, tuple_z = np.mgrid[0:xmax-xmin:1, 0:ymax-ymin:1, 0:zmax-zmin:1]
                #distance_label = np.sqrt((tuple_x - x)**2 + (tuple_y - y)**2 + (tuple_z - z)**2)
                #distance_label[distance_label > radius_label] = -1
                #distance_label[distance_label >=0] = 1
                

                #Option 3 (sphere labeling-- dimond shape labeling)
                for z_i in range(zmin,zmax):
                    for y_i in range(ymin,ymax):
                        for x_i in range(xmin,xmax):
                            if abs(z-z_i) + abs(y-y_i) + abs(x-x_i) <= label_size:
                                y_temp[z_i,y_i,x_i] = 1

            #data Augmentation (rotate volume but keep the missing wedge shape the same, so limited to 4 rotations)    
            for l in range(4):
                x_name = '{}/{}/{}_x_{}_{}.mrc'.format(data_dir, dirs_tomake[0], baseName, j, l)
                y_name = '{}/{}/{}_y_{}_{}.mrc'.format( data_dir, dirs_tomake[1], baseName, j, l)
                # original
                if l == 0:
                    rotated_x = s
                    rotated_y = y_temp
                # 180 degree on X-axis
                elif l ==1:
                    rotated_x = np.rot90(s, k=2, axes=(0,1))
                    rotated_y = np.rot90(y_temp, k=2, axes=(0,1))
                # 180 degree on Z-axis
                elif l ==2:
                    rotated_x = np.rot90(s, k=2, axes=(1,2))
                    rotated_y = np.rot90(y_temp, k=2, axes=(1,2))
                # 180 degree on Y-axis
                elif l ==3:
                    rotated_x = np.rot90(s, k=2, axes=(0,2))
                    rotated_y = np.rot90(y_temp, k=2, axes=(0,2))

                # save on disk
                with mrcfile.new(x_name, overwrite=True) as output_mrc:
                    output_mrc.set_data(normalize(rotated_x))
                with mrcfile.new(y_name, overwrite=True) as output_mrc:
                    output_mrc.set_data(rotated_y)

# split traning dataset into train and test            
def split_data(data_dir):    
    # hyper-parameters
    batch_size = 4
    ratio = 0.1
    
    #assigning classes
    all_path_x = os.listdir(data_dir+'/train_x')
    num_test = int(len(all_path_x) * ratio) 
    num_test = num_test - num_test%batch_size + batch_size
    all_path_y = [i.split('_x_')[0]+'_y_'+i.split('_x_')[1] for i in all_path_x ]

    #organizing based on distribution
    ind = np.random.permutation(len(all_path_x))[0:num_test]
    for i in ind:
        os.rename('{}/train_x/{}'.format(data_dir, all_path_x[i]), '{}/test_x/{}'.format(data_dir, all_path_x[i]) )
        os.rename('{}/train_y/{}'.format(data_dir, all_path_y[i]), '{}/test_y/{}'.format(data_dir, all_path_y[i]) )
            
if __name__ == "__main__":

    log_file = "Autopick/autopick.log"

    argv = sys.argv

    if not len(argv) == 2:
        log(None, "{} only requires one input file in JSON format".format(os.path.basename(__file__)), "error")
        sys.exit()
    else:
        try:
            train_params = SearchParam(argv[1])
        except Exception as err:
            log(None, err, "error")
            log(None, "There is formating issue with the input JSON file {}".format(argv[1]), "error")
            sys.exit()
    
    if not train_params.log_to_terminal:
        try:
            logger = logging.getLogger(__name__)
            handler = logging.FileHandler(filename=log_file, mode='a')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            formatter.datefmt = "%y-%m-%d %H:%M:%S"
            logger.handlers = [handler]
            logger.setLevel(logging.INFO)
        except:
            logger = None
    else:
        logger = None
    
    input_folder = train_params.input_folder_train
    tomoNameList = train_params.tomo_list
    result_dir= train_params.result_folder_train
    continue_from_model = train_params.continue_from_model
    label_size = train_params.label_size
    subtomo_num = train_params.subtomo_num
    cube_size = train_params.subtomo_box_size
    bin = train_params.coords_scale

    # # read params #
    # params = sys.argv    
    # input_folder = params[1]
    # tomoNameList = params[2].split(",")
    # result_dir= params[3]
    # continue_from_model = params[4]
    # label_size = int(params[5])
    # subtomo_num = int(params[6])
    # cube_size = int(params[7])
    # coords_scale = float(params[8])
    
    # # a binning factor to match coordinates with input tomograms (default 1)#
    # bin = coords_scale
    
    # # logger variable for GUI #
    # if len(params) == 10:
    #     log_file = params[9]
    #     logger = logging.getLogger(__name__)
    #     handler = logging.FileHandler(filename=log_file, mode='a')
    #     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    #     handler.setFormatter(formatter)
    #     formatter.datefmt = "%y-%m-%d %H:%M:%S"
    #     logger.handlers = [handler]
    #     logger.setLevel(logging.INFO)
    # else:
    #     logger = None
    # ###########################
    
    import time
    start_time = time.time()

    # set up folder for subtomograms #
    try:
        os.makedirs(result_dir)
    except:
        pass
    data_dir = "{}/data".format(result_dir)
    
    # read number of tomograms #
    num_tomo = len(tomoNameList)

    # if user used previous trained model file, then do not need to extract subtomograms #
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

    # handling tomograms, coordinates, and masks #
    tomoList = []
    coordsList = []
    maskList = []

    #for each tomo do
    for tomo in tomoNameList:
        # read tomogram volume file
        f = "{}/{}.mrc".format(input_folder,tomo)
        if os.path.exists(f):
            tomoList.append(f)
            mask_file = "{}/{}_mask{}".format(input_folder, tomo, ".mrc")
        else:
            tomoList.append("{}/{}.rec".format(input_folder,tomo))
            mask_file = "{}/{}_mask{}".format(input_folder, tomo, ".rec")
        
        # read mask file if any
        if os.path.exists(mask_file):
            maskList.append(mask_file)
        else:
            maskList.append(None)
        
        #check for 3 types of coordinates file
        fc1 = "{}/{}.mod".format(input_folder,tomo)
        fc2 = "{}/{}.pts".format(input_folder,tomo)
        fc3 = "{}/{}.coords".format(input_folder,tomo)
        if os.path.exists(fc1):
            coordsList.append(fc1)
        elif os.path.exists(fc2):
            coordsList.append(fc2)
        else:
            coordsList.append(fc3)

    # extraction
    log(logger, "Start subtomograms Extraction!")

    extract_subtomos_one(tomoList[0], maskList[0], coordsList[0], data_dir, label_size, subtomo_num, cube_size, logger=logger, bin=bin)
    
    for i, tomo in enumerate(tomoList[1:]):
        extract_subtomos_one(tomo, maskList[i+1], coordsList[i+1], data_dir, label_size, subtomo_num, cube_size, bin=bin, check_folder=False, logger=logger)
    
    # split data into train and test
    split_data(data_dir)

    # extraction done
    log(logger, "Extraction Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))