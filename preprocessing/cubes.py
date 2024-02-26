import numpy as np
import scipy.cluster.hierarchy as hcluster

from TomoNet.util.io import log
from TomoNet.util.geometry import in_boundary

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
        
        if in_boundary([z,y,x], sp, cubeSideLen//2):
            random_shifts = np.random.choice(cubeSideLen, 3) - cubeSideLen//2
            x,y,z = np.array([x,y,z]) + random_shifts
        
            #x,y,z = [int(p) for p in [x,y,z]]
            x,y,z = [int(p) for p in [x,y,z]]
            
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


def normalize(x, percentile = True, pmin=4.0, pmax=96.0, axis=None, clip=False, eps=1e-20):
    """Percentile-based image normalization."""
    if percentile:
        mi = np.percentile(x,pmin,axis=axis,keepdims=True)
        ma = np.percentile(x,pmax,axis=axis,keepdims=True)
        out = (x - mi) / ( ma - mi + eps )
        out = out.astype(np.float32)
        if clip:
            return np.clip(out,0,1)
        else:
            return out
    else:
        out = (x-np.mean(x))/np.std(x)
        out = out.astype(np.float32)
        return out