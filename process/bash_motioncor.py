import os, time, re, logging, subprocess
import glob
import torch
import multiprocessing as mp
from multiprocessing import Pool

from PyQt5.QtCore import QThread
#from TomoNet.util.io import mkfolder

def check_output(output_file):
    with open(output_file, 'r') as f:
        try:
            last_line = f.readlines()[-1]
            if "Total time" in last_line:
                return True
        except:
            return False
    return False

def motioncor_single(param):
    cmd = '{}{}{}{}{}'.format(param['cmd_1'],param['cmd_2'],param['cmd_3'],param['cmd_4'],param['cmd_last'])
    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as err:
        param['logger'].error('MotionCor2 failed!')
        param['logger'].error(err)
        return -1
    
    cmd = '{}'.format(param['cmd_5'])
    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as err:
        param['logger'].error('MotionCor2 failed!')
        param['logger'].error(err)
        return -1
    
    try:
        if check_output(param['output_file']):
            cmd = param['cmd_6']
            subprocess.check_output(cmd, shell=True)

            param['logger'].info('Done processing on GPU {}: {}'.format(param['gpu'], param['image']))
        else:
            param['logger'].warning('processing on GPU {} error: {}. Will try it later.'.format(param['gpu'], param['image']))
    except:
        param['logger'].warning('processing on GPU {} error: {}. File is not detected, maybe it is already been processed.'.format(param['gpu'], param['image']))
        return -1

