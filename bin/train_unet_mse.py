#!/usr/bin/env python3
import logging
import os
import sys
import math

import numpy as np
import matplotlib.pyplot as plt

from TomoNet.util.utils import string2int
from TomoNet.util.io import log

if __name__ == "__main__":
    import time
    from TomoNet.models.network_isonet_mse import Net
    start_time = time.time()

    network = Net(filter_base = 64, out_channels=1)

    params = sys.argv
    
    subtomos_dir = sys.argv[1]
    

    #continue_from_model = sys.argv[2]
    epoch_num = int(sys.argv[2])
    gpuID = sys.argv[3]
    
    lr = float(sys.argv[4])
    batch_size = int(sys.argv[5])
    steps_per_epoch = int(sys.argv[6])
    sign = sys.argv[7]

    data_dir = "{}/{}".format(subtomos_dir, sign)
    
    #############
    ncpus = 8
    acc_batches = batch_size//2

    if len(params) == 9:
        log_file = params[8]
        logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
    else:
        logger = None

    if not os.path.exists(data_dir):
        log(logger, "data folder was not detected {}, make sure the data folder exist in the same folder as your pretained model."\
            .format(data_dir), "error")
        sys.exit()

    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"]=gpuID
    
    iter_epoch_num = 10
    iter = epoch_num//iter_epoch_num
    star_iter = 0
         
    log(logger, "######## Start Training! Total epoch # is {} ########".format(epoch_num))
    for i in range(iter):
        tmp_time = time.time()
        #train based on init model and save new one as model_iter{num_iter}.h5
        metrics = network.train(data_dir, gpuID, 
                    learning_rate=lr, batch_size=batch_size,
                    epochs = iter_epoch_num, steps_per_epoch=steps_per_epoch, 
                    acc_batches=acc_batches, ncpus=ncpus, enable_progress_bar=True, precision=16) 
        
        metrics = metrics
        network.save('{}/{}_model_iter_{:0>2d}.h5'.format(subtomos_dir, sign, star_iter + iter_epoch_num*(i+1)))
        try:
            plt.close()
        except:
            pass
        fig = plt.figure()
        train_loss = metrics['train_loss']
        val_loss = metrics['val_loss']
        diff = iter_epoch_num*(i+1) - len(train_loss)
        for _ in range(diff):
            train_loss.append(train_loss[-1])
            val_loss.append(val_loss[-1])
        if diff > 0:
            log(logger, "early stoped at epoch {} ".format(star_iter + iter_epoch_num*(i+1)-diff))

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
        
        log(logger, "--- {} mins ---   epoch {}: train loss {}, val loss {} ".format(round((time.time() - tmp_time)/60, 2), star_iter + iter_epoch_num*(i+1), \
                round(metrics['train_loss'][-1],6), round(metrics['val_loss'][-1],6)))

    plt.savefig('{}/{}_metrics.png'.format(subtomos_dir, sign))
    log(logger, "Training Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))
