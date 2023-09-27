#!/usr/bin/env python3
import logging
from IsoNet.preprocessing.prepare import get_cubes_list,get_noise_level, prepare_first_iter
from IsoNet.util.dict2attr import save_args_json,load_args_from_json
import numpy as np
import os
import sys
import math
from IsoNet.util.metadata import MetaData
from IsoNet.util.utils import string2int
from IsoNet.util.io import log

import matplotlib.pyplot as plt
def run_whole(args):
    '''
    Consume all the argument parameters
    '''
    md = MetaData()
    md.read(args.subtomo_star)
    #*******set fixed parameters*******
    args.crop_size = md._data[0].rlnCropSize
    args.cube_size = md._data[0].rlnCubeSize
    args.predict_cropsize = args.crop_size
    args.residual = True
    #*******calculate parameters********
    if args.gpuID is None:
        args.gpuID = '0,1,2,3'
    else:
        args.gpuID = str(args.gpuID)
    if args.data_dir is None:
        args.data_dir = args.result_dir + '/data'
    if args.iterations is None:
        args.iterations = 30
    args.ngpus = len(list(set(args.gpuID.split(','))))
    if args.result_dir is None:
        args.result_dir = 'results'
    if args.batch_size is None:
        args.batch_size = max(4, 2 * args.ngpus)
    args.predict_batch_size = args.batch_size
    # if args.filter_base is None:
    #     args.filter_base = 64
    #     # if md._data[0].rlnPixelSize >15:
    #     #     args.filter_base = 32
    #     # else:
    #     #     args.filter_base = 64
    if args.steps_per_epoch is None:
        if args.select_subtomo_number is None:
            args.steps_per_epoch = min(int(len(md) * 8/args.batch_size) , 200)
        else:
            args.steps_per_epoch = min(int(int(args.select_subtomo_number) * 6/args.batch_size) , 200)
    if args.learning_rate is None:
        args.learning_rate = 0.0004
    #if args.noise_level is None:
    #    args.noise_level = (0.05,0.10,0.15,0.20)
    #if args.noise_start_iter is None:
    #    args.noise_start_iter = (11,16,21,26)
    if args.noise_mode is None:
        args.noise_mode = 'noFilter'
    if args.noise_dir is None:
        args.noise_dir = args.result_dir +'/training_noise'
    if args.log_level is None:
        args.log_level = "info"

    if len(md) <=0:
        logging.error("Subtomo list is empty!")
        sys.exit(0)
    args.all_mrc_list = []
    for i,it in enumerate(md):
        if "rlnImageName" in md.getLabels():
            args.all_mrc_list.append(it.rlnImageName)
    return args

if __name__ == "__main__":
    import time
    start_time = time.time()

    from IsoNet.models.network_picking import Net
    
    network = Net(filter_base = 64, out_channels=1)

    params = sys.argv
    
    result_dir = sys.argv[1]
    data_dir = "{}/data".format(result_dir)

    continue_from_model = sys.argv[2]
    epoch_num = int(sys.argv[3])
    gpuID = sys.argv[4]
    
    lr = float(sys.argv[5])
    batch_size = int(sys.argv[6])
    steps_per_epoch = int(sys.argv[7])
    
    #############
    ncpus = 12
    acc_batches = batch_size//2

    #conti = int(sys.argv[4])

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
    '''
    subtomo_star = "subtomo.star"
    md = MetaData()
    md.read(subtomo_star)
    all_mrc_list = []
    for i,it in enumerate(md):
        if "rlnImageName" in md.getLabels():
            all_mrc_list.append(it.rlnImageName)
    

    if conti == 1:
        current_iter = int(sys.argv[5])
    else:
        current_iter = 1
    #num_iter = 1


    #model_file = "{}/model_iter{:0>2d}.h5".format(result_dir, num_iter-1)

    if conti == 0:
        mkfolder(result_dir) 
        #current_iter = 1
        model_file = "{}/model_iter{:0>2d}.h5".format(result_dir, current_iter-1)
        network.save(model_file)
    '''
    #from IsoNet.preprocessing.img_processing import normalize
    # inp: list 0f (mrc_dir, index * rotation times)

    #if ncpus > 1:
        #func = partial(get_cubes, settings=settings)
        #with Pool(settings.ncpus) as p:
        #    p.map(func,inp)
    #else:
        #for i in inp:
        #    logging.info("{}".format(i))
        #    get_cubes(i, settings)

    
    '''
    all_path_x = os.listdir(data_dir+'/train_x')
    num_test = int(len(all_path_x) * 0.1) 
    num_test = num_test - num_test%batch_size + batch_size
    
    all_path_y = ['y_'+i.split('_')[1] for i in all_path_x ]
    ind = np.random.permutation(len(all_path_x))[0:num_test]
    for i in ind:
        os.rename('{}/train_x/{}'.format(data_dir, all_path_x[i]), '{}/test_x/{}'.format(data_dir, all_path_x[i]) )
        os.rename('{}/train_y/{}'.format(data_dir, all_path_y[i]), '{}/test_y/{}'.format(data_dir, all_path_y[i]) )
    '''
    #epoch_num = 30

    '''
    model_files = glob.glob("{}/*.h5".format(result_dir))
    if len(model_files) == 0:
        current_iter = 1
        model_file = "{}/model_iter_{:0>2d}.h5".format(result_dir, 0)
        network.save(model_file)
    else:
        iter_nums = [int(os.path.basename(x).split(".")[0].split("_")[-1]) for x in model_files]
        current_iter = max(iter_nums) + 1
    '''
    iter_epoch_num = 10
    iter = epoch_num//iter_epoch_num
    star_iter = 0
    
    if not continue_from_model == "None":
        #model_file = "{}/model_iter_{:0>2d}.h5".format(result_dir, iter_count-1)
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
        metrics = network.train(data_dir, gpuID, 
                                learning_rate=lr, batch_size=batch_size,
                                epochs = iter_epoch_num, steps_per_epoch=steps_per_epoch, acc_batches=acc_batches, ncpus=ncpus, enable_progress_bar=True, precision=16) #train based on init model and save new one as model_iter{num_iter}.h5
                # except KeyboardInterrupt as exception: 
                #     sys.exit("Keyboard interrupt")
        metrics = metrics
        network.save('{}/model_iter_{:0>2d}.h5'.format(result_dir, star_iter + iter_epoch_num*(i+1)))
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
        
        #print(np.arange(len(train_loss), math.ceil(len(train_loss)/20)) + 1)
        #plt.xticks(np.arange(1+star_iter, len(train_loss) + 1 + star_iter, math.ceil(len(train_loss)/20)))
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
        
        #print('{}/model_iter_{:0>2d}.h5'.format(result_dir, iter_epoch_num*(i+1)))

        #if (i+1)%10 == 0:
    
    #network.save('{}/model_iter_{:0>2d}.h5'.format(result_dir, epoch_num))
    #plt.show()
    plt.savefig('{}/metrics.png'.format(result_dir))
    log(logger, "Training Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))
