import os
import numpy as np
import mrcfile
import scipy.cluster.hierarchy as hcluster

from IsoNet.preprocessing.simulate import apply_wedge_dcube as apply_wedge
from IsoNet.util.noise_generator import make_noise_one
# from IsoNet.preprocessing.simulate import apply_wedge

from IsoNet.util.io import log

def create_cube_seeds(img3D,nCubesPerImg,cubeSideLen,mask=None):
    sp=img3D.shape
    if mask is None:
        cubeMask=np.ones(sp)
    else:
        cubeMask=mask
    border_slices = tuple([slice(s // 2, d - s + s // 2 + 1) for s, d in zip((cubeSideLen,cubeSideLen,cubeSideLen), sp)])
    valid_inds = np.where(cubeMask[border_slices])
    valid_inds = [v + s.start for s, v in zip(border_slices, valid_inds)]
    sample_inds = np.random.choice(len(valid_inds[0]), nCubesPerImg, replace=len(valid_inds[0]) < nCubesPerImg)
    rand_inds = [v[sample_inds] for v in valid_inds]
    return (rand_inds[0],rand_inds[1], rand_inds[2])

def create_cube_seeds_new(img3D, nCubesPerImg, cubeSideLen, coords, mask=None, logger=None):
    sp=img3D.shape
    
    if mask is None:
        cubeMask=np.ones(sp)
    else:
        cubeMask=mask
    border_slices = tuple([slice(s // 2, d - s + s // 2 + 1) for s, d in zip((cubeSideLen,cubeSideLen,cubeSideLen), sp)])
    
    coords = np.array(coords)
    clusters = hcluster.fclusterdata(coords, nCubesPerImg, criterion="maxclust")
    mask_coords = np.zeros(sp)
    for i in range(len(set(clusters))):
        #x,y,z = np.mean(coords[np.argwhere(clusters == i+1)], axis=0)[0] 
        x,y,z = coords[np.argwhere(clusters == i+1)][0][0]
        x,y,z = [int(p) for p in [x,y,z]]
        #print(x,y,z)
        mask_coords[z,y,x] = 1
    
    #with mrcfile.new("mask_coords.mrc", overwrite=True) as output_mrc:
    #    output_mrc.set_data(mask_coords.astype(np.float32))

    merged_mask = np.multiply(cubeMask, mask_coords)

    valid_inds = np.where(merged_mask[border_slices])
    valid_inds = [v + s.start for s, v in zip(border_slices, valid_inds)]
    sample_inds = np.random.choice(len(valid_inds[0]), nCubesPerImg, replace=len(valid_inds[0]) < nCubesPerImg)
    rand_inds = [v[sample_inds] for v in valid_inds]
    
    log(logger, "asked for {} subtomos, actually got {}".format(nCubesPerImg, len(rand_inds[0])))

    return (rand_inds[0], rand_inds[1], rand_inds[2])


def mask_mesh_seeds(mask,sidelen,croplen,threshold=0.01,indx=0):
    #indx = 0 take the even indix element of seed list,indx = 1 take the odd 
    # Count the masked points in the box centered at mesh grid point, if greater than threshold*sidelen^3, Take the grid point as seed.
    sp = mask.shape
    ni = [(i-croplen)//sidelen +1 for i in sp]
    # res = [((i-croplen)%sidelen) for i in sp]
    margin = croplen//2 - sidelen//2
    ind_list =[]
    for z in range(ni[0]):
        for y in range(ni[1]):
            for x in range(ni[2]):
                if np.sum(mask[margin+sidelen*z:margin+sidelen*(z+1),
                margin+sidelen*y:margin+sidelen*(y+1),
                margin+sidelen*x:margin+sidelen*(x+1)]) > sidelen**3*threshold:
                    ind_list.append((margin+sidelen//2+sidelen*z, margin+sidelen//2+sidelen*y,
                margin+sidelen//2+sidelen*x))
    ind_list = ind_list[indx:-1:2]
    ind0 = [i[0] for i in ind_list]
    ind1 = [i[1] for i in ind_list]
    ind2 = [i[2] for i in ind_list]
    # return ind_list
    return (ind0,ind1,ind2)


def crop_cubes(img3D,seeds,cubeSideLen):
    size=len(seeds[0])
    cube_size=(cubeSideLen,cubeSideLen,cubeSideLen)
    cubes=[img3D[tuple(slice(_r-(_p//2),_r+_p-(_p//2)) for _r,_p in zip(r,cube_size))] for r in zip(*seeds)]
    cubes=np.array(cubes)
    return cubes

class DataCubes:

    def __init__(self, tomogram, tomogram2 = None, nCubesPerImg=32, cubeSideLen=32, cropsize=32, mask = None, 
    validationSplit=0.1, noise_folder = None, noise_level = 0, noise_mode = 'ramp'):

        #TODO nCubesPerImg is always 1. We should not use this variable @Zhang Heng.
        #TODO consider add gaussian filter here
        self.tomogram = tomogram
        self.nCubesPerImg = nCubesPerImg
        self.cubeSideLen = cubeSideLen
        self.cropsize = cropsize
        self.mask = mask
        self.validationSplit = validationSplit
        self.__cubesY_padded = None
        self.__cubesX_padded = None
        self.__cubesY = None
        self.__cubesX = None
        self.noise_folder = noise_folder
        self.noise_level = noise_level
        self.noise_mode = noise_mode

        #if we have two sub-tomograms for denoising (noise to noise), we will enable the parameter tomogram2, tomogram1 and 2 should be in same size
        #Using tomogram1 for X and tomogram2 for Y.
        self.tomogram2 = tomogram2
        self.__seeds = None

    #@property
    #def seeds(self):
    #    if self.__seeds is None:
    #        self.__seeds=create_cube_seeds(self.tomogram,self.nCubesPerImg,self.cropsize,self.mask)
    #    return self.__seeds

    @property
    def cubesX_padded(self):
        if self.__cubesX_padded is None:
            #self.__cubesX_padded=crop_cubes(self.tomogram,self.seeds,self.cropsize).astype(np.float32)
            #self.__cubesX_padded = np.array(list(map(apply_wedge, self.__cubesX_padded)), dtype = np.float32)
            self.__cubesX_padded = apply_wedge(self.tomogram)
        return self.__cubesX_padded

    @property
    def cubesY_padded(self):
        if self.__cubesY_padded is None:
            #if self.tomogram2 is None:
            #    self.__cubesY_padded=crop_cubes(self.tomogram,self.seeds,self.cropsize)
            #else:
            #    self.__cubesY_padded=crop_cubes(self.tomogram2,self.seeds,self.cropsize)
            self.__cubesY_padded = self.tomogram
        return self.__cubesY_padded


    @property
    def cubesY(self):
        if self.__cubesY is None:
            self.__cubesY = self.crop_to_size(self.cubesY_padded, self.cubeSideLen)
        return self.__cubesY

    @property
    def cubesX(self):
        if self.__cubesX is None:

            self.__cubesX = self.crop_to_size(self.cubesX_padded, self.cubeSideLen)
            if self.noise_level > 0.0000001:
                if self.noise_folder is not None:
                    path_noise = sorted([self.noise_folder+'/'+f for f in os.listdir(self.noise_folder)])
                    path_index = np.random.permutation(len(path_noise))[0:self.__cubesX.shape[0]]
                    def read_vol(f):
                        with mrcfile.open(f) as mf:
                            res = mf.data
                        return res
                    noise_volume = np.array([read_vol(path_noise[j]) for j in path_index])
                else:
                    noise_volume = make_noise_one(cubesize = self.cubeSideLen,mode=self.noise_mode)
                
                self.__cubesX += self.noise_level * noise_volume / np.std(noise_volume)
        return self.__cubesX


    def crop_to_size(self, array, size):
        start = self.cropsize//2 - size//2
        end = self.cropsize//2 + size//2
        return array[start:end,start:end,start:end]

    def create_training_data3D(self):
        n_val = int(self.cubesX.shape[0]*self.validationSplit)
        n_train = int(self.cubesX.shape[0])-n_val
        X_train, Y_train = self.cubesX[:n_train], self.cubesY[:n_train]
        X_train, Y_train = np.expand_dims(X_train,-1), np.expand_dims(Y_train,-1)
        X_test, Y_test = self.cubesX[-n_val:], self.cubesY[-n_val:]
        X_test, Y_test = np.expand_dims(X_test,-1), np.expand_dims(Y_test,-1)
        return (X_train, Y_train),(X_test, Y_test)