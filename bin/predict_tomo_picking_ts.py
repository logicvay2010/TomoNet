#!/usr/bin/env python3
import os, sys
import logging
import shutil
import subprocess
from TomoNet.util.utils import mkfolder
import mrcfile
import numpy as np
from TomoNet.preprocessing.cubes import normalize
from TomoNet.util.io import log

import scipy.cluster.hierarchy as hcluster

import time
import glob

def natural_keys(text, delimiter='_', index=-2):
        return int(text.split(delimiter)[index])

if __name__ == "__main__":

    start_time = time.time()

    from TomoNet.models.network_picking import Net
    #iter_count = 2
    params = sys.argv
    
    tomoName = sys.argv[1]
    result_dir = sys.argv[2]
    model_file = sys.argv[3]
    crop_size = int(sys.argv[4])
    cube_size = int(sys.argv[5])
    mask_file = sys.argv[6]
    repeat_unit = int(sys.argv[7])
    min_patch_size = int(sys.argv[8])
    y_label_size_predict = int(sys.argv[9])  
    tolerance = float(sys.argv[10])  

    #check if running using terminal or GUI 
    if len(params) == 12:
        log_file = params[11]
        logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
    else:
        logger = None

    save_patch_MODE = False
    # create result folder if not exist
    if not os.path.exists(result_dir):
        os.mkdir(result_dir)
    
    # make a folder storing intermediate subtomograms
    data_dir = "{}/data".format(result_dir)
    mkfolder(data_dir)

    # get the current tomogram base name and read the volume
    log(logger, "######## Predicting tomogram {} ########".format(tomoName))
    baseName = tomoName.split('/')[-1].split('.')[0]
    with mrcfile.open(tomoName) as mrcData:
        orig_data = mrcData.data.astype(np.float32)
    
    # check if mask file used
    mask_data = None
    if not (mask_file == "None" or mask_file == None):
        with mrcfile.open(mask_file) as m:
                mask_data = m.data
        log(logger, "######## Using mask file {} ########".format(mask_file))

    sp = np.array(orig_data.shape)
    #print(sp)

    margin_1 = (crop_size - cube_size)//2

    #########
    pad_width = (cube_size - (sp-2*margin_1)%cube_size)%cube_size//2
    #print(pad_width)
    pad_orig_data = np.pad(orig_data, ((pad_width[0], pad_width[0]),(pad_width[1], pad_width[1]),(pad_width[2], pad_width[2])), 'mean')
    orig_data = pad_orig_data
    sp = np.array(orig_data.shape)
    if not (mask_file == "None" or mask_file == None):
         mask_data = np.pad(mask_data, ((pad_width[0], pad_width[0]),(pad_width[1], pad_width[1]),(pad_width[2], pad_width[2])), 'constant')
    
    
    sidelen = (sp-2*margin_1)//cube_size

    crop_start = margin_1

    count = 0
    location_origins = "{}/location_origins.txt".format(result_dir)
    location_origins_list = []
    log(logger, "Calculated subtomos #:{}".format(sidelen[0]*sidelen[1]*sidelen[2]))
    #with open(location_origins, "w") as f:
    #voxel num for cubic labeling
    #voxel_num = crop_size**3

    #voxel num for psedo sphere labeling
    #voxel_num = crop_size**3/4

    #print(voxel_num/4)    
    #print(np.where(mask_data==0)[0])
    #print(len(np.where(mask_data==0)[0]))
    for i in range(sidelen[0]):
        for j in range(sidelen[1]):
            for k in range(sidelen[2]):

                z1,z2 = [i*cube_size, i*cube_size+crop_size]
                y1,y2 = [j*cube_size, j*cube_size+crop_size]
                x1,x2 = [k*cube_size, k*cube_size+crop_size]
                
                if not (mask_file == "None" or mask_file == None):
                        if np.sum(mask_data[z1:z2, y1:y2, x1:x2]) <= 0:
                            continue
                        
                # use a default number (voxel_num) as threshold for using a subtomogram        
                #elif len(np.where(mask_data[z1:z2, y1:y2, x1:x2]==0)[0]) <= voxel_num:
                #        continue
                
                cube = orig_data[z1:z2, y1:y2, x1:x2]

                cube = normalize(cube)
                #outdata.append(cube)
                x_name = "{}/x_{}.mrc".format(data_dir, count)
                with mrcfile.new(x_name, overwrite=True) as output_mrc:
                    output_mrc.set_data(cube)
                count+=1
                #f.write("{},{},{}\n".format(z1,y1,x1))
                location_origins_list.append([z1,y1,x1])
    
    #all_subtomo_list=np.array(outdata)
    
    log(logger, "Actual used subtomos #:{}".format(count))

    if count == 0:
         log(logger, "The crop size = box size + 8 which is {} and it is larger than the dimension of input tomogram: {}.".format(crop_size, np.flip(sp)))

    all_mrc_list = []
    

    for it in glob.glob("{}/*".format(data_dir)):
        #if "rlnImageName" in md.getLabels():
        all_mrc_list.append(it)

    network = Net(filter_base = 64, out_channels=1)

    network.load(model_file)

    pred_dir = "{}/predict".format(result_dir)
    #if not os.path.exists(pred_dir):
    mkfolder(pred_dir)
    
    log(logger,"trained_model={}".format(model_file))
    log(logger,"tolerance={}".format(tolerance))
    

    network.predict(all_mrc_list[:], pred_dir, iter_count=0, inverted=False, filter_strength=tolerance)

    
    log(logger,"Subtomogram Predict Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))
    start_time = time.time()
    log(logger,"###### Start getting particles locations ######")

    all_mrc_pred_list = []
    for it in glob.glob("{}/*".format(pred_dir)):
        if it.endswith(".mrc"):
            all_mrc_pred_list.append(it)

    all_mrc_pred_list.sort(key=natural_keys)
    
    global_map = np.ones(sp, dtype=np.float32)

    thresh = 1.5

    #create folder for current tomogram
    tomoName_final = "{}_final".format(baseName)
    tomo_current_dir = "{}/{}".format(result_dir, tomoName_final)
    #if not os.path.exists(pred_dir):
    mkfolder(tomo_current_dir)

    particle_list = []
    mini_cube_size = (y_label_size_predict*2)+1
    # for cube labeling
    cube_activate_num = mini_cube_size**3*3
    # for psedo sphere labeling (pyramid)
    cube_activate_num = mini_cube_size**3*3/4
    for i in range(len(all_mrc_pred_list)):
        pred = all_mrc_pred_list[i]

        ind = int(pred.split("_")[-2])
        z_crop, y_crop, x_crop = location_origins_list[ind]

        with mrcfile.open(pred) as mrc:
            y_map = mrc.data[0]
        #print(y_map.shape)
        
        points = np.argwhere(y_map > 0.1)
        #print(points)
        if points.shape[0] > cube_activate_num:
            global_map[z_crop:z_crop+crop_size, y_crop:y_crop+crop_size, x_crop:x_crop+crop_size] = 63*y_map+1
            clusters = hcluster.fclusterdata(points, thresh, criterion="distance")
            
            for i in range(len(set(clusters))):
                z,y,x = np.mean(points[np.argwhere(clusters == i+1)], axis=0)[0]
                if x >=margin_1 and x <=crop_size-margin_1 and y >=margin_1 and y <=crop_size-margin_1 and z >=margin_1 and z <=crop_size-margin_1:
                    #w.write("{} {} {}\n".format(x+x_crop,y+y_crop,z+z_crop))
                    particle_list.append([x+x_crop, y+y_crop, z+z_crop])
        else:
            pass
        
    particle_list = np.array(particle_list)
    particle_list_rmdup = []
    particle_dup_ratio = 0.75
    log(logger, "Particle # before remove duplicates:{}".format(particle_list.shape[0]))
    if particle_list.shape[0] > 1:
        
        clusters = hcluster.fclusterdata(particle_list, repeat_unit*particle_dup_ratio, criterion="distance")
        log(logger, "Particle # after remove duplicates:{}".format(len(set(clusters))))
        for i in range(len(set(clusters))):
                x,y,z = np.mean(particle_list[np.argwhere(clusters == i+1)], axis=0)[0]
                #if x >=margin_1 and x <=crop_size-margin_1 and y >=margin_1 and y <=crop_size-margin_1 and z >=margin_1 and z <=crop_size-margin_1:
                    #w.write("{} {} {}\n".format(x+x_crop,y+y_crop,z+z_crop))
                particle_list_rmdup.append([x,y,z])
                #w.write("{} {} {}\n".format(x,y,z))
    min_num_c = 0
    patch_c = 0
    patch_dis_ratio = 1.25
    particle_list_rmdup = np.array(particle_list_rmdup)
    if particle_list_rmdup.shape[0] > 1:
        #with open("{}/{}_full.pts".format(result_dir, baseName),'w') as w:
        with open("{}/{}/{}.pts".format(result_dir, tomoName_final, baseName),'w') as w:
            clusters = hcluster.fclusterdata(particle_list_rmdup, repeat_unit*patch_dis_ratio, criterion="distance")
            log(logger, "Detected patch #:{}".format(len(set(clusters))))
            for i in range(len(set(clusters))):
                    neighbors = np.squeeze(particle_list_rmdup[np.argwhere(clusters == i+1)], axis=1)
                    if len(neighbors) >= min_patch_size:
                        
                        with open("{}/{}/{}_patch_{}.pts".format(result_dir, tomoName_final, baseName, patch_c+1),'w') as wp:
                            #min_num_c+=len(neighbors)
                            for n in neighbors:
                                #w.write("{} {} {}\n".format(n[0],n[1],n[2]))
                                
                                #w.write("{} {} {}\n".format(n[0]+1,n[1]+1,n[2]+1))
                                
                                if n[0]+1-pad_width[2] > 0 and n[1]+1-pad_width[1] > 0 and n[2]+1-pad_width[0] > 0:
                                    #if mask_data[int(n[0])][int(n[1])][int(n[2])] > 0:
                                    w.write("{} {} {} {}\n".format(patch_c+1, n[0]+1-pad_width[2], n[1]+1-pad_width[1], n[2]+1-pad_width[0]))
                                    wp.write("{} {} {}\n".format(n[0]+1-pad_width[2], n[1]+1-pad_width[1], n[2]+1-pad_width[0]))
                                    min_num_c+=1
                                #if n[0]+1>0 and n[1]+1> 0 and n[2]+1> 0:
                                #    
                                #    w.write("{} {} {}\n".format(n[0]+1,n[1]+1,n[2]+1))
                        prefix_temp = "{}_patch_{}".format(baseName, patch_c+1)
                        if save_patch_MODE:
                            cmd_pts2mod = "cd {}/{}; point2model {}.pts {}.mod -sc -sp 3; rm {}.pts".format(result_dir, tomoName_final, prefix_temp, prefix_temp, prefix_temp)
                            subprocess.check_output(cmd_pts2mod, shell=True)
                        else:
                            cmd_pts2mod = "cd {}/{}; rm {}.pts".format(result_dir, tomoName_final, prefix_temp)
                            subprocess.check_output(cmd_pts2mod, shell=True)
                        patch_c+=1
                    #x,y,z = np.mean(particle_list[np.argwhere(clusters == i+1)], axis=0)[0]
                    #if x >=margin_1 and x <=crop_size-margin_1 and y >=margin_1 and y <=crop_size-margin_1 and z >=margin_1 and z <=crop_size-margin_1:
                        #w.write("{} {} {}\n".format(x+x_crop,y+y_crop,z+z_crop))
                    #particle_list_rmdup.append([x,y,z])
                    #w.write("{} {} {}\n".format(x,y,z))
    log(logger, "saved patches #:{}".format(patch_c))
    log(logger, "Particle # after remove small patches:{}".format(min_num_c))
    
    ####### save global map prediction #############
    #global_map_filename = "{}/{}/predict.mrc".format(result_dir, tomoName_final)
    #with mrcfile.new(global_map_filename, overwrite=True) as output_mrc:
    #   output_mrc.set_data(global_map)

    cmd_linkMrc = "cd {}/{}; ln -s {} ./".format(result_dir, tomoName_final, tomoName)
    subprocess.check_output(cmd_linkMrc, shell=True)
    #local center cluster
    #output will be a list of coordinates
    
    if min_num_c > 0:
        mod_file = "{}/{}/{}.mod".format(result_dir, tomoName_final, baseName)
        pts_file = "{}/{}/{}.pts".format(result_dir, tomoName_final, baseName)
        cmd_pts2mod = "point2model {} {} -sc -sp 3".format(pts_file, mod_file)
        subprocess.run(cmd_pts2mod, shell=True, encoding="utf-8")

    #rm predict folder
    if os.path.exists(pred_dir):
        shutil.rmtree(pred_dir)
    if os.path.exists("{}~".format(pred_dir)):
        shutil.rmtree("{}~".format(pred_dir))
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    log(logger, "Particles saved for {} --- {} mins ---".format(baseName, round((time.time() - start_time)/60, 2)))
    
