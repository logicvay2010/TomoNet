import os
import logging
from PyQt5.QtCore import QThread

from TomoNet.util.dict2attr import idx2list

from TomoNet.preprocessing.prepare import extract_subtomos

class ExtractSubtomos(QThread):

    def __init__(self, d):
        super().__init__()
        self.d = d

        # self.mask_folder = d['mask_folder']
        # self.tomogram_star = d['tomogram_star'] 
        # self.tomo_idx = d['tomo_idx']
        # self.patch_size_mask = d['patch_size_mask']
        # self.zAxis_crop_mask = d['zAxis_crop_mask']
        # self.use_deconv_mask = d['use_deconv_mask']

        # self.log_file = "IsoNet/isonet.log"

        # self.isonet_folder = "IsoNet"
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def run(self):

        logging.info("\n##################Isonet starts extracting subtomograms##################\n")

        try:
            if os.path.isdir(subtomo_folder):
                logging.warning("subtomo directory exists, the current directory will be overwritten")
                import shutil
                shutil.rmtree(subtomo_folder)
            os.mkdir(subtomo_folder)


            if crop_size is None:
                d_args.crop_size = cube_size + 16
            else:
                d_args.crop_size = crop_size
            d_args.subtomo_dir = subtomo_folder
            d_args.tomo_idx = idx2list(tomo_idx)
            extract_subtomos(d_args)
            logging.info("\n######Isonet done extracting subtomograms######\n")
        except Exception:
            error_text = traceback.format_exc()
            f =open('log.txt','a+')
            f.write(error_text)
            f.close()
            logging.error(error_text)
    
    def stop_process(self):
        self.quit()
        self.terminate()
        self.wait()