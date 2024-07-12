import os
import subprocess
import logging
import mrcfile
import numpy as np
from multiprocessing import Pool
from PyQt5.QtCore import QThread

def newstack(param):
        
    image_folder = param['image_folder'] 
    tomo_lists = param['tomo_list'] 
    rawtlt_lists = [str(x) for x in param['rawtlt_list'] ]
    base_name = param['base_name'] 
    index = param['index'] 
    ts_folder = param['ts_folder'] 
    logger = param['logger'] 
    origin_tomo = param['origin_tomo']
    existing_tomo = param['existing_tomo']
    history_record_file = param['history_record_file']
    flip_axis = param['flip_axis']
    generate_odd_even = param['generate_odd_even']

    folder_ODD = "{}/ODD".format(ts_folder)
    folder_EVN = "{}/EVN".format(ts_folder)

    if ts_folder[-1] == '/':
        ts_folder = ts_folder[:-1]
    if image_folder[-1] == '/':
        image_folder = image_folder[:-1]

    if origin_tomo not in existing_tomo:
        output_name = "{}/{}_{}.st".format(ts_folder, base_name, index)
        output_tlt = "{}/{}_{}.rawtlt".format(ts_folder, base_name, index)
        input_images = ["{}/{}".format(image_folder,x) for x in tomo_lists]
        cmd = "newstack {} {} ".format(" ".join(input_images), output_name)

        try:        
            subprocess.check_output(cmd, shell=True)
            with open(output_tlt, "w") as f:
                for i in rawtlt_lists:
                    f.write("{}\n".format(i))
        except Exception as err:
            logger.error('Fail generating Tilt Series for {}_{}!'.format(base_name, index))
            logger.error(f"Unexpected {err=}, {type(err)=}")
        # deal with flip
        try:
            if flip_axis in [1, 2]:
                #flip by X or Y axis
                output_name_flip = "{}/{}_{}_flip.st".format(ts_folder, base_name, index)
                mrc = mrcfile.open(output_name)
                mrcdata_flip = np.flip(mrc.data, axis=flip_axis)
                apix = mrc.voxel_size   
                mrc.close()

                mrc_flip = mrcfile.new(output_name_flip, overwrite=True)
                mrc_flip.set_data(mrcdata_flip)
                mrc_flip.voxel_size = apix.copy()
                #print(mrc_flip.voxel_size)
                mrc_flip.close()

                os.replace(output_name_flip, output_name)
        except:
            logger.error("Fail flipping axis for {}.".format(output_name))

        if generate_odd_even == 1:
            output_name_ODD = "{}/{}_{}_ODD.st".format(folder_ODD, base_name, index)
            output_tlt_ODD = "{}/{}_{}_ODD.rawtlt".format(folder_ODD, base_name, index)
            try:
                input_images_ODD = ["{}/ODD_sums/{}_ODD{}".format(\
                    image_folder, os.path.splitext(x)[0],os.path.splitext(x)[1]) for x in tomo_lists]
                cmd = "newstack {} {} ".format(" ".join(input_images_ODD), output_name_ODD)
            except Exception as err:
                logger.error('Fail generating ODD and EVN Tilt Series for {}_{}!'.format(base_name, index))
                logger.error(f"Unexpected {err=}, {type(err)=}")
            try:        
                subprocess.check_output(cmd, shell=True)
                with open(output_tlt_ODD, "w") as f:
                    for i in rawtlt_lists:
                        f.write("{}\n".format(i))
            except Exception as err:
                logger.error('Fail generating ODD and EVN Tilt Series for {}_{}!'.format(base_name, index))
                logger.error(f"Unexpected {err=}, {type(err)=}")
            # deal with flip
            try:
                if flip_axis in [1, 2]:
                    #flip by X or Y axis
                    output_name_ODD_flip = "{}/{}_{}_ODD_flip.st".format(folder_ODD, base_name, index)
                    mrc = mrcfile.open(output_name_ODD_flip)
                    mrcdata_flip = np.flip(mrc.data, axis=flip_axis)
                    apix = mrc.voxel_size   
                    mrc.close()
                    mrc_flip = mrcfile.new(output_name_ODD_flip, overwrite=True)
                    mrc_flip.set_data(mrcdata_flip)
                    mrc_flip.voxel_size = apix.copy()
                    mrc_flip.close()
                    os.replace(output_name_ODD_flip, output_name_ODD)
            except:
                logger.error("Fail flipping axis for {}.".format(output_name_ODD))

            output_name_EVN = "{}/{}_{}_EVN.st".format(folder_EVN, base_name, index)
            output_tlt_EVN = "{}/{}_{}_EVN.rawtlt".format(folder_EVN, base_name, index)
            try:
                input_images_EVN = ["{}/EVN_sums/{}_EVN{}".format(\
                    image_folder, os.path.splitext(x)[0],os.path.splitext(x)[1]) for x in tomo_lists]
                cmd = "newstack {} {} ".format(" ".join(input_images_EVN), output_name_EVN)
            except Exception as err:
                logger.error('Fail generating ODD and EVN Tilt Series for {}_{}!'.format(base_name, index))
                logger.error(f"Unexpected {err=}, {type(err)=}")
            try:        
                subprocess.check_output(cmd, shell=True)
                with open(output_tlt_EVN, "w") as f:
                    for i in rawtlt_lists:
                        f.write("{}\n".format(i))
            except Exception as err:
                logger.error('Fail generating ODD and EVN Tilt Series for {}_{}!'.format(base_name, index))
                logger.error(f"Unexpected {err=}, {type(err)=}")
            # deal with flip
            try:
                if flip_axis in [1, 2]:
                    #flip by X or Y axis
                    output_name_EVN_flip = "{}/{}_{}_EVN_flip.st".format(folder_EVN, base_name, index)
                    mrc = mrcfile.open(output_name_EVN_flip)
                    mrcdata_flip = np.flip(mrc.data, axis=flip_axis)
                    apix = mrc.voxel_size   
                    mrc.close()
                    mrc_flip = mrcfile.new(output_name_EVN_flip, overwrite=True)
                    mrc_flip.set_data(mrcdata_flip)
                    mrc_flip.voxel_size = apix.copy()
                    mrc_flip.close()
                    os.replace(output_name_EVN_flip, output_name_EVN)
            except:
                logger.error("Fail flipping axis for {}.".format(output_name_EVN))
        try:
            with open(history_record_file, "a") as f:
                f.write("{}->{}_{}\n".format(origin_tomo, base_name, index))
        except:
            logger.error("Fail to write file into {}.".format(history_record_file))
        
        logger.info("{}   >>>>>>>>   {}_{}"\
            .format(origin_tomo, base_name, index))
    else:
        logger.info("{}   >>>>>>>>   {}_{} was processed, skip!"\
            .format(origin_tomo, base_name, index))

