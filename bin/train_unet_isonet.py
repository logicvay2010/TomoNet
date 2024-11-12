#!/usr/bin/env python3
import os, sys, re, logging, shutil
import torch

from TomoNet.util.io import log, mkfolder
from TomoNet.util.dict2attr import save_args_json
from TomoNet.util.searchParam import SearchParam 
from TomoNet.util.metadata import MetaData
from TomoNet.preprocessing.prepare import prepare_first_iter, get_noise_level, get_cubes_list
from TomoNet.models.network_isonet import Net

def check_gpu(gpu_ID, logger):
    try:
        detected_gpu_num = torch.cuda.device_count()
        if detected_gpu_num == 0:
            log(logger, "GPU is not detected!")
            return 0
        elif detected_gpu_num < len(gpu_ID):
            log(logger, "Ask for {} GPUs, but only detected {} GPUs!".format(len(gpu_ID), detected_gpu_num))
            return 0
    except:
        log(logger, "GPU is not accessible by pyTorch. Please make that torch.cuda.device_count() has GPU # > 0 !")
        return 0
    return 1

def check_params(args):
    md = MetaData()
    md.read(args.train_subtomos_star)
    #*******set fixed parameters*******
    args.crop_size = md._data[0].rlnCropSize
    args.cube_size = md._data[0].rlnCubeSize
    args.predict_cropsize = args.crop_size
    args.residual = True
    args.train_pretrained_model = None

    #*******calculate parameters********

    args.data_dir = "{}/data".format(args.train_result_folder)

    angle_1, angle_2 = args.tilt_range

    args.missingAngle = [90 + angle_1, 90 - angle_2]
    # if not hasattr(args, "missingAngle"):
    #     args.missingAngle = [30,30]

    if args.train_batch_size is None:
        args.train_batch_size = max(4, 2 * args.ngpus)
    
    args.predict_batch_size = args.train_batch_size

    if args.train_steps_per_epoch is None:
        args.train_steps_per_epoch = min(int(len(md) * 8 / args.train_batch_size) , 200)

    args.noise_dir = "{}/training_noise".format(args.train_result_folder)

    try:
        args.noise_level = [float(x) for x in args.noise_level.split(",")]
    except Exception as err:
            log(logger, err, "error")
            log(logger, "There is formating issue with noise level", "error")
            sys.exit()
    
    try:
        args.noise_start_iter = [int(x) for x in args.noise_start_iter.split(",")]
    except Exception as err:
            log(logger, err, "error")
            log(logger, "There is formating issue with noise start iterations", "error")
            sys.exit()

    if len(md) <=0:
        log(logger, "{} list is empty!".format(args.train_subtomos_star), "error")
        sys.exit()

    args.all_mrc_list = []
    
    for it in md:
        if "rlnImageName" in md.getLabels():
            args.all_mrc_list.append(it.rlnImageName)
    
    if not hasattr(args, "remove_intermediate"):
        args.remove_intermediate = False
    
    if not hasattr(args, "low_mem"):
        args.low_mem = False
    
    try:
        args.gpu_list = [int(x) for x in re.split(',| ', args.train_gpuID)]
    except Exception as err:
        args.gpu_list = [0,1,2,3]
    return args

