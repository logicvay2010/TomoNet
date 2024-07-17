import os
import subprocess
import re
import logging
import torch
import shutil
from multiprocessing import Pool
from TomoNet.util.io import mkfolder_ifnotexist

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

def fix_format_aretomo(aretomo_folder, tomoName, tiltAxis, correct_ImodFile_format):
    folder_imod_correct = "{}/{}".format(aretomo_folder, tomoName)
    tlt_file = "{}/{}.tlt".format(folder_imod_correct, tomoName)
    tlt_tmp_file = "{}/{}_tmp.tlt".format(folder_imod_correct, tomoName)

    #remove last empty line in .tlt file
    with open(tlt_file, 'r') as f:
        lines = f.readlines()
        with open(tlt_tmp_file, 'w') as w:
            for line in lines:
                if len(line.strip()) > 0:
                    w.write(line)
    os.replace(tlt_tmp_file, tlt_file)
        
    if correct_ImodFile_format == 1:
        tilt_com_file = "{}/tilt.com".format(folder_imod_correct)
        tilt_com_tmp_file = "{}/tilt_tmp.com".format(folder_imod_correct)
        with open(tilt_com_file, 'r') as f:
            lines = f.readlines()
            with open(tilt_com_tmp_file, 'w') as w:
                for line in lines:
                    if "EXCLUDELIST" in line:
                        skipped_views = ','.join([str(int(x) + 1) for x in line.split('EXCLUDELIST')[-1].strip().replace(' ','').split(',')])
                        new_line = "EXCLUDELIST {}\n".format(skipped_views)
                        w.write(new_line)
                    elif "EXCLUDELIST2" in line:
                        skipped_views = ','.join([str(int(x) + 1) for x in line.split('EXCLUDELIST2')[-1].strip().replace(' ','').split(',')])
                        new_line = "EXCLUDELIST2 {}\n".format(skipped_views)
                        w.write(new_line)
                    elif "FULLIMAGE" in line:
                        seg = line.split()
                        if abs(tiltAxis) > 60 and abs(tiltAxis) < 120:
                            new_line = "{} {} {}\n".format(seg[0], seg[2], seg[1])
                        else:
                            new_line = line
                        w.write(new_line)
                    else:
                        w.write(line)
        os.replace(tilt_com_tmp_file, tilt_com_file)

