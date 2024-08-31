import os, logging, json
from PyQt5.QtCore import QThread, QProcess

from TomoNet.util.metadata import MetaData, Label
from TomoNet.util.dict2attr import idx2list
from TomoNet.process.deconvolution import deconv_one

class Deconvolve(QThread):

    def __init__(self, d):
        super().__init__()
        self.d = d

        self.p = None

        self.tomogram_star = d['tomogram_star']
        self.deconv_folder = d['deconv_folder'] 
        self.tomo_idx = d['tomo_idx']
        self.ncpu = d['ncpu'] 
        self.highpassnyquist  = d['highpassnyquist']
        self.chunk_size = d['chunk_size']
        self.overlap_rate = d['overlap_rate'] 
        self.voltage = d['voltage'] 
        self.cs = d['cs'] 

        self.log_file = "IsoNet/isonet.log"

        self.isonet_folder = "IsoNet"
        
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def run(self):
        self.md = MetaData()
        self.md.read(self.tomogram_star)

        if not 'rlnSnrFalloff' in self.md.getLabels():
            self.md.addLabels('rlnSnrFalloff','rlnDeconvStrength','rlnDeconvTomoName')
            for it in self.md:
                self.md._setItemValue(it,Label('rlnSnrFalloff'),1.0)
                self.md._setItemValue(it,Label('rlnDeconvStrength'),1.0)
                self.md._setItemValue(it,Label('rlnDeconvTomoName'),None)
        
        if not os.path.isdir(self.deconv_folder):
            os.mkdir(self.deconv_folder)
        
        tomo_idx = idx2list(self.tomo_idx)
        if not tomo_idx is None:
            self.logger.info("\n####################Processing Ctf Deconvolution for {} Tomogram(s)####################\n".format(len(tomo_idx)))
        else:
            self.logger.info("\n####################Processing Ctf Deconvolution for {} Tomogram(s)####################\n".format(len(self.md)))
        
        self.logger.info("########The results will be saved in folder {} ########".format(self.deconv_folder))

        for it in self.md:
            if tomo_idx is None or str(it.rlnIndex) in tomo_idx:
                if it.rlnSnrFalloff is not None:
                    self.md._setItemValue(it, Label('rlnSnrFalloff'), it.rlnSnrFalloff)
                if it.rlnDeconvStrength is not None:
                    self.md._setItemValue(it, Label('rlnDeconvStrength'), it.rlnDeconvStrength)

                tomo_file = it.rlnMicrographName
                base_name = os.path.basename(tomo_file)
                deconv_tomo_name = '{}/{}'.format(self.deconv_folder, base_name)

                try:
                    temp_deconv_param_file = self.generate_deconv_json(it.rlnMicrographName, deconv_tomo_name, self.isonet_folder, \
                                self.voltage, self.cs, it.rlnDefocus/10000.0, \
                                it.rlnPixelSize, it.rlnSnrFalloff, it.rlnDeconvStrength, \
                                self.highpassnyquist, self.chunk_size, self.overlap_rate, self.ncpu,\
                                self.deconv_folder)
                    cmd = "deconv_one.py {}".format(temp_deconv_param_file)
                    self.logger.info("Running deconv command: {}".format(cmd))
                    self.p = QProcess()
                    self.p.start(cmd)
                    res = self.p.waitForFinished(86400)
                    # deconv_one(it.rlnMicrographName, deconv_tomo_name, self.isonet_folder, voltage=self.voltage, cs=self.cs, defocus=it.rlnDefocus/10000.0, \
                    #         pixel_size=it.rlnPixelSize, snrfalloff=it.rlnSnrFalloff, deconvstrength=it.rlnDeconvStrength, \
                    #             highpassnyquist=self.highpassnyquist, chunk_size=self.chunk_size, overlap_rate=self.overlap_rate, ncpu=self.ncpu, logger=self.logger)
                    try:
                        self.p.kill() 
                    except:
                        pass
                    self.p = None
                except Exception as err:
                    self.logger.error("error")
                try:
                    os.remove(temp_deconv_param_file)
                except:
                    pass
                if res:
                    self.md._setItemValue(it, Label('rlnDeconvTomoName'), deconv_tomo_name)
                
                    self.md.write(self.tomogram_star)
        
        self.logger.info('\n##################Isonet done ctf deconvolve##################\n')

    def generate_deconv_json(self, *args):
        
        d = {}
        d['tomo_name'] = args[0]
        d['deconv_tomo_name'] = args[1]
        d['isonet_folder'] = args[2] 
        d['voltage'] = args[3]
        d['cs'] = args[4]
        d['defocus'] = args[5]
        d['pixel_size'] = args[6]
        d['snrfalloff'] = args[7]
        d['deconvstrength'] = args[8]
        d['highpassnyquist'] = args[9]
        d['chunk_size'] = args[10]
        d['overlap_rate'] = args[11]
        d['ncpu'] = args[12]
        deconv_dir = args[13]
        
        temp_file = "{}/temp_param_deconv.json".format(deconv_dir)

        with open(temp_file, 'w') as fp:
            json.dump(d, fp, indent=2, default=int)
        return temp_file
    
    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()
    
    def kill_process(self):
        self.p.kill() 