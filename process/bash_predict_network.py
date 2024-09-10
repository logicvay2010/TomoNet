import os, logging, subprocess, json
import glob
from PyQt5.QtCore import QThread, QProcess

class Predict_network(QThread):

    def __init__(self, d):
        super().__init__()
        self.d = d
        self.log_file = "Autopick/autopick.log"
        self.p = None
        self.d['log_to_terminal'] = False
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def run(self):
        tomo_list = self.get_tomo_list(self.d['input_folder_predict'])
        mask_list = []

        for tomo in tomo_list:
            if tomo.endswith(".mrc"):
                prefix = tomo.split(".mrc")[0]
                #suffix = ".mrc"
            else:
                prefix = tomo.split(".rec")[0]
                #suffix = ".rec"

            mask_file_mrc = "{}_mask{}".format(prefix, ".mrc")
            mask_file_rec = "{}_mask{}".format(prefix, ".rec")
            if os.path.exists(mask_file_mrc):
                mask_list.append(mask_file_mrc)
            elif os.path.exists(mask_file_rec):
                mask_list.append(mask_file_rec)
            else:
                mask_list.append(None)
        input_model = self.d['input_model']
        result_path = os.path.dirname(input_model)
        if result_path == "":
            result_path = os.getcwd()
        predict_result_path = "{}/predict_result_box@{}_unitSize@{}_minPatch@{}_labelSize@{}_tol@{}_olSize@{}".format(result_path, \
            self.d['box_size_predict'], self.d['unit_size_predict'], self.d['min_patch_size_predict'],self.d['y_label_size_predict'],self.d['tolerance'],self.d['margin'])
        self.d['predict_result_path'] = predict_result_path 
        
        self.logger.info("######## Start Predicting! Total tomo # is {} ########".format(len(tomo_list)))

        for i, tomo in enumerate(tomo_list):
            #margin = self.d['margin']
            self.d['current_tomo'] = tomo
            self.d['current_mask'] = mask_list[i]
            
            current_pred_param_file = "{}/predict_params.json".format(result_path)

            with open(current_pred_param_file, 'w') as fp:
                json.dump(self.d, fp, indent=2, default=int)   
            
            cmd = "predict_tomo_picking_ts.py {}".format(current_pred_param_file)
            # cmd = "predict_tomo_picking_ts.py {} {} {} {} {} {} {} {} {} {} {} {}".\
            #     format(tomo, predict_result_path, input_model, self.d['box_size_predict'], self.d['box_size_predict']-margin,\
            #     mask_list[i], self.d['unit_size_predict'], self.d['min_patch_size_predict'], self.d['y_label_size_predict'], self.d['tolerance'], self.d['save_seg_map'], self.log_file)
            if self.d['checkBox_print_only_predict_network']:
                # cmd = "predict_tomo_picking_ts.py {} {} {} {} {} {} {} {} {} {} {}".\
                #     format(tomo, predict_result_path, input_model, self.d['box_size_predict'], self.d['box_size_predict']-margin,\
                #     mask_list[i], self.d['unit_size_predict'], self.d['min_patch_size_predict'], self.d['y_label_size_predict'], self.d['tolerance'], self.d['save_seg_map'])
                self.logger.info("########cmd for network predicting: {}########".format(os.path.basename(tomo)))
                self.logger.info(cmd)
            else:

                self.p = QProcess()
                self.p.start(cmd)
                #self.logger.info("PID {}".format(self.p.pid()))
                res = self.p.waitForFinished(8.64e7)

                try:
                    self.p.terminate() 
                except:
                    pass
                self.p = None
                #subprocess.run(cmd, shell=True, encoding="utf-8", stdout=open(self.log_file, 'a'))
        
                # with open("{}/param.json".format(predict_result_path), 'w') as fp:
                #     json.dump(self.d, fp, indent=2, default=int)        
        
    def get_tomo_list(self, folder):
        rec_files = set(glob.glob("{}/*.rec".format(folder)))
        tomo_files = set(glob.glob("{}/*.mrc".format(folder)))
        tomo_files.update(rec_files)
        tomo_files = list(tomo_files)
        tomo_files_filtered = []
        for tomo in tomo_files:
            if "mask" not in tomo:
                tomo_files_filtered.append(tomo)
        return sorted(tomo_files_filtered)

    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()

    def kill_process(self):
        self.p.kill()
        self.p.terminate()