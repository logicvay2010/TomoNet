"""
Generate mask by comparing local variance and global variance
"""
import numpy as np

def maxmask(tomo, side=5,percentile=60):
    from scipy.ndimage.filters import maximum_filter
    # print('maximum_filter')
    filtered = maximum_filter(-tomo, 2*side+1, mode='reflect')
    out =  filtered > np.percentile(filtered,100-percentile)
    out = out.astype(np.uint8)
    return out

def stdmask(tomo,side=10,threshold=60):
    from scipy.signal import convolve
    # print('std_filter')
    tomosq = tomo**2
    ones = np.ones(tomo.shape)
    eps = 0.001
    kernel = np.ones((2*side+1, 2*side+1, 2*side+1))
    s = convolve(tomo, kernel, mode="same")
    s2 = convolve(tomosq, kernel, mode="same")
    ns = convolve(ones, kernel, mode="same") + eps

    out = np.sqrt((s2 - s**2 / ns) / ns + eps)
    # out = out>np.std(tomo)*threshold
    out  = out>np.percentile(out, 100-threshold)
    return out.astype(np.uint8)

def boundary_mask(tomo, mask_boundary, binning = 2, logger=None):
    out = np.zeros(tomo.shape, dtype = np.float32)
    import os
    import sys
    if mask_boundary[-4:] == '.mod':
        os.system('model2point {} {}.point >> /dev/null'.format(mask_boundary, mask_boundary[:-4]))
    else:
        if logger is not None:
            logger.error("mask boundary file should end with '.mod' but got {} !\n".format(mask_boundary))
        sys.exit()
    
    points = np.loadtxt(mask_boundary[:-4]+'.point', dtype = np.float32)/binning
    
    def get_polygon(points):
        if len(points) == 0:
            if logger is not None:
                logger.info("No polygonal mask")
            return None
        elif len(points) <= 2:
            if logger is not None:
                logger.error("In {}, {} points cannot defines a polygon of mask".format(mask_boundary, len(points)))
            sys.exit()
        else:
            if logger is not None:
                logger.info("In {}, {} points defines a polygon of mask".format(mask_boundary, len(points)))
            return points[:,[1,0]]
    
    if points.ndim < 2: 
        if logger is not None:
            logger.error("In {}, too few points to define a boundary".format(mask_boundary))
        sys.exit()

    z1=points[-2][-1]
    z0=points[-1][-1]

    if abs(z0 - z1) < 5:
        zmin = 0
        zmax = tomo.shape[0]
        polygon = get_polygon(points)
        if logger is not None:
            logger.info("In {}, all points defines a polygon with full range in z".format(mask_boundary))

    else:
        zmin = max(min(z0,z1),0) 
        zmax = min(max(z0,z1),tomo.shape[0])
        polygon = get_polygon(points[:-2])
        if logger is not None:
            logger.info("In {}, the last two points defines the z range of mask".format(mask_boundary))

    zmin = int(zmin)
    zmax = int(zmax)
    if polygon is None:
        out[zmin:zmax,:,:] = 1
    else:
        from matplotlib.path import Path
        poly_path = Path(polygon)
        y, x = np.mgrid[:tomo.shape[1],:tomo.shape[2]]
        coors = np.hstack((y.reshape(-1, 1), x.reshape(-1,1)))
        mask = poly_path.contains_points(coors)
        mask = mask.reshape(tomo.shape[1],tomo.shape[2])
        mask = mask.astype(np.float32)
        out[zmin:zmax,:,:] = mask[np.newaxis,:,:]

    return out
