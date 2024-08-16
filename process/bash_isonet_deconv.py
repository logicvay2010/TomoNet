import os
import logging
from PyQt5.QtCore import QThread

from TomoNet.util.metadata import MetaData, Label
from TomoNet.process.deconvolution import deconv_one
from TomoNet.util.dict2attr import idx2list

class Deconvolve(QThread):

    def __init__(self, d):
        super().__init__()
        self.d = d

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
            self.logger.info("########Processing Ctf Deconvolution for {} Tomogram(s)########".format(len(tomo_idx)))
        else:
            self.logger.info("########Processing Ctf Deconvolution for {} Tomogram(s)########".format(len(self.md)))
        
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
                    deconv_one(it.rlnMicrographName, deconv_tomo_name, self.isonet_folder, voltage=self.voltage, cs=self.cs, defocus=it.rlnDefocus/10000.0, \
                            pixel_size=it.rlnPixelSize, snrfalloff=it.rlnSnrFalloff, deconvstrength=it.rlnDeconvStrength, \
                                highpassnyquist=self.highpassnyquist, chunk_size=self.chunk_size, overlap_rate=self.overlap_rate, ncpu=self.ncpu, logger=self.logger)
                except Exception as err:
                    self.logger.error(f"Unexpected {err=}, {type(err)=}")
                
                self.md._setItemValue(it, Label('rlnDeconvTomoName'), deconv_tomo_name)
                
                self.md.write(self.tomogram_star)
        
        self.logger.info('######Isonet done ctf deconvolve######\n')

    def stop_process(self):
        self.quit()
        self.terminate()
        self.wait()