class Generate_TS(QThread):

    def __init__(self, image_folder, tomo_lists, rawtlt_lists, base_name, start_index, delimiter, key_index, ts_folder = "Recon/ts_tlt",cpus=8, flip_axis=0, only_process_unfinished=1, generate_odd_even=0):
        super().__init__()

        self._history_record = "Recon/history_record.txt"

        self._image_folder = image_folder
        self._ts_folder = ts_folder
        self._tomo_lists = tomo_lists
        self._rawtlt_lists = rawtlt_lists
        self._base_name = base_name
        self._start_index = start_index
        self.params = []
        self.cpus = cpus
        self.key_index = key_index
        self.delimiter = delimiter
        self.flip_axis = flip_axis
        self.only_process_unfinished = only_process_unfinished
        self.generate_odd_even = generate_odd_even

        self.log_file = "Recon/recon.log"
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

        folder_ODD = "{}/ODD".format(ts_folder)
        folder_EVN = "{}/EVN".format(ts_folder)
        if generate_odd_even == 1:
            try:
                if not os.path.exists(folder_ODD):
                    os.mkdir(folder_ODD)
                if not os.path.exists(folder_EVN):
                    os.mkdir(folder_EVN)
            except Exception as err:
                self.logger.error('Fail generating ODD and EVN sub-folder!')
                self.logger.error(f"Unexpected {err=}, {type(err)=}")

        existing_tomo = []

        if only_process_unfinished == 1:
            if os.path.exists(self._history_record):
                with open(self._history_record) as file:
                    try:
                        existing_tomo = [line.rstrip().split("->")[0] for line in file]
                    except:
                        self.logger.warning("The history record file's format is wrong: {}".format(self._history_record))
            else:
                self.logger.warning("The history record file is not found: {}.".format(self._history_record))
        else:
            try:
                os.remove(self._history_record)
                self.logger.warning("Only Process Unfinished Data set as No. The old history record file is removed: {}.".format(self._history_record))
            except:
                pass
        acc = 0
        for i in range(len(self._tomo_lists)):
            try:
                origin_tomo = self.delimiter.join\
                    (self._tomo_lists[i][0].split(self.delimiter)[self.key_index[0]:self.key_index[1]])
            except Exception as err:
                self.logger.error(f"Unexpected {err=}, {type(err)=}")
                continue
            if origin_tomo not in existing_tomo:
                current_param = {}
                current_param['image_folder'] = self._image_folder
                current_param['tomo_list'] = self._tomo_lists[i]
                current_param['rawtlt_list'] = self._rawtlt_lists[i]
                current_param['base_name'] = self._base_name
                current_param['index'] = self._start_index + acc
                current_param['ts_folder'] = self._ts_folder
                current_param['logger'] = self.logger
                current_param['origin_tomo'] = origin_tomo
                current_param['existing_tomo'] = existing_tomo
                current_param['history_record_file'] = self._history_record
                current_param['flip_axis'] = self.flip_axis
                current_param['generate_odd_even'] = self.generate_odd_even
                acc+=1
                self.params.append(current_param)
            else:
                self.logger.info("{} already been processed, skiped!".format(origin_tomo))
    
    def set_param(self, image_folder, tomo_lists, rawtlt_lists, base_name, start_index, ts_folder = "Recon/ts_tlt", cpus=8, flip_axis=0):
        
        self._image_folder = image_folder
        self._ts_folder = ts_folder
        self._tomo_lists = tomo_lists
        self._rawtlt_lists = rawtlt_lists
        self._base_name = base_name
        self._start_index = start_index
        self.params = []
        self.cpus = cpus
        self.flip_axis = flip_axis
        for i in range(len(self._tomo_lists)):
            current_param = {}
            current_param['image_folder'] = self._image_folder
            current_param['tomo_list'] = self._tomo_lists[i]
            current_param['rawtlt_list'] = self._rawtlt_lists[i]
            current_param['base_name'] = self._base_name
            current_param['index'] = self._start_index + i
            current_param['ts_folder'] = self._ts_folder
            current_param['logger'] = self.logger
            current_param['flip_axis'] = self.flip_axis
            self.params.append(current_param)

    def run(self):
        if not os.path.exists(self._ts_folder):
            os.makedirs(self._ts_folder)
            
        self.pool = Pool(self.cpus)
        self.pool.map(newstack, self.params)

    def stop_process(self):
        self.pool.terminate()
        self.terminate()
        self.quit()
        self.wait()
    

