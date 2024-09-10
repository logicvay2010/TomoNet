import os, logging, json
# import mrcfile
# import numpy as np

# from scipy.ndimage.filters import gaussian_filter
# from skimage.transform import resize

from PyQt5.QtCore import QThread, QProcess

from TomoNet.util.metadata import MetaData, Label
from TomoNet.util.dict2attr import idx2list
# from TomoNet.util.filter import maxmask, stdmask

class MaskGeneration(QThread):

    def __init__(self, d):
        super().__init__()
        self.d = d
        self.p = None

        self.mask_folder = d['mask_folder']
        self.tomogram_star = d['tomogram_star'] 
        self.tomo_idx = d['tomo_idx']
        self.patch_size_mask = d['patch_size_mask']
        self.zAxis_crop_mask = d['zAxis_crop_mask']
        self.use_deconv_mask = d['use_deconv_mask']

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
        self.logger.info('\n##################IsoNet starts generating mask##################\n')
        try:
            if not os.path.isdir(self.mask_folder):
                os.mkdir(self.mask_folder)
            # write star percentile threshold
            md = MetaData()
            md.read(self.tomogram_star)
            if not 'rlnMaskDensityPercentage' in md.getLabels():
                md.addLabels('rlnMaskDensityPercentage','rlnMaskStdPercentage','rlnMaskName')
                for it in md:
                    md._setItemValue(it,Label('rlnMaskDensityPercentage'),50)
                    md._setItemValue(it,Label('rlnMaskStdPercentage'),50)
                    md._setItemValue(it,Label('rlnMaskName'),None)

            tomo_idx = idx2list(self.tomo_idx)
            
            for it in md:
                if tomo_idx is None or str(it.rlnIndex) in tomo_idx:
                    if self.use_deconv_mask == 1:
                        if "rlnDeconvTomoName" in md.getLabels() and it.rlnDeconvTomoName not in [None,'None']:
                            tomo_file = it.rlnDeconvTomoName
                        else:
                            tomo_file = it.rlnMicrographName
                            self.logger.warning('use deconv tomo checked, but the deconvoled map for tomo #{} was not detected. Use original map instead.'.format(it.rlnIndex))
                    else:
                        tomo_file = it.rlnMicrographName
                    
                    tomo_root_name = os.path.splitext(os.path.basename(tomo_file))[0]
                    if os.path.isfile(tomo_file):
                        self.logger.info('Input map: {} | Mask save to: {} | Density%: {} | STD%: {} | Patch size: {}'.format(os.path.basename(tomo_file),
                        self.mask_folder, it.rlnMaskDensityPercentage, it.rlnMaskStdPercentage, self.patch_size_mask))                        
                        
                        #if mask_boundary is None:
                        if "rlnMaskBoundary" in md.getLabels() and it.rlnMaskBoundary not in [None, "None"]:
                            mask_boundary = it.rlnMaskBoundary 
                            self.logger.info('mask boundary is used for tomo #{}.'.format(it.rlnIndex))
                        else:
                            mask_boundary = None
                              
                        mask_out_name = '{}/{}_mask.mrc'.format(self.mask_folder, tomo_root_name)

                        try:
                            temp_mask_param_file = self.generate_mask_json(tomo_file,
                                                                        mask_out_name, 
                                                                        mask_boundary, 
                                                                        self.patch_size_mask, 
                                                                        it.rlnMaskDensityPercentage,
                                                                        it.rlnMaskStdPercentage,
                                                                        self.zAxis_crop_mask,
                                                                        self.mask_folder)
                            cmd = "mask_one.py {}".format(temp_mask_param_file)
                            self.logger.info("Running mask generation command: {}".format(cmd))
                            self.p = QProcess()
                            self.p.start(cmd)
                            res = self.p.waitForFinished(60000*30)
                            
                            try:
                                self.p.terminate()
                                #self.p.kill() 
                            except:
                                pass
                            self.p = None

                        except Exception as err:
                            self.logger.error(f"Unexpected {err=}, {type(err)=}")
                        # try:
                        #     os.remove(temp_mask_param_file)
                        # except:
                        #     pass

                        # self.make_mask_one(tomo_file,
                        #                 mask_out_name, 
                        #                 mask_boundary = mask_boundary, 
                        #                 side = self.patch_size_mask, 
                        #                 density_percentage = it.rlnMaskDensityPercentage,
                        #                 std_percentage = it.rlnMaskStdPercentage,
                        #                 surface = self.zAxis_crop_mask)
                        if res:
                            md._setItemValue(it,Label('rlnMaskName'), mask_out_name)
                            self.logger.info('##################Isonet done generating mask for tomo # {}##################\n'.format(it.rlnIndex))
                        
                            md.write(self.tomogram_star)
                    else:
                        self.logger.warning("input file {} does not exist, please double check it. Skip mask generation for this one.".format(tomo_file))
                        continue
        except Exception as err:
            self.logger.error(f"Unexpected {err=}, {type(err)=}")
            return

    def generate_mask_json(self, tomo_file, mask_out_name, mask_boundary, side, 
                            density_percentage, std_percentage, surface, mask_dir):
        d = {}
        d['tomo_file'] = tomo_file
        d['mask_out_name'] = mask_out_name
        d['mask_boundary'] = mask_boundary
        d['side'] = side
        d['density_percentage'] = density_percentage
        d['std_percentage'] = std_percentage
        d['surface'] = surface        
        
        temp_file = "{}/temp_param_deconv.json".format(mask_dir)

        with open(temp_file, 'w') as fp:
            json.dump(d, fp, indent=2, default=int)
        
        return temp_file

    # def make_mask_one(self, tomo_path, mask_name, mask_boundary = None, side = 5, density_percentage=50.0, std_percentage=50.0, surface=None):
        
    #     with mrcfile.open(tomo_path, permissive=True) as n:
    #         header_input = n.header
    #         pixel_size = n.voxel_size
    #         tomo = n.data.astype(np.float32)
    #     sp=np.array(tomo.shape)
    #     sp2 = sp//2
    #     bintomo = resize(tomo,sp2,anti_aliasing=True)
    
    #     gauss = gaussian_filter(bintomo, side/2)
    #     if density_percentage <=99.8:
    #         mask1 = maxmask(gauss,side=side, percentile=density_percentage)
    #     else:
    #         mask1 = np.ones(sp2)

    #     if std_percentage <=99.8:
    #         mask2 = stdmask(gauss,side=side, threshold=std_percentage)
    #     else:
    #         mask2 = np.ones(sp2)

    #     out_mask_bin = np.multiply(mask1,mask2)
    
    #     if mask_boundary is not None:
    #         from TomoNet.util.filter import boundary_mask
    #         mask3 = boundary_mask(bintomo, mask_boundary, logger=self.logger)
    #         out_mask_bin = np.multiply(out_mask_bin, mask3)

    #     if (surface is not None) and surface < 1:
    #         for i in range(int(surface*sp2[0])):
    #             out_mask_bin[i] = 0
    #         for i in range(int((1-surface)*sp2[0]),sp2[0]):
    #             out_mask_bin[i] = 0

    #     out_mask = np.zeros(sp)
    #     out_mask[0:-1:2,0:-1:2,0:-1:2] = out_mask_bin
    #     out_mask[0:-1:2,0:-1:2,1::2] = out_mask_bin
    #     out_mask[0:-1:2,1::2,0:-1:2] = out_mask_bin
    #     out_mask[0:-1:2,1::2,1::2] = out_mask_bin
    #     out_mask[1::2,0:-1:2,0:-1:2] = out_mask_bin
    #     out_mask[1::2,0:-1:2,1::2] = out_mask_bin
    #     out_mask[1::2,1::2,0:-1:2] = out_mask_bin
    #     out_mask[1::2,1::2,1::2] = out_mask_bin
    #     out_mask = (out_mask>0.5).astype(np.uint8)

    #     with mrcfile.new(mask_name,overwrite=True) as n:
    #         n.set_data(out_mask)

    #         n.header.extra2 = header_input.extra2
    #         n.header.origin = header_input.origin
    #         n.header.nversion = header_input.nversion
    #         n.voxel_size = pixel_size
    
    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()
    
    def kill_process(self):
        self.p.kill()
        self.p.terminate()
        #self.p.kill() 