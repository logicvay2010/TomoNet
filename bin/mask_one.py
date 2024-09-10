#!/usr/bin/env python3
import os, time
import mrcfile
import numpy as np
from skimage.transform import resize
from scipy.ndimage import gaussian_filter
from TomoNet.util.filter import maxmask, stdmask
from TomoNet.util.io import log
from TomoNet.util.searchParam import SearchParam 

def make_mask_one(tomo_path, mask_name, mask_boundary = None, side = 5, density_percentage=50.0, std_percentage=50.0, surface=None, logger=None):
        
        with mrcfile.open(tomo_path, permissive=True) as n:
            header_input = n.header
            pixel_size = n.voxel_size
            tomo = n.data.astype(np.float32)
        sp=np.array(tomo.shape)
        sp2 = sp//2
        bintomo = resize(tomo,sp2,anti_aliasing=True)
    
        gauss = gaussian_filter(bintomo, side/2)
        if density_percentage <=99.8:
            mask1 = maxmask(gauss,side=side, percentile=density_percentage)
        else:
            mask1 = np.ones(sp2)

        if std_percentage <=99.8:
            mask2 = stdmask(gauss,side=side, threshold=std_percentage)
        else:
            mask2 = np.ones(sp2)

        out_mask_bin = np.multiply(mask1,mask2)
    
        if mask_boundary is not None:
            from TomoNet.util.filter import boundary_mask
            mask3 = boundary_mask(bintomo, mask_boundary, logger=logger)
            out_mask_bin = np.multiply(out_mask_bin, mask3)

        if (surface is not None) and surface < 1:
            for i in range(int(surface*sp2[0])):
                out_mask_bin[i] = 0
            for i in range(int((1-surface)*sp2[0]),sp2[0]):
                out_mask_bin[i] = 0

        out_mask = np.zeros(sp)
        out_mask[0:-1:2,0:-1:2,0:-1:2] = out_mask_bin
        out_mask[0:-1:2,0:-1:2,1::2] = out_mask_bin
        out_mask[0:-1:2,1::2,0:-1:2] = out_mask_bin
        out_mask[0:-1:2,1::2,1::2] = out_mask_bin
        out_mask[1::2,0:-1:2,0:-1:2] = out_mask_bin
        out_mask[1::2,0:-1:2,1::2] = out_mask_bin
        out_mask[1::2,1::2,0:-1:2] = out_mask_bin
        out_mask[1::2,1::2,1::2] = out_mask_bin
        out_mask = (out_mask>0.5).astype(np.uint8)

        with mrcfile.new(mask_name,overwrite=True) as n:
            n.set_data(out_mask)

            n.header.extra2 = header_input.extra2
            n.header.origin = header_input.origin
            n.header.nversion = header_input.nversion
            n.voxel_size = pixel_size

if __name__ == "__main__":
    import logging, sys

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
            mask_params = SearchParam(argv[1])
        except Exception as err:
            log(logger, err, "error")
            log(logger, "There is formating issue with the input JSON file {}".format(argv[1]), "error")
            sys.exit()
    t1 = time.time()

    make_mask_one(mask_params.tomo_file, mask_params.mask_out_name, mask_params.mask_boundary, 
                  mask_params.side, mask_params.density_percentage, 
                  mask_params.std_percentage, mask_params.surface, logger=logger)
    
    log(logger, 'time consumed: {:10.4f} s'.format(time.time()-t1))