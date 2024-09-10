
import os, json, logging #subprocess
import glob 

from PyQt5.QtCore import QThread, QProcess

from TomoNet.util.utils import natural_keys
from TomoNet.util.io import mkfolder_ifnotexist

class Train_network(QThread):
    def __init__(self, d):
        super().__init__()
        self.d = d
        self.log_file = "Autopick/autopick.log"
        self.p = None
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

        self.d['log_to_terminal'] = False

    def run(self):
        tomo_list = self.get_tomo_list(self.d['input_folder_train'])
        if len(tomo_list) == 0:
            self.logger.error("########No tomogram was detected in folder {}########".format(self.d['input_folder_train']))
            return 
        
        mkfolder_ifnotexist(self.d['result_folder_train'])
        
        self.d['tomo_list'] = tomo_list

        param_file = "{}/train_params.json".format(self.d['result_folder_train'])
        with open(param_file, 'w') as fp:
                json.dump(self.d, fp, indent=2, default=int)
        
        # cmd = "extraction_ts.py {} {} {} {} {} {} {} {} {}".format(\
        #     self.d['input_folder_train'], ",".join(tomo_list), \
        #     self.d['result_folder_train'], self.d['continue_from_model'], \
        #     self.d['label_size'], self.d['subtomo_num'], \
        #     self.d['subtomo_box_size'], self.d['coords_scale'], self.log_file)
        
        cmd = "extraction_ts.py {}".format(param_file)

        if self.d['checkBox_print_only_train_network']:
            # cmd = "extraction_ts.py {} {} {} {} {} {} {} {}".format(\
            #     self.d['input_folder_train'], ",".join(tomo_list), \
            #     self.d['result_folder_train'], self.d['continue_from_model'], self.d['label_size'],\
            #     self.d['subtomo_num'],  self.d['subtomo_box_size'], self.d['coords_scale'])
            self.logger.info("########cmd for subtomogram extraction:########")
            self.logger.info("If you prefer to output log info in the terminal, please edit the {} file to change the log_to_terminal variable to 'true' before runing the following command".format(param_file))
            self.logger.info(cmd)
        else:
            self.p = QProcess()
            self.p.start(cmd)
            #self.logger.info("PID {}".format(self.p.pid()))
            res = self.p.waitForFinished(8.64e7*3)
            #subprocess.run(cmd, shell=True, encoding="utf-8", stdout=subprocess.PIPE)
            
            # with open("{}/train_params.json".format(self.d['result_folder_train']), 'w') as fp:
            #     json.dump(self.d, fp, indent=2, default=int)
            
            #clean process 
            try:
                self.p.terminate(8.64e7*3) 
                #self.p.close()
            except:
                pass
            self.p = None
        
        # cmd = "train_picking_ts.py {} {} {} {} {} {} {} {}".format(self.d['result_folder_train'], self.d['continue_from_model'], \
        #         self.d['epoch_num'], self.d['GPU_id'], self.d['lr'], self.d['batch_size'], self.d['steps_per_epoch'], self.log_file)
        
        cmd = "train_picking_ts.py {}".format(param_file)

        if self.d['checkBox_print_only_train_network']:
            # cmd = "train_picking_ts.py {} {} {} {} {} {} {}".format(self.d['result_folder_train'], self.d['continue_from_model'],\
            #     self.d['epoch_num'], self.d['GPU_id'],self.d['lr'], self.d['batch_size'], self.d['steps_per_epoch'])
            self.logger.info("########cmd for network training:########")
            self.logger.info("If you prefer to output log info in the terminal, please edit the {} file to change the log_to_terminal variable to 'true' before runing the following command".format(param_file))
            self.logger.info(cmd)
        else:
            #subprocess.run(cmd, shell=True, encoding="utf-8")
            self.p = QProcess()
            self.p.start(cmd)
            self.logger.info("PID {}".format(self.p.pid()))
            res = self.p.waitForFinished(86400*3)

    def get_tomo_list(self, folder):
        tomoName_mod = set([ os.path.basename(x).split(".")[0] for x in glob.glob("{}/*.mod".format(folder))])
        tomoName_coords = set([ os.path.basename(x).split(".")[0] for x in glob.glob("{}/*.coords".format(folder))])
        tomoName_pts = set([ os.path.basename(x).split(".")[0] for x in glob.glob("{}/*.pts".format(folder))])
        rec_files = set(glob.glob("{}/*.rec".format(folder)))
        tomo_files = set(glob.glob("{}/*.mrc".format(folder)))
        tomo_files.update(rec_files)
        tomoName_coords.update(tomoName_mod)
        tomoName_coords.update(tomoName_pts)
        tomoName_tomo = set([ os.path.basename(x).split(".")[0] for x in list(tomo_files)])
        intersection_tomoName = list(tomoName_coords.intersection(tomoName_tomo))
        try:
            intersection_tomoName.sort(key=natural_keys)
        except:
            pass
        return intersection_tomoName

    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()

    def kill_process(self):
        self.p.kill()
        self.p.terminate()
        