import os
import time
import logging
import mrcfile
import numpy as np
from PyQt5.QtCore import QThread

from TomoNet.util.dict2attr import idx2list

from TomoNet.util.io import mkfolder

from TomoNet.util.metadata import MetaData, Label, Item

from TomoNet.preprocessing.cubes import create_cube_seeds, crop_cubes, normalize

from scipy.ndimage import rotate

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
        self.subtomo_star_plus_x = "{}/subtomos_plus_x.star".format(self.subtomo_folder)
        self.subtomo_star_plus_y = "{}/subtomos_plus_y.star".format(self.subtomo_folder)
        self.subtomo_star_minus_x = "{}/subtomos_minus_x.star".format(self.subtomo_folder)
        self.subtomo_star_minus_y = "{}/subtomos_minus_y.star".format(self.subtomo_folder)

        self.cube_size = d['subtomo_cube_size']
        self.crop_size = self.cube_size + self.cube_size//2
        self.tomo_index_subtomo_plus = d['tomo_index_subtomo_plus']
        self.tomo_index_subtomo_minus = d['tomo_index_subtomo_minus']
        self.tilt_range = d['tilt_range']
        self.target_tilt_range = d['target_tilt_range']
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

        if not os.path.isdir(self.subtomo_folder):
            os.mkdir(self.subtomo_folder)
        plus_folder = "{}/plus".format(self.subtomo_folder)
        mkfolder(plus_folder)
        # if not os.path.isdir(plus_folder):
        #     os.mkdir(plus_folder)
        minus_folder = "{}/minus".format(self.subtomo_folder)
        mkfolder(minus_folder)
        # if not os.path.isdir(minus_folder):
        #     os.mkdir(minus_folder)

        dirs_tomake = ['train_x','train_y', 'test_x', 'test_y']

        for dir in dirs_tomake:
            folder = '{}/{}'.format(plus_folder, dir)
            if not os.path.exists(folder):
                os.makedirs(folder)
        for dir in dirs_tomake:
            folder = '{}/{}'.format(minus_folder, dir)
            if not os.path.exists(folder):
                os.makedirs(folder)

        tomo_idx_plus = idx2list(self.tomo_index_subtomo_plus)
        tomo_idx_minus = idx2list(self.tomo_index_subtomo_minus)

        # subtomo_md_x_plus = MetaData()
        # subtomo_md_x_plus.addLabels('rlnSubtomoIndex','rlnImageName','rlnCubeSize','rlnCropSize','rlnPixelSize')
        # subtomo_md_y_plus = MetaData()
        # subtomo_md_y_plus.addLabels('rlnSubtomoIndex','rlnImageName','rlnCubeSize','rlnCropSize','rlnPixelSize')
        # subtomo_md_x_minus = MetaData()
        # subtomo_md_x_minus.addLabels('rlnSubtomoIndex','rlnImageName','rlnCubeSize','rlnCropSize','rlnPixelSize')
        # subtomo_md_y_minus = MetaData()
        # subtomo_md_y_minus.addLabels('rlnSubtomoIndex','rlnImageName','rlnCubeSize','rlnCropSize','rlnPixelSize')
        
        side_len = self.cube_size//2
        
        tilt_plus = abs(self.target_tilt_range[1] - self.tilt_range[1])
        tilt_minus = abs(self.target_tilt_range[0] - self.tilt_range[0])

        missing_angle_plus = [self.tilt_range[0] + 90 + tilt_plus, 90 - self.tilt_range[1]]
        #self.logger.info("{}, {}".format(missing_angle_plus[0], missing_angle_plus[1]))
        missing_angle_minus = [self.tilt_range[0] + 90, 90 - self.tilt_range[1] + tilt_minus]
        #self.logger.info("{}, {}".format(missing_angle_minus[0], missing_angle_minus[1]))

        # count_plus = 0
        # count_minus = 0
        for it in md:
            if tomo_idx_plus is None or str(it.rlnIndex) in tomo_idx_plus:
                if self.use_deconv_subtomo == 1:
                    if "rlnDeconvTomoName" in md.getLabels() and it.rlnDeconvTomoName not in [None,'None']:
                        tomo_file = it.rlnDeconvTomoName
                    else:
                        tomo_file = it.rlnMicrographName
                        self.logger.warning('use deconved tomo checked, but the deconvoled map for tomo #{} was not detected. Use original map instead.'.format(it.rlnIndex))
                else:
                    tomo_file = it.rlnMicrographName
                
                #pixel_size = it.rlnPixelSize
                
                self.logger.info("Extract from tomogram {}".format(tomo_file))
                with mrcfile.open(tomo_file, permissive=True) as mrcData:
                    orig_data = mrcData.data.astype(np.float32)*-1

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
                        #im_name_x = '{}/{}/x_{}_{:0>6d}.mrc'.format(plus_folder, dirs_tomake[0], base_name, j)
                        im_name_x = '{}/{}/{}_x_{}.mrc'.format(plus_folder, dirs_tomake[0], base_name, j)
                        
                        ns = normalize(s)
                        rotated_data = rotate(ns, tilt_plus, axes=(0,2))
                        center_x, center_y, center_z = [v//2 for v in rotated_data.shape]

                        with mrcfile.new(im_name_x, overwrite=True) as output_mrc:
                            # count_plus += 1
                            # subtomo_it = Item()
                            # subtomo_md_x_plus.addItem(subtomo_it)
                            # subtomo_md_x_plus._setItemValue(subtomo_it,Label('rlnSubtomoIndex'), str(count_plus))
                            # subtomo_md_x_plus._setItemValue(subtomo_it,Label('rlnImageName'), im_name_x)
                            # subtomo_md_x_plus._setItemValue(subtomo_it,Label('rlnCubeSize'), self.cube_size)
                            # subtomo_md_x_plus._setItemValue(subtomo_it,Label('rlnCropSize'), self.crop_size)
                            # subtomo_md_x_plus._setItemValue(subtomo_it,Label('rlnPixelSize'), pixel_size)
                            
                            cube = rotated_data[center_x-side_len:center_x+side_len, center_y-side_len:center_y+side_len, center_z-side_len:center_z+side_len]

                            cube = apply_wedge(cube, missing_angle_plus)
                            
                            output_mrc.set_data(cube.astype(np.float32))
                        
                        #im_name_y = '{}/plus/y_{}_{:0>6d}.mrc'.format(self.subtomo_folder, base_name, j)
                        im_name_y = '{}/{}/{}_y_{}.mrc'.format(plus_folder, dirs_tomake[1], base_name, j)
                        with mrcfile.new(im_name_y, overwrite=True) as output_mrc:
                            # subtomo_it = Item()
                            # subtomo_md_y_plus.addItem(subtomo_it)
                            # subtomo_md_y_plus._setItemValue(subtomo_it,Label('rlnSubtomoIndex'), str(count_plus))
                            # subtomo_md_y_plus._setItemValue(subtomo_it,Label('rlnImageName'), im_name_y)
                            # subtomo_md_y_plus._setItemValue(subtomo_it,Label('rlnCubeSize'), self.cube_size)
                            # subtomo_md_y_plus._setItemValue(subtomo_it,Label('rlnCropSize'), self.crop_size)
                            # subtomo_md_y_plus._setItemValue(subtomo_it,Label('rlnPixelSize'), pixel_size)

                            #rotated_data = rotate(s, tilt_plus, axes=(0,2))

                            cube = rotated_data[center_x-side_len:center_x+side_len, center_y-side_len:center_y+side_len, center_z-side_len:center_z+side_len]

                            output_mrc.set_data(cube.astype(np.float32))
                else:
                    self.logger.warning('Tomogram map {} was not detected.'.format(tomo_file))

            if tomo_idx_minus is None or str(it.rlnIndex) in tomo_idx_minus:
                if self.use_deconv_subtomo == 1:
                    if "rlnDeconvTomoName" in md.getLabels() and it.rlnDeconvTomoName not in [None,'None']:
                        tomo_file = it.rlnDeconvTomoName
                    else:
                        tomo_file = it.rlnMicrographName
                        self.logger.warning('use deconved tomo checked, but the deconvoled map for tomo #{} was not detected. Use original map instead.'.format(it.rlnIndex))
                else:
                    tomo_file = it.rlnMicrographName
                
                #pixel_size = it.rlnPixelSize
                
                self.logger.info("Extract from deconvolved tomogram {}".format(tomo_file))
                
                with mrcfile.open(tomo_file, permissive=True) as mrcData:
                    orig_data = mrcData.data.astype(np.float32)*-1

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
                        #im_name_x = '{}/minus/x_{}_{:0>6d}.mrc'.format(self.subtomo_folder, base_name, j)
                        im_name_x = '{}/{}/{}_x_{}.mrc'.format(minus_folder, dirs_tomake[0], base_name, j)
                        rotated_data = rotate(s, -tilt_minus, axes=(0,2))
                        center_x, center_y, center_z = [v//2 for v in rotated_data.shape]
                        with mrcfile.new(im_name_x, overwrite=True) as output_mrc:
                            # count_minus += 1
                            # subtomo_it = Item()
                            # subtomo_md_x_minus.addItem(subtomo_it)
                            # subtomo_md_x_minus._setItemValue(subtomo_it,Label('rlnSubtomoIndex'), str(count_minus))
                            # subtomo_md_x_minus._setItemValue(subtomo_it,Label('rlnImageName'), im_name_x)
                            # subtomo_md_x_minus._setItemValue(subtomo_it,Label('rlnCubeSize'), self.cube_size)
                            # subtomo_md_x_minus._setItemValue(subtomo_it,Label('rlnCropSize'), self.crop_size)
                            # subtomo_md_x_minus._setItemValue(subtomo_it,Label('rlnPixelSize'), pixel_size)
                            
                            

                            cube = rotated_data[center_x-side_len:center_x+side_len, center_y-side_len:center_y+side_len, center_z-side_len:center_z+side_len]

                            cube = apply_wedge(cube, missing_angle_minus)

                            output_mrc.set_data(cube.astype(np.float32))
                        
                        #im_name_y = '{}/minus/y_{}_{:0>6d}.mrc'.format(self.subtomo_folder, base_name, j)
                        im_name_y = '{}/{}/{}_y_{}.mrc'.format(minus_folder, dirs_tomake[1], base_name, j)
                        with mrcfile.new(im_name_y, overwrite=True) as output_mrc:
                            # subtomo_it = Item()
                            # subtomo_md_y_minus.addItem(subtomo_it)
                            # subtomo_md_y_minus._setItemValue(subtomo_it,Label('rlnSubtomoIndex'), str(count_minus))
                            # subtomo_md_y_minus._setItemValue(subtomo_it,Label('rlnImageName'), im_name_y)
                            # subtomo_md_y_minus._setItemValue(subtomo_it,Label('rlnCubeSize'), self.cube_size)
                            # subtomo_md_y_minus._setItemValue(subtomo_it,Label('rlnCropSize'), self.crop_size)
                            # subtomo_md_y_minus._setItemValue(subtomo_it,Label('rlnPixelSize'), pixel_size)

                            cube = rotated_data[center_x-side_len:center_x+side_len, center_y-side_len:center_y+side_len, center_z-side_len:center_z+side_len]

                            output_mrc.set_data(cube.astype(np.float32))
                else:
                    self.logger.warning('Tomogram map {} was not detected.'.format(tomo_file))
                
                
        # subtomo_md_x_plus.write(self.subtomo_star_plus_x)
        # subtomo_md_y_plus.write(self.subtomo_star_plus_y)
        # subtomo_md_x_minus.write(self.subtomo_star_minus_x)
        # subtomo_md_y_minus.write(self.subtomo_star_minus_y)

        self.logger.info( "Extraction Done --- {} mins ---".format(round((time.time() - start_time)/60, 2)))

        split_data(plus_folder)
        split_data(minus_folder)
    
    def stop_process(self):
        self.quit()
        self.terminate()
        self.wait()