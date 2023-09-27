import os
import numpy as np
import torch
from torch.utils.data.dataset import Dataset
import mrcfile
from TomoNet.preprocessing.cubes import normalize

class Train_sets(Dataset):
    def __init__(self, data_dir, prefix = "train"):
        super(Train_sets, self).__init__()
        self.path_all = []
        for d in  [prefix+"_x", prefix+"_y"]:
            p = '{}/{}/'.format(data_dir, d)
            self.path_all.append(sorted([p+f for f in os.listdir(p)]))
        #print(self.path_all)

    def __getitem__(self, idx):
        with mrcfile.open(self.path_all[0][idx]) as mrc:
            #print(self.path_all[0][idx])
            rx = mrc.data[np.newaxis,:,:,:]
            # rx = mrc.data[:,:,:,np.newaxis]
        with mrcfile.open(self.path_all[1][idx]) as mrc:
            #print(self.path_all[1][idx])
            ry = mrc.data[np.newaxis,:,:,:]
            # ry = mrc.data[:,:,:,np.newaxis]
        rx = torch.from_numpy(rx.copy())
        ry = torch.from_numpy(ry.copy())
        return rx, ry

    def __len__(self):
        return len(self.path_all[0])

class Train_sets_new(Dataset):
    def __init__(self, data_dir, prefix = "train"):
        super(Train_sets_new, self).__init__()
        self.path_all = []
        for d in  [prefix+"_x", prefix+"_y"]:
            p = '{}/{}/'.format(data_dir, d)
            self.path_all.append(sorted([p+f for f in os.listdir(p)]))
        #print(self.path_all)

    def __getitem__(self, idx):
        with mrcfile.open(self.path_all[0][idx]) as mrc:
            #print(self.path_all[0][idx])
            rx = mrc.data[np.newaxis,:,:,:]
            # rx = mrc.data[:,:,:,np.newaxis]
        with mrcfile.open(self.path_all[1][idx]) as mrc:
            #print(self.path_all[1][idx])
            ry = mrc.data[np.newaxis,:,:,:]
            # ry = mrc.data[:,:,:,np.newaxis]
        rx = torch.from_numpy(rx.copy())
        ry = torch.from_numpy(ry.copy())
        #ry1 = torch.from_numpy(ry.copy())
        #ry2 = torch.from_numpy(1-ry.copy())
        #ry = np.concatenate((ry1,ry2))
        #ry = ry.reshape(tuple([2])+ry1.shape[1:])
        #print(ry.shape)
        return rx, ry

    def __len__(self):
        return len(self.path_all[0])

class Predict_sets(Dataset):
    def __init__(self, mrc_list, inverted=True):
        super(Predict_sets, self).__init__()
        self.mrc_list=mrc_list
        self.inverted = inverted

    def __getitem__(self, idx):
        with mrcfile.open(self.mrc_list[idx]) as mrc:
            rx = mrc.data[np.newaxis,:,:,:].copy()
        # rx = mrcfile.open(self.mrc_list[idx]).data[:,:,:,np.newaxis]
        if self.inverted:
            rx=normalize(-rx, percentile = True)

        return rx

    def __len__(self):
        return len(self.mrc_list)



def get_datasets(data_dir):
    train_dataset = Train_sets_new(data_dir, prefix="train")
    val_dataset = Train_sets_new(data_dir, prefix="test")
    return train_dataset, val_dataset#, bench_dataset


class Train_sets_angle(Dataset):
    def __init__(self, data_dir, prefix = "train"):
        super(Train_sets_angle, self).__init__()
        self.path_all = []
        for d in  [prefix+"_x", prefix+"_y"]:
            p = '{}/{}/'.format(data_dir, d)
            self.path_all.append(sorted([p+f for f in os.listdir(p)]))
        #print(self.path_all)

    def __getitem__(self, idx):
        with mrcfile.open(self.path_all[0][idx]) as mrc:
            #print(self.path_all[0][idx])
            rx = mrc.data[np.newaxis,:,:,:]
            # rx = mrc.data[:,:,:,np.newaxis]
        with mrcfile.open(self.path_all[1][idx]) as mrc:
            #print(self.path_all[1][idx])
            ry = mrc.data[np.newaxis,:,:,:]
            # ry = mrc.data[:,:,:,np.newaxis]
        rx_pre = torch.from_numpy(rx.copy())
        rx_shape = rx_pre.shape
        rx = rx_pre.reshape((2,rx_shape[1]//2,rx_shape[2],rx_shape[3]))
        ry_pre = torch.from_numpy(ry.copy())
        ry_shape = ry_pre.shape
        ry = ry_pre.reshape((3,ry_shape[1]//3,ry_shape[2],ry_shape[3]))
        #ry1 = torch.from_numpy(ry.copy())
        #ry2 = torch.from_numpy(1-ry.copy())
        #ry = np.concatenate((ry1,ry2))
        #ry = ry.reshape(tuple([2])+ry1.shape[1:])
        #print(ry.shape)
        return rx, ry

    def __len__(self):
        return len(self.path_all[0])
    
def get_datasets_angles(data_dir):
    train_dataset = Train_sets_angle(data_dir, prefix="train")
    val_dataset = Train_sets_angle(data_dir, prefix="test")
    return train_dataset, val_dataset#, bench_dataset


class Predict_sets_angle(Dataset):
    def __init__(self, mrc_list, inverted=True):
        super(Predict_sets_angle, self).__init__()
        self.mrc_list=mrc_list
        self.inverted = inverted

    def __getitem__(self, idx):
        with mrcfile.open(self.mrc_list[idx]) as mrc:
            rx = mrc.data[np.newaxis,:,:,:].copy()
        # rx = mrcfile.open(self.mrc_list[idx]).data[:,:,:,np.newaxis]
        if self.inverted:
            rx=normalize(-rx, percentile = True)
        sp = rx.shape
        rx = rx.reshape(2,sp[1]//2,sp[2],sp[3])
        #print(rx.shape)
        return rx

    def __len__(self):
        return len(self.mrc_list)