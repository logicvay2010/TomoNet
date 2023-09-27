from PyQt5.QtCore import QThread
import os, glob
from multiprocessing import Pool
import subprocess
import logging

def ctffind4_single(param):
        #param = self.get_param()
        ctf_folder = param['ctf_folder']
        tomoName = param['tomoName']
        st_file = param['st_file']
        ctffind_exe = param['ctffind_exe']
        apix = param['apix']
        kv = param['voltage']
        cs = param['cs']
        amp = param['amp']
        pow_size = param['pow_size']
        min_res = param['min_res']
        max_res = param['max_res']
        min_defocus = param['min_defocus']
        max_defocus = param['max_defocus']
        search_step = param['defocus_step']
        is_astig = 'no'
        exhaustive_serach = 'no'
        res_astig = 'yes'
        exp_astig = '200'
        additional_phase = 'no'
        exp_opt= 'no'

        mrc_file = "{}.mrc".format(tomoName)
        sh_code = "#!/bin/bash\
                \n#\
                \n#   ctffind4\
                \n#\
                \ntime {} << eof > {}_ctf.log\n{}\nno\n{}_ctf.mrc\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\neof"\
                .format(ctffind_exe, tomoName, mrc_file, tomoName, apix, \
                            kv, cs, amp, pow_size, min_res, max_res, \
                        min_defocus, max_defocus,\
                        search_step, is_astig, exhaustive_serach, \
                        res_astig, exp_astig,\
                        additional_phase, exp_opt)
        
        existing_ctf = param['existing_ctf']
        history_record_file = param['history_record_file']
        overwrite = False
        logger = param['logger']
        
        if (tomoName not in existing_ctf) or overwrite:
            cmd_file_name = "{}/{}/{}_cmd.sh".format(ctf_folder, tomoName, tomoName)
            cmd_file_folder = "{}/{}".format(ctf_folder, tomoName, tomoName)
            
            
            if not os.path.exists(cmd_file_folder):
                os.mkdir(cmd_file_folder)
            
            f=open(cmd_file_name, "w", encoding="utf-8")
            f.write(sh_code)
            f.close()

            #cmd = "cd {}; exec sh {}_cmd.sh".format(cmd_file_folder, tomoName)
            cmd = "cd {}; ln -s {} {}.mrc; exec sh {}_cmd.sh".format(cmd_file_folder, st_file, tomoName, tomoName)
            #cmd2 = "cd {}".format(cmd_file_folder, tomoName)
            
            subprocess.run(cmd, shell=True, capture_output=True)
            #os.system(cmd)
            #time.sleep(5)
            logger.info("Done Ctf Estimation for {}".format(tomoName))
            try:
                with open(history_record_file, "a") as f:
                    f.write("{}\n".format(tomoName))
            except:
                logger.error("Error: unable to write file to {}.".format(history_record_file))
            
        else:
            logger.info("ctf estimation for {} exist, skip it!\nIf you want to redo it, please edit the history txt file {}."\
            .format(tomoName, history_record_file))

class Ctffind4(QThread):

    def __init__(self,d):
        super().__init__()
        self.d = d

        self._history_record = "Ctffind/history_record.txt"

        self.ts_folder = d['ts_tlt_folder']
        self.ctf_folder = "Ctffind"
        self.ctffind_exe = d['ctffind_exe']
        self.log_file = "Ctffind/ctffind.log"
        #self.proc = QProcess()
        #self.stream = StringIO()
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

        existing_ctf = []
        if os.path.exists(self._history_record):
            with open(self._history_record) as file:
                try:
                    existing_ctf = [line.strip() for line in file]
                except:
                    self.logger.warning("The history record file's format is wrong: {}".format(self._history_record))        

        tomoName_list, st_list = self.get_ts_list(self.d['ts_tlt_folder'])
                
        self.params = []
        #s = min(len(st_list), self.d['cpu_num'])
        
        #for i, st in enumerate(st_list[:s]):
        for i, st in enumerate(st_list):
            param = {}
            tomoName = tomoName_list[i]
            #cmd_2 = '{}/{} -OutMrc {}/{}_ali.mrc '.format(self.d['raw_image_folder'],image,self.corrected_folder,basename)
            #cmd_4 = '-Gpu {} -LogFile {}/{}.log > {}/{}_MotionCor2_output.log 2>&1 '\
            #    '\" > {}/{}_MotionCor2_cmd.log'.format(gpu_ID[i], self.corrected_folder, basename, self.corrected_folder,\
            #    basename, self.corrected_folder, basename)
            #cmd_5 = 'sh {}/{}_MotionCor2_cmd.log; mv {}/{} {}/'.format(self.corrected_folder, basename,\
            #self.d['raw_image_folder'], image, self.processed_folder,image)
            param = self.d.copy()
            
            param['ctf_folder'] = self.ctf_folder
            param['tomoName'] = tomoName
            param['st_file'] = st
            param['logger'] = self.logger
            param['existing_ctf'] = existing_ctf
            param['history_record_file'] = self._history_record
            self.params.append(param)

    def run(self):
        self.logger.info("########Processing Ctf Estimation for {} Tilt Series########".format(len(self.params)))
        self.logger.info("########The results will be saved in folder {} individually########".format(self.ctf_folder))
        
        self.pool = Pool(self.d['cpu_num']) 
        self.pool.map(ctffind4_single, self.params)


    def get_ts_list(self, path):
        tomoName_list1 = [os.path.basename(x).split(".")[0] for x in glob.glob("{}/*.st".format(path))]
        #tomoName_list2 = [os.path.basename(x).split(".")[0] for x in glob.glob("{}/*.rawtlt".format(path))]
        #tomoName_list = list(set(tomoName_list1) & set(tomoName_list2))
        tomoName_list = tomoName_list1
        
        st_list = ["{}/{}.st".format(path,x) for x in tomoName_list]
        #st_list2 = glob.glob("{}/*.st".format(path))

        return [tomoName_list, st_list]

    def stop_process(self):
       
        self.pool.terminate()

        self.terminate()
        self.quit()
        self.wait()