def aretomo_single(param):
    cmd = param['cmd']
    generate_odd_even_aretomo = param['generate_odd_even_aretomo']
    processed_folder = param['processed_folder']
    ts = param['ts']
    tomoName = param['tomoName']
    gpu_ID = param['gpu_ID']
    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as err:
        param['logger'].error('AreTomo reconstruction failed on GPU {} for tomo: {}. Please check {}.log for details if needed.'.format(param['gpu_ID'], param['tomoName'], param['tomoName']))
        param['logger'].error(f"Unexpected {err=}, {type(err)=}")
        return -1
    
    if check_output(processed_folder, ts=ts, tomoName=tomoName) >= 0:
        try:
            fix_format_aretomo(processed_folder, tomoName, param['TiltAxis'], param['correct_ImodFile_format'])
        except Exception as err:
            param['logger'].error(f"Unexpected {err=}, {type(err)=}")
        
        param['logger'].info('Done AreTomo on GPU {}: {}'.format(gpu_ID, ts))
    else:
        param['logger'].error('Failed AreTomo on GPU {}: {}'.format(gpu_ID, ts))
    
    if generate_odd_even_aretomo == 1:
        path_ODD_st = "{}/ODD/{}_ODD.st".format(param['aretomo_input_folder'], tomoName)
        path_EVN_st = "{}/EVN/{}_EVN.st".format(param['aretomo_input_folder'], tomoName)
        if os.path.exists(path_ODD_st) and os.path.exists(path_EVN_st):
            mkfolder_ifnotexist("{}/{}/ODD".format(processed_folder, tomoName))
            cmd_2 = "-InMrc {}".format(path_ODD_st)
            output_path = "{}/{}/ODD/{}_ODD.rec".format(processed_folder, tomoName, tomoName) 
            cmd_3 = "-OutMrc {}".format(output_path)

            full_path_AlnFile = "{}/{}/{}.aln".format(processed_folder, tomoName, tomoName)
            #full_path_AlnFile_2 = "{}/{}.aln".format(processed_folder, ts)
            #full_path_AlnFile = full_path_AlnFile_1 if os.path.exists(full_path_AlnFile_1) else full_path_AlnFile_2
            if os.path.exists(full_path_AlnFile):
                cmd_5 = "-AlnFile {}".format(full_path_AlnFile)
            else:
                param['logger'].warning('AlnFile is not detected for ODD Recon of {}'.format(tomoName))
                cmd_5 = ""
            cmd_7_ODD = param['cmd_list'][6].replace("{}.log".format(tomoName), "{}/ODD/{}_ODD.log".format(tomoName, tomoName))
            cmd_7_ODD = cmd_7_ODD.replace("-OutImod 1", "-OutImod 0")
            cmd_7_ODD = cmd_7_ODD.replace("-OutImod 2", "-OutImod 0")
            cmd_7_ODD = cmd_7_ODD.replace("-OutImod 3", "-OutImod 0")
            cmd_ODD = "{} {} {} {} {} {} {}".format(param['cmd_list'][0], cmd_2, cmd_3, param['cmd_list'][3], cmd_5, param['cmd_list'][5], cmd_7_ODD)
            
            #param['logger'].info(cmd_ODD)
            subprocess.check_output(cmd_ODD, shell=True)

            mkfolder_ifnotexist("{}/{}/EVN".format(processed_folder, tomoName))
            cmd_2 = "-InMrc {}".format(path_EVN_st)
            output_path = "{}/{}/EVN/{}_EVN.rec".format(processed_folder, tomoName, tomoName) 
            cmd_3 = "-OutMrc {}".format(output_path)

            #full_path_AlnFile_1 = "{}/{}/{}.aln".format(processed_folder, tomoName, tomoName)
            #full_path_AlnFile_2 = "{}/{}.aln".format(processed_folder, ts)
            #full_path_AlnFile = full_path_AlnFile_1 if os.path.exists(full_path_AlnFile_1) else full_path_AlnFile_2
            if os.path.exists(full_path_AlnFile):
                cmd_5 = "-AlnFile {}".format(full_path_AlnFile)
                #param['logger'].info('AlnFile detected for: {}'.format(ts))
            else:
                param['logger'].warning('AlnFile is not detected for EVN Recon of {}'.format(tomoName))
                cmd_5 = ""
            cmd_7_EVN = param['cmd_list'][6].replace("{}.log".format(tomoName), "{}/EVN/{}_EVN.log".format(tomoName, tomoName))
            cmd_7_EVN = cmd_7_EVN.replace("-OutImod 1", "-OutImod 0")
            cmd_7_EVN = cmd_7_EVN.replace("-OutImod 2", "-OutImod 0")
            cmd_7_EVN = cmd_7_EVN.replace("-OutImod 3", "-OutImod 0")
            cmd_EVN = "{} {} {} {} {} {} {}".format(param['cmd_list'][0], cmd_2, cmd_3, param['cmd_list'][3], cmd_5, param['cmd_list'][5], cmd_7_EVN)
            
            #param['logger'].info(cmd_EVN)
            subprocess.check_output(cmd_EVN, shell=True)

            param['logger'].info('Done processing ODD and EVN reconstruction on GPU {} for tomo: {}'.format(gpu_ID, tomoName))

        else:
            param['logger'].warning('ODD and/or EVN TS are not detected under sub-folder ODD and EVN for tomo: {}. Skip it!'.format(tomoName))

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
        cmd_1 = self.d['aretomo_name']

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
                
                if self.d['pixelSize_aretomo'] == -1:
                    header = read_header(full_ts_path)
                    apix = header['apix']
                else:
                    apix = self.d['pixelSize_aretomo']

                cmd_6 = "-Gpu {}".format(gpu_ID[0])

                cmd_7 = "-VolZ {} -OutBin {} -TiltAxis {} -OutImod {} -FlipVol {} {} -PixSize {} > {}/{}.log".format(self.d['VolZ'],\
                        self.d['OutBin'], self.d['TiltAxis'], self.d['OutImod'], self.d['FlipVol'],\
                        self.d['aretomo_addtional_param'], apix, self.processed_folder, tomoName)

                cmd = "{} {} {} {} {} {} {}".format(cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6, cmd_7)
                param = {}
                param['cmd'] = cmd
                param['cmd_list'] = [cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6, cmd_7]
                param['TiltAxis'] = self.d['TiltAxis']
                param['aretomo_input_folder'] = self.d['aretomo_input_folder']
                param['generate_odd_even_aretomo'] = self.d['generate_odd_even_aretomo']
                param['correct_ImodFile_format'] = self.d['correct_ImodFile_format']
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

                    if self.d['pixelSize_aretomo'] == -1:
                        header = read_header(full_ts_path)
                        apix = header['apix']
                    else:
                        apix = self.d['pixelSize_aretomo']

                    cmd_7 = "-VolZ {} -OutBin {} -TiltAxis {} -OutImod {} -FlipVol {} {} -PixSize {} > {}/{}.log".format(self.d['VolZ'],\
                            self.d['OutBin'], self.d['TiltAxis'], self.d['OutImod'], self.d['FlipVol'],\
                            self.d['aretomo_addtional_param'], apix, self.processed_folder, tomoName)

                    cmd = "{} {} {} {} {} {} {}".format(cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6, cmd_7)

                    param['cmd'] = cmd
                    param['cmd_list'] = [cmd_1, cmd_2, cmd_3, cmd_4, cmd_5, cmd_6, cmd_7]
                    param['TiltAxis'] = self.d['TiltAxis']
                    param['generate_odd_even_aretomo'] = self.d['generate_odd_even_aretomo']
                    param['aretomo_input_folder'] = self.d['aretomo_input_folder']
                    param['correct_ImodFile_format'] = self.d['correct_ImodFile_format']
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