class MotionCor2(QThread):

    def __init__(self,d, corrected_folder,processed_folder):
        super().__init__()
        self.d = d
        self.corrected_folder =corrected_folder
        self.processed_folder = processed_folder
        self.log_file = "MotionCorrection/motion.log"
        self.pool = None
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def run(self):
        counter = 0
        gpu_ID = re.split(',| ', self.d["gpu_ID"])

        try:
            detected_gpu_num = torch.cuda.device_count()
            if detected_gpu_num == 0:
                self.logger.error("GPU is not detected!")
                return 
            elif detected_gpu_num < len(gpu_ID):
                self.logger.error("Ask for {} GPUs, but only detected {} GPUs!".format(len(gpu_ID), detected_gpu_num))
                return 
        except:
            self.logger.error("GPU is not detected!")
            return 

        if not os.path.exists(self.corrected_folder):
                os.makedirs(self.corrected_folder)
        if not os.path.exists(self.processed_folder):
                os.makedirs(self.processed_folder)
        
        max_counter = 100
        while counter < max_counter:
            batch_size = len(gpu_ID)
            try:
                raw_images = sorted([ os.path.basename(x) for x in glob.glob("{}/*.{}".format(self.d['raw_image_folder'], self.d['input_file_type']))])
            except:
                raw_images = []
            if len(raw_images) > 0:
                self.logger.info("########Processing {} images on GPU {}########".format(len(raw_images), self.d["gpu_ID"]))
                self.logger.info("########The results will be saved in {}########".format(self.corrected_folder))

                if self.d['input_file_type'] == 'mrc':
                    input_file_type = '-InMrc'
                else:
                    input_file_type = '-InTiff'
                cmd_1 = 'echo \"{} {} '.format(self.d['motioncor_exe'], input_file_type)

                if not self.d['frame_dose']:
                    cmd_3 = '-Gain {} -InitDose {}  -RotGain 0  -FlipGain 0   -Patch 5 5 10  -Iter 10  -Tol 0.4 -Throw 0  -Trunc 0'\
                            '  -Kv 300 -PixSize  {}  -Bft 500  150  -FtBin {} '\
                            ' -OutStack 0 -Group 1 {} '.format(self.d['gain_ref'],self.d['frame_dose'], self.d['pixel_size'], \
                                self.d['ftbin'], self.d['addtional_param'])
                else:
                    cmd_3 = '-Gain {} -InitDose {}  -RotGain 0  -FlipGain 0   -Patch 5 5 10  -Iter 10  -Tol 0.4 -Throw 0  -Trunc 0'\
                            '  -Kv 300 -PixSize  {}  -FmDose {} -Bft 500  150  -FtBin {} '\
                            ' -OutStack 0 -Group 1 {} '.format(self.d['gain_ref'],self.d['frame_dose'], self.d['pixel_size'], \
                                self.d['frame_dose'], self.d['ftbin'], self.d['addtional_param'])
                t = len(self.d['input_file_type'])

                if self.d['splitSum'] == 'Yes':
                    cmd_4 = '-SplitSum 1 '
                    try:
                        ODD_folder = "{}/ODD_sums".format(self.corrected_folder)
                        EVN_folder = "{}/EVN_sums".format(self.corrected_folder)
                        if not os.path.exists(ODD_folder):
                            os.mkdir(ODD_folder)
                        if not os.path.exists(EVN_folder):
                            os.mkdir(EVN_folder)
                        #mkdir directory for ODD and EVN tilts
                    except Exception as err:
                        self.logger.error('Creating ODD and EVN subfolder failed!')
                        self.logger.error(err)
                        break
                else:
                    cmd_4 = '-SplitSum 0 '

                if batch_size == 1:
                    for image in raw_images:
                        
                        basename = image[:-t-1]
                        cmd_2 = '{}/{} -OutMrc {}/{}_ali.mrc '.format(self.d['raw_image_folder'], image, self.corrected_folder, basename)
                        cmd_last = '-Gpu {} -LogFile {}/{}.log > {}/{}_MotionCor2_output.log 2>&1 '\
                                '\" > {}/{}_MotionCor2_cmd.log'.format(gpu_ID[0], self.corrected_folder, basename, self.corrected_folder,\
                                basename, self.corrected_folder, basename)
                        
                        cmd = '{}{}{}{}{};'.format(cmd_1,cmd_2,cmd_3,cmd_4,cmd_last)
                        try:
                            subprocess.check_output(cmd, shell=True)
                        except Exception as err:
                            self.logger.error('MotionCor2 failed!')
                            self.logger.error(err)
                            break
                        cmd = 'sh {}/{}_MotionCor2_cmd.log'.format(self.corrected_folder, basename)
                        try:
                            subprocess.check_output(cmd, shell=True)
                        except Exception as err:
                            self.logger.error('MotionCor2 failed!')
                            self.logger.error(err)
                            break

                        if check_output("{}/{}_MotionCor2_output.log".format(self.corrected_folder, basename)):
                            try:
                                cmd = 'mv {}/{} {}/'.format(self.d['raw_image_folder'], image, self.processed_folder)
                                subprocess.check_output(cmd, shell=True)
                                self.logger.info('Done processing on GPU {}: {}'.format(gpu_ID[0], image))
                                corrected_images_ODD = "{}/{}_ali_ODD.mrc".format(self.corrected_folder, basename)
                                corrected_images_EVN = "{}/{}_ali_EVN.mrc".format(self.corrected_folder, basename)
                                if self.d['splitSum'] == 'Yes':
                                    cmd = "mv {} {}/; mv {} {}/;".format(corrected_images_ODD, ODD_folder, corrected_images_EVN, EVN_folder)
                                    subprocess.check_output(cmd, shell=True)
                            except Exception as err:
                                self.logger.error('failed move raw frames into {}!'.format(self.processed_folder))
                                self.logger.error(err)
                                #break
                        else:
                            self.logger.warning('processing on GPU {} error: {}. Will try it later.'.format(gpu_ID[0], image))
                elif batch_size > 1:
                    TIMEOUT = 120
                    while len(raw_images) > 0:
                        params = []
                        current_images = []
                        s = min(len(raw_images),batch_size)
                        for i,image in enumerate(raw_images[:s]):
                            param = {}
                            basename = image[:-t-1]
                            cmd_2 = '{}/{} -OutMrc {}/{}_ali.mrc '.format(self.d['raw_image_folder'],image,self.corrected_folder,basename)
                            cmd_last = '-Gpu {} -LogFile {}/{}.log > {}/{}_MotionCor2_output.log 2>&1 '\
                                '\" > {}/{}_MotionCor2_cmd.log'.format(gpu_ID[i], self.corrected_folder, basename, self.corrected_folder,\
                                basename, self.corrected_folder, basename)
                            cmd_5 = 'sh {}/{}_MotionCor2_cmd.log'.format(self.corrected_folder, basename)
                            if self.d['splitSum'] == 'Yes':
                                corrected_images_ODD = "{}/{}_ali_ODD.mrc".format(self.corrected_folder, basename)
                                corrected_images_EVN = "{}/{}_ali_EVN.mrc".format(self.corrected_folder, basename)
                                cmd_6 = 'mv {}/{} {}/; mv {} {}/; mv {} {}/;'.format(\
                                    self.d['raw_image_folder'], image, self.processed_folder, \
                                    corrected_images_ODD, ODD_folder, corrected_images_EVN, EVN_folder)
                            else:
                                cmd_6 = 'mv {}/{} {}/'.format(self.d['raw_image_folder'], image, self.processed_folder)
                            param['cmd_1'] = cmd_1
                            param['cmd_2'] = cmd_2
                            param['cmd_3'] = cmd_3
                            param['cmd_4'] = cmd_4
                            param['cmd_5'] = cmd_5
                            param['cmd_6'] = cmd_6
                            param['cmd_last'] = cmd_last
                            param['output_file'] = "{}/{}_MotionCor2_output.log".format(self.corrected_folder, basename)
                            param['gpu'] = gpu_ID[i]
                            param['image'] = image
                            param['logger'] = self.logger
                            params.append(param)
                            current_images.append(image)

                        with Pool(s) as pool:
                            results = [pool.apply_async(motioncor_single, args=(v,)) for v in params]
                            time_to_wait = TIMEOUT
                            start_time = time.time()
                            
                            for index, result in enumerate(results):
                                try:
                                    return_value = result.get(time_to_wait) # wait for up to time_to_wait seconds
                                except mp.TimeoutError:
                                    self.logger.warning('Skip processing on GPU {} after 2 mins: {}'.format(gpu_ID[index], current_images[index]))
                                used_time = time.time() - start_time
                                time_to_wait = TIMEOUT - used_time
                                if time_to_wait < 0:
                                    time_to_wait = 0
                        #set timeout just in case progress get stucked

                        raw_images = raw_images[batch_size:]
                        self.logger.info('{} images left for this round.'.format(len(raw_images)))  
                else:
                    self.logger.info('No GPU ID provided')
                    return -1
            else:
                self.logger.info('No frames detected! Please make sure all parameters are properly set.')
            counter +=1
            self.logger.info('No frames left now! Sleep for 5 min! <{}/{}>'.format(counter,max_counter))
            time.sleep(300)
            
    
    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()