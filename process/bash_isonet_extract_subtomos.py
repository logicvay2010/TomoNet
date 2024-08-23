import os
import time
import logging
import mrcfile
import numpy as np
from PyQt5.QtCore import QThread

from TomoNet.util.dict2attr import idx2list

from TomoNet.util.io import mkfolder

from TomoNet.util.metadata import MetaData, Label, Item

from TomoNet.preprocessing.cubes import create_cube_seeds, crop_cubes

#from TomoNet.preprocessing.prepare import extract_subtomos


def mw2d(dim,missingAngle=[30,30]):
    mw=np.zeros((dim,dim),dtype=np.double)
    missingAngle = np.array(missingAngle)
    missing=np.pi/180*(90-missingAngle)
    for i in range(dim):
        for j in range(dim):
            y=(i-dim/2)
            x=(j-dim/2)
            if x==0:# and y!=0:
                theta=np.pi/2
            #elif x==0 and y==0:
            #    theta=0
            #elif x!=0 and y==0:
            #    theta=np.pi/2
            else:
                theta=abs(np.arctan(y/x))

            if x**2+y**2<=min(dim/2,dim/2)**2:
                if x > 0 and y > 0 and theta < missing[0]:
                    mw[i,j]=1#np.cos(theta)
                if x < 0 and y < 0 and theta < missing[0]:
                    mw[i,j]=1#np.cos(theta)
                if x > 0 and y < 0 and theta < missing[1]:
                    mw[i,j]=1#np.cos(theta)
                if x < 0 and y > 0 and theta < missing[1]:
                    mw[i,j]=1#np.cos(theta)

            if int(y) == 0:
                mw[i,j]=1
    #from mwr.util.image import norm_save
    #norm_save('mw.tif',self._mw)
    return mw

def apply_wedge(ori_data, missingAngle, ld1 = 1, ld2 = 0):

    data = np.rot90(ori_data, k=1, axes=(0,1)) #clock wise of counter clockwise??
    mw = mw2d(data.shape[1], missingAngle)

    #if inverse:
    #    mw = 1-mw
    mw = mw * ld1 + (1-mw) * ld2

    outData = np.zeros(data.shape,dtype=np.float32)
    mw_shifted = np.fft.fftshift(mw)
    for i, item in enumerate(data):
        outData_i=np.fft.ifft2(mw_shifted * np.fft.fft2(item))
        outData[i] = np.real(outData_i)

    outData.astype(np.float32)
    outData=np.rot90(outData, k=3, axes=(0,1))

    return outData

def split_data(data_dir):    
    # hyper-parameters
    batch_size = 4
    ratio = 0.1
    
    #assigning classes
    all_path_x = os.listdir(data_dir+'/train_x')
    num_test = int(len(all_path_x) * ratio) 
    num_test = num_test - num_test%batch_size + batch_size
    all_path_y = [i.split('_x_')[0]+'_y_'+i.split('_x_')[1] for i in all_path_x ]

    #organizing based on distribution
    ind = np.random.permutation(len(all_path_x))[0:num_test]
    for i in ind:
        os.rename('{}/train_x/{}'.format(data_dir, all_path_x[i]), '{}/test_x/{}'.format(data_dir, all_path_x[i]) )
        os.rename('{}/train_y/{}'.format(data_dir, all_path_y[i]), '{}/test_y/{}'.format(data_dir, all_path_y[i]) )

