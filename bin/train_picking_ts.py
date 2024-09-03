#!/usr/bin/env python3
import logging, os, sys, math
import torch

import numpy as np
import matplotlib.pyplot as plt

from TomoNet.util.utils import string2int
from TomoNet.util.io import log
from TomoNet.util.searchParam import SearchParam 

if __name__ == "__main__":
    import time
    from TomoNet.models.network_picking import Net
    start_time = time.time()
    
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

    # Reading params from JSON file
    result_dir= train_params.result_folder_train
    data_dir = "{}/data".format(result_dir)

    continue_from_model = train_params.continue_from_model
    epoch_num = train_params.epoch_num
    gpuID = train_params.GPU_id
    lr = train_params.lr
    batch_size = train_params.batch_size
    steps_per_epoch = train_params.steps_per_epoch

    ncpus = 8
    acc_batches = batch_size//2

    input_folder = train_params.input_folder_train
    tomoNameList = train_params.tomo_list
    
    
    label_size = train_params.label_size
    subtomo_num = train_params.subtomo_num
    cube_size = train_params.subtomo_box_size
    bin = train_params.coords_scale

    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"]=gpuID

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
    
    
    network = Net(filter_base = 64, out_channels=1, logger=logger)

    # params = sys.argv
    
    # result_dir = sys.argv[1]
    # data_dir = "{}/data".format(result_dir)

    # continue_from_model = sys.argv[2]
    # epoch_num = int(sys.argv[3])
    # gpuID = sys.argv[4]
    
    # lr = float(sys.argv[5])
    # batch_size = int(sys.argv[6])
    # steps_per_epoch = int(sys.argv[7])
    
    # #############
    # ncpus = 12
    # acc_batches = batch_size//2

    # if len(params) == 9:
    #     log_file = params[8]
    #     logger = logging.getLogger(__name__)
    #     handler = logging.FileHandler(filename=log_file, mode='a')
    #     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    #     handler.setFormatter(formatter)
    #     formatter.datefmt = "%y-%m-%d %H:%M:%S"
    #     logger.handlers = [handler]
    #     logger.setLevel(logging.INFO)
    # else:
    #     logger = None

    if not os.path.exists(data_dir):
        log(logger, "data folder was not detected {}, make sure the data folder exist in the same folder as your pretained model."\
            .format(data_dir), "error")
        sys.exit()
    
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

    iter_epoch_num = 10
    iter = epoch_num//iter_epoch_num
    star_iter = 0
    
    if not continue_from_model == "None":
        try:
            tmp_int = string2int(continue_from_model.split(".h5")[0].split("_")[-1])
            if tmp_int == None:
                log(logger, "cannot read iteration number of pretrained model: {}, the model index will start from 1."\
                    .format(continue_from_model), level="warning")
            else:
                star_iter = tmp_int
                network.load(continue_from_model)
        except:
            log(logger, "error loading pretrained model: {}".format(continue_from_model), level="error")
            sys.exit()
        
    log(logger, "######## Start Training! Total epoch # is {} ########".format(epoch_num))
    for i in range(iter):
        tmp_time = time.time()
        #train based on init model and save new one as model_iter{num_iter}.h5
        metrics = network.train(data_dir, gpuID, 
                    learning_rate=lr, batch_size=batch_size,
                    epochs = iter_epoch_num, steps_per_epoch=steps_per_epoch, 
                    acc_batches=acc_batches, ncpus=ncpus, enable_progress_bar=True, precision=16) 
        
        metrics = metrics
        network.save('{}/model_iter_{:0>2d}.h5'.format(result_dir, star_iter + iter_epoch_num*(i+1)))
        try:
            plt.close()
        except:
            pass
        fig = plt.figure()
        train_loss = metrics['train_loss']
        val_loss = metrics['val_loss']
        # diff = iter_epoch_num*(i+1) - len(train_loss)
        # for _ in range(diff):
        #     train_loss.append(train_loss[-1])
        #     val_loss.append(val_loss[-1])
        # if diff > 0:
        #     log(logger, "early stoped at epoch {} ".format(star_iter + iter_epoch_num*(i+1)-diff))

        xpoints = np.arange(len(train_loss)) + 1
        ypoints1 = train_loss
        ypoints2 = val_loss
        plt.title('Train vs Val loss')
        plt.plot(xpoints, ypoints1, label='train_loss')
        plt.plot(xpoints, ypoints2, '-.', label='val_loss')

        plt.xticks(np.arange(1, len(train_loss) + 1, math.ceil(len(train_loss)/20)))
        plt.xlabel("epoch #")
        plt.ylabel("cross entropy loss")
        plt.yscale('log')
        plt.legend(loc='best')
        plt.title("Metrics")
        plt.draw()
        plt.pause(1)
        
        log(logger, "epoch {}: train loss {}, val loss {} --- {} mins --- ".format( star_iter + iter_epoch_num*(i+1), \
                round(metrics['train_loss'][-1],6), round(metrics['val_loss'][-1],6), round((time.time() - tmp_time)/60, 2)))

    plt.savefig('{}/metrics.png'.format(result_dir))
    log(logger, "Training Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))
