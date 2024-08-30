#!/usr/bin/env python3
import os, sys, logging, re
#from TomoNet.util.image import *

from TomoNet.util.metadata import MetaData, Label
from TomoNet.util.dict2attr import idx2list
from TomoNet.util.io import log
from TomoNet.util.searchParam import SearchParam 
from TomoNet.models.network_isonet import Net 

def check_gpu(gpu_ID, logger):
    import torch
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
    #*******set fixed parameters*******
  
    if not hasattr(args, "normalize_percentile"):
        args.normalize_percentile = True

    if not hasattr(args, "use_deconv_tomo"):
        args.use_deconv_tomo = True

    if not hasattr(args, "batch_size"):
        args.batch_size = None

    return args

def predict(args):

    gpu_ID = re.split(',| ', args.gpuID)

    args.ngpus = len(gpu_ID)

    logger = args.logger

    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"]=args.gpuID

    if not check_gpu(gpu_ID, logger):
        sys.exit()
    
    args = check_params(args)

    #log(logger, 'percentile: {}'.format(args.normalize_percentile))
    #log(logger, 'gpuID: {}'.format(args.gpuID))

    network = Net(logger=logger)
    #network.initialize()
    network.load(args.model)

    if args.batch_size is None:
        args.batch_size = 4 * args.ngpus
    
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    md = MetaData()
    md.read(args.star_file)

    if not 'rlnCorrectedTomoName' in md.getLabels():
        md.addLabels('rlnCorrectedTomoName')
        for it in md:
            md._setItemValue(it, Label('rlnCorrectedTomoName'), None)
    
    args.tomo_idx = idx2list(args.tomo_idx)

    log(logger, "\n###### IsoNet starts Predicting ######")

    for it in md:
        if args.tomo_idx is None or str(it.rlnIndex) in args.tomo_idx:
            if args.use_deconv_tomo and "rlnDeconvTomoName" in md.getLabels() and it.rlnDeconvTomoName not in [None,'None']:
                tomo_file = it.rlnDeconvTomoName
            else:
                tomo_file = it.rlnMicrographName

            tomo_root_name = os.path.splitext(os.path.basename(tomo_file))[0]
            
            if os.path.isfile(tomo_file):
                tomo_out_name = '{}/{}_corrected.mrc'.format(args.output_dir, tomo_root_name)
                network.predict_tomo(args, tomo_file, output_file=tomo_out_name)
                md._setItemValue(it, Label('rlnCorrectedTomoName'), tomo_out_name)
    md.write(args.star_file)

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
            predict_params = SearchParam(argv[1])
        except Exception as err:
            log(logger, err, "error")
            log(logger, "There is formating issue with the input JSON file {}".format(argv[1]), "error")
            sys.exit()
    
    predict_params.logger = logger

    predict(predict_params)