class ExtractSubtomos(QThread):

    def __init__(self, d):
        super().__init__()
        self.d = d

        self.tomogram_star = d['tomogram_star']
        
        self.subtomo_folder = d['subtomo_dir']
        self.subtomo_star = d['subtomo_star_file']

        self.cube_size = d['subtomo_cube_size']
        self.crop_size = self.cube_size + 16
        self.tomo_index_subtomo =  d['tomo_index_subtomo']
        self.use_deconv_subtomo = d['use_deconv_subtomo']

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
        
        start_time = time.time()
        self.logger.info("\n##################Isonet starts extracting subtomograms##################\n")
        
        md = MetaData()
        md.read(self.tomogram_star)
        
        mkfolder(self.subtomo_folder)
        # if not os.path.isdir(self.subtomo_folder):
        #     os.mkdir(self.subtomo_folder)


        # dirs_tomake = ['train_x','train_y', 'test_x', 'test_y']

        # for dir in dirs_tomake:
        #     folder = '{}/{}'.format(self.subtomo_folder, dir)
        #     if not os.path.exists(folder):
        #         os.makedirs(folder)

        tomo_idx = idx2list(self.tomo_index_subtomo)

        subtomo_md = MetaData()
        subtomo_md.addLabels('rlnSubtomoIndex','rlnImageName','rlnCubeSize','rlnCropSize','rlnPixelSize')

        count = 0
        for it in md:
            if tomo_idx is None or str(it.rlnIndex) in tomo_idx:
                if self.use_deconv_subtomo == 1:
                    if "rlnDeconvTomoName" in md.getLabels() and it.rlnDeconvTomoName not in [None,'None']:
                        tomo_file = it.rlnDeconvTomoName
                    else:
                        tomo_file = it.rlnMicrographName
                        self.logger.warning('use deconved tomo checked, but the deconvoled map for tomo #{} was not detected. Use original map instead.'.format(it.rlnIndex))
                else:
                    tomo_file = it.rlnMicrographName
                
                pixel_size = it.rlnPixelSize
                
                self.logger.info("Extracting from tomogram {}".format(tomo_file))
                with mrcfile.open(tomo_file, permissive=True) as mrcData:
                    orig_data = mrcData.data.astype(np.float32)

                #tomo_root_name = os.path.splitext(os.path.basename(tomo_file))[0]
                #self.logger.info(tomo_root_name)
                
                if os.path.isfile(tomo_file):  
                    #if mask is None:
                    if "rlnMaskName" in md.getLabels() and it.rlnMaskName not in [None, "None"]:
                        with mrcfile.open(it.rlnMaskName, permissive=True) as m:
                            mask_data = m.data
                        self.logger.info('mask is been used for tomogram #{}.'.format(it.rlnIndex))
                    else:
                        mask_data = None
                        self.logger.info(" mask is not been used for tomogram #{}!".format(it.rlnIndex))

                    seeds = create_cube_seeds(orig_data, it.rlnNumberSubtomo, self.crop_size, mask=mask_data)
                    subtomos = crop_cubes(orig_data, seeds, self.crop_size)

                    # save sampled subtomo to {results_dir}/subtomos instead of subtomo_dir (as previously does)
                    base_name = os.path.splitext(os.path.basename(it.rlnMicrographName))[0]
                    
                    for j, s in enumerate(subtomos):
                        im_name_x = '{}/{}_{:0>6d}.mrc'.format(self.subtomo_folder, base_name, j+1)
                        #im_name_x = '{}/{}/{}_x_{}.mrc'.format(self.subtomo_folder, dirs_tomake[0], base_name, j)

                        with mrcfile.new(im_name_x, overwrite=True) as output_mrc:
                            count += 1
                            subtomo_it = Item()
                            subtomo_md.addItem(subtomo_it)
                            subtomo_md._setItemValue(subtomo_it,Label('rlnSubtomoIndex'), str(count))
                            subtomo_md._setItemValue(subtomo_it,Label('rlnImageName'), im_name_x)
                            subtomo_md._setItemValue(subtomo_it,Label('rlnCubeSize'), self.cube_size)
                            subtomo_md._setItemValue(subtomo_it,Label('rlnCropSize'), self.crop_size)
                            subtomo_md._setItemValue(subtomo_it,Label('rlnPixelSize'), pixel_size)
                            
                            output_mrc.set_data(s.astype(np.float32))
                else:
                    self.logger.warning('Tomogram map {} was not detected.'.format(tomo_file))
                
        subtomo_md.write(self.subtomo_star)

        self.logger.info( "Extraction Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))

        #split_data(self.subtomo_folder)
    
    def stop_process(self):
        self.quit()
        self.terminate()
        self.wait()