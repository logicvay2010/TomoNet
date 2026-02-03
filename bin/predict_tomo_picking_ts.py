#!/usr/bin/env python3
import os, sys, logging, shutil, subprocess, time, math
import glob
import mrcfile
import torch
import numpy as np
import scipy.cluster.hierarchy as hcluster

from TomoNet.util.io import log
from TomoNet.util.utils import mkfolder
from TomoNet.preprocessing.cubes import normalize
from TomoNet.util.searchParam import SearchParam 

# used for extract sort keys
def natural_keys(text, delimiter='_', index=-2):
    return int(text.split(delimiter)[index])

if __name__ == "__main__":

    start_time = time.time()

    from TomoNet.models.network_picking import Net
    
    log_file = "Autopick/autopick.log"

    argv = sys.argv
    
    if not len(argv) == 2:
        log(None, "{} only requires one input file in JSON format".format(os.path.basename(__file__)), "error")
        sys.exit()
    else:
        try:
            predict_params = SearchParam(argv[1])
        except Exception as err:
            log(None, err, "error")
            log(None, "There is formating issue with the input JSON file {}".format(argv[1]), "error")
            sys.exit()

    if not predict_params.log_to_terminal:
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
    # Reading params from JSON file
    tomoName = predict_params.current_tomo
    result_dir = predict_params.predict_result_path
    model_file = predict_params.input_model
    crop_size = predict_params.box_size_predict
    cube_size = predict_params.box_size_predict - predict_params.margin
    mask_file = predict_params.current_mask
    repeat_unit = predict_params.unit_size_predict
    min_patch_size = predict_params.min_patch_size_predict
    y_label_size_predict = predict_params.y_label_size_predict
    tolerance = predict_params.tolerance
    save_seg_map = predict_params.save_seg_map
    gpuID = predict_params.predict_gpuID

    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"]=gpuID

    if isinstance(gpuID, str):
        gpuID_list = list(map(int, gpuID.split(',')))
        
    gpu_device_count = torch.cuda.device_count()
    if gpu_device_count == 0:
        log(logger, "No available GPU detected, based on the requested GPU ID {}.".format(gpuID), "error")
        sys.exit()
    elif len(gpuID_list) > gpu_device_count:
        log(logger, "No enough available GPUs ({} detected), based on the requested GPU ID {}. Available GPUs are:".format(gpu_device_count, gpuID), "error")
        for i in range(gpu_device_count):
            log(logger, torch.cuda.get_device_properties(i).name)
        sys.exit()
    else:
        log(logger, "Run training on {} GPU(s):".format(len(gpuID_list)))
        for i in range(len(gpuID_list)):
            log(logger, torch.cuda.get_device_properties(i).name)

    # # read parameters
    # params = sys.argv
    # tomoName = sys.argv[1]
    # result_dir = sys.argv[2]
    # model_file = sys.argv[3]
    # crop_size = int(sys.argv[4])
    # cube_size = int(sys.argv[5])
    # mask_file = sys.argv[6]
    # repeat_unit = int(sys.argv[7])
    # min_patch_size = int(sys.argv[8])
    # y_label_size_predict = int(sys.argv[9])  
    # tolerance = float(sys.argv[10])  
    # save_seg_map = int(sys.argv[11])
    
    # #check whether running using terminal (12) or GUI (13) 
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
    #     logger = None

    # set visiable gpus


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
        orig_data = mrcData.data.astype(np.float32)
    
    # check if mask file used
    mask_data = None
    if not (mask_file == "None" or mask_file == None):
        with mrcfile.open(mask_file) as m:
                mask_data = m.data
        log(logger, "######## Using mask file {} ########".format(mask_file))

    sp = np.array(orig_data.shape)

    # margin related to overlaping region (pad_width) when extracting subtomograms
    #margin_1 = (crop_size - cube_size)//2
    #pad_width = (cube_size - (sp-2*margin_1)%cube_size)%cube_size//2
    
    # padded 3D volume data
    #pad_orig_data = np.pad(orig_data, ((pad_width[0], pad_width[0]),(pad_width[1], pad_width[1]),(pad_width[2], pad_width[2])), 'mean')
    #orig_data = pad_orig_data
    #sp = np.array(orig_data.shape)
    
    # check if using mask
    #if not (mask_file == "None" or mask_file == None):
    #     mask_data = np.pad(mask_data, ((pad_width[0], pad_width[0]),(pad_width[1], pad_width[1]),(pad_width[2], pad_width[2])), 'constant')
    
    # number of cubes (x, y, z axis)
    #sidelen = (sp-2*margin_1)//cube_size
    sidelen = (sp//cube_size) + 1

    # so, if no cube was detected, stop here 
    if sp[0]< cube_size or sp[1]< cube_size or sp[2]< cube_size:
        log(logger, "The crop size {} is larger than the dimension of input tomogram: {}.".format(crop_size, np.flip(sp)), level="error")
        sys.exit()

    # crop starting coords (origin)
    crop_start = 0

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

                if i==sidelen[0] - 1:
                    z1,z2 = [sp[0]-crop_size, sp[0]]
                if j==sidelen[1] - 1:
                    y1,y2 = [sp[1]-crop_size, sp[1]]
                if k==sidelen[2] - 1:
                    x1,x2 = [sp[2]-crop_size, sp[2]]
                
                # if the current cube does not overlaping with the mask, skip it (this helps with exclude empty area to avoid false positive)
                if not (mask_file == "None" or mask_file == None):
                        if np.sum(mask_data[z1:z2, y1:y2, x1:x2]) <= 0:
                            continue
                
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
        log(logger, "The crop size {} is and it is larger than the dimension of input tomogram: {}.".format(crop_size, np.flip(sp)), level="error")
        sys.exit()

    # read all cube volume into memory
    all_mrc_list = []
    for it in glob.glob("{}/*".format(data_dir)):
        all_mrc_list.append(it)

    # load trained neural network
    network = Net(filter_base = 64, out_channels=1)
    network.load(model_file)

    # network inference for all the cubes
    pred_dir = "{}/predict".format(result_dir)
    mkfolder(pred_dir)
    log(logger,"trained_model={}".format(model_file))
    log(logger,"tolerance={}".format(tolerance))
    network.predict(all_mrc_list[:], pred_dir, iter_count=0, inverted=False, filter_strength=tolerance, logger=logger)
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

    # threshold for hierarchy cluster (min distance between two clusters)
    thresh = 1.5

    # create result folder for current tomogram ( particle locations )
    tomoName_final = "{}_final".format(baseName)
    tomo_current_dir = "{}/{}".format(result_dir, tomoName_final)
    mkfolder(tomo_current_dir)

    # for particle list 
    particle_list = []
    # calculate the size of y labeling for each particle 
    mini_cube_size = (y_label_size_predict*2)+1
    
    # in predicted seg map, pixel near particles will be activated. Use a minimum activated pixel # to exclude noise. 
    #(Assume a normal cube containing particles should have certain amount of activated pixels, otherwise just false positives) 
    # Option 1: for cubic labeling 
    #cube_activate_num = mini_cube_size**3*3
    # Option 2: for psedo sphere labeling (pyramid)
    #cube_activate_num = mini_cube_size**3*3/4
    cube_activate_num = y_label_size_predict**3*math.pi*4/3 *(0.5)
    log(logger, "cube_activate_num: {}".format(cube_activate_num))
    
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
        points = np.argwhere(y_map > 0.1)
        # filter based on the # of activated pixels
        if points.shape[0] > cube_activate_num:
            
            # connected voxels will be clustered into the same particle (a block of voxels)
            global_map[z_crop:z_crop+crop_size, y_crop:y_crop+crop_size, x_crop:x_crop+crop_size] = 63*y_map+1
            clusters = hcluster.fclusterdata(points, thresh, criterion="distance")
            
            # for each block (particle), use the cluster center as the particle center. And this particle will be saved
            for i in range(len(set(clusters))):
                if points[np.argwhere(clusters == i+1)].shape[0] >= cube_activate_num:
                    z,y,x = np.mean(points[np.argwhere(clusters == i+1)], axis=0)[0]
                    #if x >=margin_1 and x <=crop_size-margin_1 and y >=margin_1 and y <=crop_size-margin_1 and z >=margin_1 and z <=crop_size-margin_1:
                    #    particle_list.append([x+x_crop, y+y_crop, z+z_crop])
                    particle_list.append([x+x_crop, y+y_crop, z+z_crop])
    # So far, the raw paricles info is extracted from seg maps, but need to clean a little bit
    
    # First, remove duplication
    particle_list = np.array(particle_list)
    particle_list_rmdup = []
    # particles within < unit distance * particle_dup_ratio > pixels will be considered as duplicates 
    particle_dup_ratio = 0.75
    log(logger, "Particle # before remove duplicates:{}".format(particle_list.shape[0]))
    
    if particle_list.shape[0] > 1:
        # again use cluster method to achieve particle removal
        clusters = hcluster.fclusterdata(particle_list, repeat_unit*particle_dup_ratio, criterion="distance")
        log(logger, "Particle # after remove duplicates:{}".format(len(set(clusters))))
        
        for i in range(len(set(clusters))):
                x,y,z = np.mean(particle_list[np.argwhere(clusters == i+1)], axis=0)[0]
                particle_list_rmdup.append([x,y,z])
    
    # Second, remove small lattices, which is likely to be false positive (for lattice-like particles)
    min_num_c = 0
    # patch count
    patch_c = 0
    # unit_distance * patch_dis_ratio is the min distance for clusters when using hcluster.fclusterdata
    patch_dis_ratio = 1.25
    particle_list_rmdup = np.array(particle_list_rmdup)
    if particle_list_rmdup.shape[0] > 1:
        # global result
        with open("{}/{}/{}.pts".format(result_dir, tomoName_final, baseName),'w') as w:
            # again, use hcluster (distance based) to perform clustering
            clusters = hcluster.fclusterdata(particle_list_rmdup, repeat_unit*patch_dis_ratio, criterion="distance")
            log(logger, "Detected patch #:{}".format(len(set(clusters))))
            # check each particle cluster (i.e., lattice)
            for i in range(len(set(clusters))):
                neighbors = np.squeeze(particle_list_rmdup[np.argwhere(clusters == i+1)], axis=1)
                if len(neighbors) >= min_patch_size:
                    # patch result
                    with open("{}/{}/{}_patch_{}.pts".format(result_dir, tomoName_final, baseName, patch_c+1),'w') as wp:
                        for n in neighbors:
                            # make sure all particles are inside the boundary                          
                            # if n[0]+1-pad_width[2] > 0 and n[1]+1-pad_width[1] > 0 and n[2]+1-pad_width[0] > 0:
                            #     w.write("{} {} {} {}\n".format(patch_c+1, n[0]+1-pad_width[2], n[1]+1-pad_width[1], n[2]+1-pad_width[0]))
                            #     wp.write("{} {} {}\n".format(n[0]+1-pad_width[2], n[1]+1-pad_width[1], n[2]+1-pad_width[0]))
                            #     min_num_c+=1
                            w.write("{} {} {} {}\n".format(patch_c+1, n[0]+1, n[1]+1, n[2]+1))
                            wp.write("{} {} {}\n".format(n[0]+1, n[1]+1, n[2]+1))
                            min_num_c+=1
                    prefix_temp = "{}_patch_{}".format(baseName, patch_c+1)
                    # debug using only
                    if save_patch_MODE:
                        cmd_pts2mod = "cd {}/{}; point2model {}.pts {}.mod -sc -sp 3; rm {}.pts".format(result_dir, tomoName_final, prefix_temp, prefix_temp, prefix_temp)
                        subprocess.check_output(cmd_pts2mod, shell=True)
                    else:
                        cmd_pts2mod = "cd {}/{}; rm {}.pts".format(result_dir, tomoName_final, prefix_temp)
                        subprocess.check_output(cmd_pts2mod, shell=True)
                    patch_c+=1
    
    log(logger, "saved patches #:{}".format(patch_c))
    log(logger, "Particle # after remove small patches:{}".format(min_num_c))
    
    ####### save global map prediction seg map #############
    if save_seg_map == 1:
        global_map_filename = "{}/{}/predict.mrc".format(result_dir, tomoName_final)
        with mrcfile.new(global_map_filename, overwrite=True) as output_mrc:
            output_mrc.set_data(global_map)

    # create a link of mrc file #
    
    cmd_linkMrc = "cd {}/{}; ln -s {} ./".format(result_dir, tomoName_final, tomoName)
    #cmd_linkMrc = "cd {}/{}; ln -s {}/{} ./".format(result_dir, tomoName_final, os.getcwd(), tomoName)
    subprocess.check_output(cmd_linkMrc, shell=True)
    
    # check if particle number > 0 (valid outcomes), if so generate a mod file presenting all particles
    if min_num_c > 0:
        mod_file = "{}/{}/{}.mod".format(result_dir, tomoName_final, baseName)
        pts_file = "{}/{}/{}.pts".format(result_dir, tomoName_final, baseName)
        cmd_pts2mod = "point2model {} {} -sc -sp 3".format(pts_file, mod_file)
        subprocess.run(cmd_pts2mod, shell=True, encoding="utf-8")

    # clean up intermediate results
    if os.path.exists(pred_dir):
        shutil.rmtree(pred_dir)
    if os.path.exists("{}~".format(pred_dir)):
        shutil.rmtree("{}~".format(pred_dir))
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    log(logger, "Particles saved for {} --- {} mins ---".format(baseName, round((time.time() - start_time)/60, 2)))
    
