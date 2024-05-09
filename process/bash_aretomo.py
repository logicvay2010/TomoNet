import os
import subprocess
import re
import logging
import torch
import shutil
from multiprocessing import Pool

from PyQt5.QtCore import QThread

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
        rec_file = "{}/{}.rec".format(aretomo_folder, tomoName)
        proj_files = ["{}_projXZ.mrc".format(rec_file), "{}_projXY.mrc".format(rec_file)]
        folder_imod = "{}_Imod".format(rec_file)
        folder_imod_correct = "{}/{}".format(aretomo_folder, tomoName)
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

def aretomo_single(param):
    cmd = param['cmd']
    processed_folder = param['processed_folder']
    ts = param['ts']
    tomoName = param['tomoName']
    gpu_ID = param['gpu_ID']
    try:
        subprocess.check_output(cmd, shell=True)
    except:
        param['logger'].error('AreTomo reconstruction failed on GPU {} for tomo: {}. \
            Please check {}.log for details if needed.'.format(param['gpu_ID'], param['tomoName'], param['tomoName']))
        return 
    
    if check_output(processed_folder, ts=ts, tomoName=tomoName) >= 0:
        param['logger'].info('Done AreTomo on GPU {}: {}'.format(gpu_ID, ts))
    else:
        param['logger'].error('Failed AreTomo on GPU {}: {}'.format(gpu_ID, ts))

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

        self.logger.info("\n########Processing {} images on GPU {}########".format(len(self.d['current_ts_list_selected']), self.d["GPU_ID"]))
        self.logger.info("\n########The results will be saved in {}########".format(self.processed_folder))
        cmd_1 = "AreTomo"

        batch_size = len(gpu_ID)

        if batch_size == 1:
            for ts in self.d['current_ts_list_selected']:
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

                cmd_6 = "-Gpu {}".format(gpu_ID[0])

                cmd_7 = "-VolZ {} -OutBin {} -TiltAxis {} -OutImod {} -FlipVol {} {} -PixSize {} > {}/{}.log".format(self.d['VolZ'],\
                        self.d['OutBin'], self.d['TiltAxis'], self.d['OutImod'], self.d['FlipVol'],\
                        self.d['aretomo_addtional_param'], header['apix'], self.processed_folder, tomoName)

                cmd = "{} {} {} {} {} {} {}".format(cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6, cmd_7)
                param = {}
                param['cmd'] = cmd
                param['processed_folder'] = self.processed_folder
                param['ts'] = ts
                param['tomoName'] = tomoName
                param['gpu_ID'] = gpu_ID[0]
                param['logger'] = self.logger

                aretomo_single(param)

        elif batch_size > 1:
            ts_todo_list = self.d['current_ts_list_selected']
            while len(ts_todo_list) > 0:
                params = []
                current_ts = []
                s = min(len(ts_todo_list), batch_size)
                for i, ts in enumerate(ts_todo_list[:s]):
                    param = {}
                    tomoName = ts.split(".st")[0] 
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

                    cmd_6 = "-Gpu {}".format(gpu_ID[i])

                    cmd_7 = "-VolZ {} -OutBin {} -TiltAxis {} -OutImod {} -FlipVol {} {} -PixSize {} > {}/{}.log".format(self.d['VolZ'],\
                            self.d['OutBin'], self.d['TiltAxis'], self.d['OutImod'], self.d['FlipVol'],\
                            self.d['aretomo_addtional_param'], header['apix'], self.processed_folder, tomoName)

                    cmd = "{} {} {} {} {} {} {}".format(cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6, cmd_7)

                    param['cmd'] = cmd
                    param['gpu_ID'] = gpu_ID[i]
                    param['processed_folder'] = self.processed_folder
                    param['ts'] = ts
                    param['tomoName'] = tomoName
                    param['logger'] = self.logger

                    params.append(param)
                    current_ts.append(ts)

                with Pool(s) as pool:
                    pool.map(aretomo_single, params)

                ts_todo_list = ts_todo_list[batch_size:]
                if len(ts_todo_list) > 0:
                    self.logger.info('{} AreTomo Reconstructions remains to do.'.format(len(ts_todo_list)))  
                else:
                    self.logger.info('AreTomo Reconstructions all Done.')  
        
        else:
            self.logger.info('No GPU ID provided')
            return -1
    
    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()