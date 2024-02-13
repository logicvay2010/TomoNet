from PyQt5.QtCore import QThread
import os, time, glob
import multiprocessing as mp
from multiprocessing import Pool
import subprocess
import re
import logging
import torch
import shutil
from TomoNet.util.utils import mkfolder

def read_header(st_path):
    d = {}
    d['apix'] = 1.0
    cmd = "header {} ".format(st_path)
    out = subprocess.check_output(cmd, shell=True)
    lines = out.decode('utf-8').split("\n")
    for line in lines:
        if "Pixel spacing" in line:
            apix = line.strip().split()[-1]
            d['apix'] = float(apix)
        if "Number of columns" in line:
            sections = line.strip().split()[-1]
            d['sections'] = int(sections)  
    return d

def aretomo_single(param):
    cmd = '{}{}{}{}; {}'.format(param['cmd_1'],param['cmd_2'],param['cmd_3'],param['cmd_4'],param['cmd_5'])
    try:
        subprocess.check_output(cmd, shell=True)
    except:
        param['logger'].warning('processing on GPU {} error: {}. File is not detected, maybe it is already been processed.'.format(param['gpu'], param['image']))

def check_output(aretomo_folder, ts, tomoName):
    log_file = "{}/{}.log".format(aretomo_folder,tomoName)
    
    success = False
    with open(log_file, 'r') as f:
        try:
            for last_line in f.readlines()[-3:]:
                if "Total time" in last_line:
                    success = True
        except:
            return -1
    if not success:
        return -1
    else:
        aln_file_path = "{}/{}.aln".format(aretomo_folder, ts)
        #print(aln_file_path)
        rec_file = "{}/{}.rec".format(aretomo_folder, tomoName)
        #print(rec_file)
        proj_files = ["{}_projXZ.mrc".format(rec_file), "{}_projXY.mrc".format(rec_file)]
        #print(proj_files)
        folder_imod = "{}_Imod".format(rec_file)
        #print(folder_imod)
        folder_imod_correct = "{}/{}".format(aretomo_folder, tomoName)
        #print(folder_imod_correct)
        try:
            aln_file_old_path = "{}/{}.aln".format(folder_imod_correct, tomoName)
            aln_file_path_correct_1 = "{}/{}.aln".format(aretomo_folder, tomoName)
            if os.path.exists(aln_file_path):
                os.replace(aln_file_path, aln_file_path_correct_1)
            elif os.path.exists(aln_file_old_path):
                os.replace(aln_file_old_path, aln_file_path_correct_1)
            if os.path.exists(folder_imod_correct):
                shutil.rmtree(folder_imod_correct)
            shutil.move(folder_imod, folder_imod_correct)
            #mkfolder(folder_imod_correct)
            
            aln_file_path_correct_2 = "{}/{}.aln".format(folder_imod_correct, tomoName)
            os.replace(aln_file_path_correct_1, aln_file_path_correct_2)

            rec_file_correct = "{}/{}.rec".format(folder_imod_correct, tomoName)
            os.replace(rec_file, rec_file_correct)
            
            for proj in proj_files:
                os.remove(proj)
            log_file_correct = "{}/{}.log".format(folder_imod_correct, tomoName)
            os.replace(log_file, log_file_correct)

        except:
            return -1
        
        

    return 1

class AreTomo(QThread):

    def __init__(self,d, processed_folder):
        super().__init__()
        self.d = d
        self.processed_folder = processed_folder
        self.log_file = "Recon/recon.log"
        self.pool = None
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def run(self):
        gpu_ID = re.split(',| ', self.d["GPU_ID"])
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
        
        if not os.path.exists(self.processed_folder):
            os.makedirs(self.processed_folder)

        #raw_images = sorted([ os.path.basename(x) for x in glob.glob("{}/*.{}".format(self.d['raw_image_folder'], self.d['input_file_type']))])
        self.logger.info("\n########Processing {} images on GPU {}########".format(len(self.d['current_ts_list']), self.d["GPU_ID"]))
        self.logger.info("\n########The results will be saved in {}########".format(self.processed_folder))
        cmd_1 = "AreTomo"

        batch_size = len(gpu_ID)

        if batch_size == 1:
            for ts in self.d['current_ts_list']:
                tomoName = ts.split('.st')[0]    
                full_ts_path = "{}/{}".format(self.d['aretomo_input_folder'], ts)
                cmd_2 = "-InMrc {}".format(full_ts_path)
                output_path = "{}/{}.rec".format(self.processed_folder, tomoName) 
                cmd_3 = "-OutMrc {}".format(output_path)

                full_rawtlt_path = "{}/{}.rawtlt".format(self.d['aretomo_input_folder'], tomoName)
                if not os.path.exists(full_rawtlt_path):
                    self.logger.warning("*.rawtlt file is not found! Skip tomo {}".format(tomoName))
                    continue
                else:
                    cmd_4 = "-AngFile {}".format(full_rawtlt_path)

                cmd_5=''
                if self.d['UseAlnFile'] == 1:
                    full_path_AlnFile = "{}/{}/{}.aln".format(self.processed_folder, tomoName, tomoName)
                    if os.path.exists(full_path_AlnFile):
                        cmd_5 = "-AlnFile {}".format(full_path_AlnFile)
                        self.logger.info('AlnFile detected for: {}'.format(ts))
                    else:
                        self.logger.warning('AlnFile is not detected for: {}'.format(ts))
                header = read_header(full_ts_path)

                cmd_6 = "-VolZ {} -OutBin {} -TiltAxis {} -OutImod {} -FlipVol {} {} -PixSize {} > {}/{}.log".format(self.d['VolZ'],\
                        self.d['OutBin'], self.d['TiltAxis'], self.d['OutImod'], self.d['FlipVol'],\
                        self.d['aretomo_addtional_param'], header['apix'], self.processed_folder, tomoName)

                cmd = "{} {} {} {} {} {}".format(cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6)
                print(cmd)
                subprocess.check_output(cmd, shell=True)

                if check_output(self.processed_folder, ts=ts, tomoName=tomoName) >= 0:
                    self.logger.info('Done AreTomo on GPU {}: {}'.format(gpu_ID[0], ts))
                else:
                    self.logger.error('Failed AreTomo on GPU {}: {}'.format(gpu_ID[0], ts))
        elif batch_size > 1:
            pass
    
    def stop_process(self):

        self.terminate()
        self.quit()
        self.wait()