if __name__ == "__main__":

    log_file = "IsoNet/isonet.log"
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

    argv = sys.argv

    if not len(argv) == 2:
        log(logger, "{} only requires one input file in JSON format".format(os.path.basename(__file__)), "error")
        sys.exit()
    else:
        try:
            train_params = SearchParam(argv[1])
            #log(logger, vars(train_params), "info")
            #params = vars(train_params)
        except Exception as err:
            log(logger, err, "error")
            log(logger, "There is formating issue with the input JSON file {}".format(argv[1]), "error")
            sys.exit()
    
    train_params.logger = logger

    log(logger, "\n######Isonet Starts Traning######\n")

    if train_params.continue_from_iter is not None:
        log(logger, '\n######Isonet Continues Refining######\n')
        args_continue = SearchParam(train_params.continue_from_iter)
        for item in args_continue.__dict__:
            if args_continue.__dict__[item] is not None and (train_params.__dict__ is None or not hasattr(train_params, item)):
                train_params.__dict__[item] = args_continue.__dict__[item]

    #environment
    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"]=train_params.train_gpuID
    #os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"

    gpu_ID = re.split(',| ', train_params.train_gpuID)

    train_params.ngpus = len(gpu_ID)

    if not check_gpu(gpu_ID, logger):
        sys.exit()
        
    try:
        train_params = check_params(train_params)
    except Exception as err:
        log(logger, err, "error")
        log(logger, "Error checking input file: {}, please check this input file is related to your subtomograms, and in the correct format".\
                    format(train_params.train_subtomos_star), "error")

        #log(logger, "There is formating issue with the input JSON file {}".format(argv[1]), "error")
        sys.exit()
    
    #print(vars(train_params))

    from TomoNet.models.network_isonet import Net

    network = Net()

    ###  find current iterations ###        
    current_iter = train_params.iter_count if hasattr(train_params, "iter_count") else 1
    if train_params.continue_from_iter is not None:
        current_iter += 1
    
    ###  Main Loop ###
    ###  1. find network model file ###
    ###  2. prediction if network found ###
    ###  3. prepare training data ###
    ###  4. training and save model file ###

    for num_iter in range(current_iter, train_params.train_iteration + 1):        
        
        log(logger, "Start Iteration #{}!".format(num_iter))

        ### Select a subset of subtomos, useful when the number of subtomo is too large ###
        # if train_params.select_subtomo_number is not None:
        #     train_params.mrc_list = np.random.choice(train_params.all_mrc_list, size = int(train_params.select_subtomo_number), replace = False)
        # else:
        
        train_params.mrc_list = train_params.all_mrc_list

        ### Update the iteration count ###
        train_params.iter_count = num_iter
        train_params.model_file = "{}/model_iter{:0>2d}.h5".format(train_params.train_result_folder, num_iter - 1)
        
        if num_iter == 1 and train_params.train_pretrained_model is None:
        ### First iteration ###
            mkfolder(train_params.train_result_folder)
            network.save(train_params.model_file)
            prepare_first_iter(train_params)
            if train_params.continue_from_iter is not None:
                log(logger, "Ignore continue from iterations and start from first iteration", "warning")                    
        else:
            if train_params.train_pretrained_model is not None and train_params.continue_from_iter is not None:
                log(logger, "You provided both pretrained model and continue_from! Those two parameters conflict with each other.", "error")
                sys.exit()

            ### use pretrained model ###
            if train_params.train_pretrained_model is not None:
                mkfolder(train_params.train_result_folder)  
                shutil.copyfile(train_params.train_pretrained_model, train_params.model_file)
                network.load(train_params.model_file)

                logging.info('Use Pretrained model as the output model of iteration {} and predict subtomograms'.format(num_iter - 1))
                train_params.train_pretrained_model = None

            ### Continue from a json file ###
            if train_params.continue_from_iter is not None:
                log(logger, 'Continue from previous model: {} and predict subtomograms'.format(train_params.model_file))
                train_params.continue_from_iter = None
                if os.path.exists(train_params.model_file):
                    network.load(train_params.model_file)
                else:
                    log(logger, "Continue from iteration # defined, however, the corresponding model file {} cannot be found.".format(train_params.model_file), "error")
                    sys.exit()

            ### Subsequent iterations for all conditions ###
            log(logger, "Start predicting subtomograms!")
            network.predict(train_params.mrc_list, train_params.train_result_folder, train_params.iter_count)
            log(logger, "Done predicting subtomograms!")

        ### Noise settings ###
        num_noise_volume = 1000
        if num_iter >= train_params.noise_start_iter[0] and \
                    (not os.path.isdir(train_params.noise_dir) or \
                    len(os.listdir(train_params.noise_dir)) < num_noise_volume):
            
            from TomoNet.util.noise_generator import make_noise_folder
            make_noise_folder(train_params.noise_dir, train_params.noise_mode, train_params.cube_size, \
                                                num_noise_volume, ncpus=train_params.train_ncpu, logger=logger)
             
        noise_level_series = get_noise_level(train_params.noise_level, train_params.noise_start_iter, train_params.train_iteration)
        train_params.noise_level_current =  noise_level_series[num_iter]
        log(logger, "Noise Level:{}".format(train_params.noise_level_current))
 
        ### remove data_dir and generate training data in data_dir###
        try:
            shutil.rmtree(train_params.data_dir)     
        except OSError:
            pass
        get_cubes_list(train_params)
        log(logger, "Done preparing subtomograms for iteration #{}!".format(train_params.iter_count))

        ### remove all the mrc files in results_dir ###
        if train_params.remove_intermediate is True:
            log(logger, "Remove intermediate files in iteration {}".format(train_params.iter_count-1))
            for mrc in train_params.mrc_list:
                root_name = mrc.split('/')[-1].split('.')[0]
                current_mrc = '{}/{}_iter{:0>2d}.mrc'.format(train_params.train_result_folder, root_name, train_params.iter_count-1)
                os.remove(current_mrc)

        ### start training and save model and json ###
        log(logger, "Start training iteration #{}!".format(num_iter))
        log(logger, "The training progress shows in terminal.")
        # try:
        metrics = network.train(train_params.data_dir, gpuID=train_params.gpu_list, 
                        learning_rate=train_params.train_learning_rate, batch_size=train_params.train_batch_size,
                        epochs = train_params.train_epoch_num, steps_per_epoch=train_params.train_steps_per_epoch, acc_grad=train_params.low_mem) #train based on init model and save new one as model_iter{num_iter}.h5
        # except KeyboardInterrupt as exception: 
        #     sys.exit("Keyboard interrupt")
        train_params.metrics = metrics

        network.save('{}/model_iter{:0>2d}.h5'.format(train_params.train_result_folder, train_params.iter_count))

        save_args_json(train_params, train_params.train_result_folder+'/refine_iter{:0>2d}.json'.format(num_iter))
        from TomoNet.util.plot_metrics import plot_metrics
        plot_metrics(metrics, train_params.train_result_folder+"/losses.png")
        log(logger, "Done training iteration #{}!".format(num_iter))

        ### for last iteration predict subtomograms ###
        if num_iter == train_params.train_iteration and train_params.remove_intermediate == False:
            log(logger, "Predicting subtomograms for last iterations")
            train_params.iter_count +=1 
            network.predict(train_params.mrc_list, train_params.train_result_folder, train_params.iter_count)
            train_params.iter_count -=1 

        log(logger, "Done Iteration #{}!".format(num_iter))
