from .unet import Unet
import torch
import torch.nn as nn
import pytorch_lightning as pl
from TomoNet.util.io import log

import os
from .data_sequence import get_datasets, Predict_sets
import mrcfile
from TomoNet.preprocessing.cubes import normalize
import numpy as np
import logging
from TomoNet.util.toTile import reform3D
import sys
from tqdm import tqdm


class Net:
    def __init__(self,filter_base=64,out_channels=1, learning_rate = 3e-4, add_last=False, metrics=None):
        self.model = Unet(filter_base = filter_base,learning_rate=learning_rate, out_channels=out_channels, add_last=add_last, metrics=metrics)


    def load(self, path):
        checkpoint = torch.load(path)
        self.model.load_state_dict(checkpoint)

    def load_jit(self, path):
        #Using the TorchScript format, you will be able to load the exported model and run inference without defining the model class.
        self.model = torch.jit.load(path)
    
    def save(self, path):
        state = self.model.state_dict()
        torch.save(state, path)

    def save_jit(self, path):
        model_scripted = torch.jit.script(self.model) # Export to TorchScript
        model_scripted.save(path) # Save

    def train(self, data_path, gpuID=[0,1,2,3], batch_size=None, 
              epochs = 10, steps_per_epoch=200, acc_batches =2,
              ncpus=8, precision=32, learning_rate=3e-4, enable_progress_bar=True):
        self.model.learning_rate = learning_rate
        #print(batch_size)
        #print('acc_batches',acc_batches)
        #acc_grad = True
        train_batches = int(steps_per_epoch*0.9)
        val_batches = steps_per_epoch - train_batches
        #acc_batches = 4
        if acc_batches > 1:
            logging.info("use accumulate gradient to reduce GPU memory consumption")
            batch_size = batch_size//acc_batches
            train_batches = train_batches * acc_batches
            val_batches = val_batches * acc_batches

        #torch.multiprocessing.set_sharing_strategy('file_system')
        train_dataset, val_dataset = get_datasets(data_path)
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True, persistent_workers=True,
                                                num_workers=ncpus//2, pin_memory=True, drop_last=True)

        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=True, persistent_workers=True,
                                                pin_memory=True, num_workers=ncpus//2, drop_last=True)
        #val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False, persistent_workers=True,
        #                                        pin_memory=True, num_workers=ncpus//2, drop_last=True)
        self.model.train()
        if isinstance(gpuID, str):
            gpuID = list(map(int,gpuID.split(',')))
        
        if enable_progress_bar:
            callbacks = pl.callbacks.progress.ProgressBar(refresh_rate=5)
        else:
            callbacks = None

        #early_stopping = pl.callbacks.EarlyStopping('train_loss', patience = 3)
        #early_stopping = pl.callbacks.EarlyStopping('val_loss', patience = 3)
        
        trainer = pl.Trainer(
            accumulate_grad_batches=acc_batches,
            accelerator='gpu',
            precision=precision,
            devices=gpuID,
            num_nodes=1,
            max_epochs=epochs,
            limit_train_batches = train_batches,
            limit_val_batches = val_batches,
            strategy = 'dp',
            enable_progress_bar=enable_progress_bar,
            logger=False,
            enable_checkpointing=False,
            callbacks=[callbacks],
            num_sanity_val_steps=0,
        )
        trainer.fit(self.model, train_loader, val_loader)        
        return self.model.metrics

    def predict(self, mrc_list, result_dir, iter_count, inverted=True, mw3d=None, batch_size=1, filter_strength=1.5, logger=None):    

        full_size = 100
        full_length = len(mrc_list)
        iter = full_length//full_size
        if full_length%full_size == 0:
            iter-=1
        #print("iter num:",iter)
        for i in range(iter+1):
            
            if i == iter:
                subset = mrc_list[i*full_size:] 
            else:
                subset = mrc_list[i*full_size:(i+1)*full_size]

            if i == iter or iter//4 == 0 or (i+1)%(iter//4) == 0:
                log(logger, "{} out of {}".format(i*full_size + len(subset), full_length))

            bench_dataset = Predict_sets(subset, inverted=inverted)
            bench_loader = torch.utils.data.DataLoader(bench_dataset, batch_size=batch_size, num_workers=1)

            model = torch.nn.DataParallel(self.model.cuda())
            model.eval()

            predicted = []
            with torch.no_grad():
                for _, val_data in enumerate(bench_loader):
                        res = model(val_data) 
                        miu = res.cpu().detach().numpy().astype(np.float32)
                        for item in miu:
                            #print(item.shape)
                            #it = item.squeeze(0)
                            predicted.append(item)
            for i, mrc in enumerate(subset):
                root_name = mrc.split('/')[-1].split('.')[0]

                #outData = normalize(predicted[i], percentile = normalize_percentile)
                if iter_count == 0:
                    file_name = '{}/{}_pred.mrc'.format(result_dir, root_name)
                else:
                    file_name = '{}/{}_iter{:0>2d}.mrc'.format(result_dir, root_name, iter_count-1)
    
                with mrcfile.new(file_name, overwrite=True) as output_mrc:
                    #temp = predicted[i][0] - predicted[i][1]
                    temp = predicted[i]
                    tensor_temp = torch.from_numpy(temp)
                    temp = np.array(nn.Sigmoid()(tensor_temp))
                    #print(temp)
                    p = 1/(10**filter_strength)
                    temp[temp < p] = 0
                    temp[temp >= p] = 1
                    #temp[temp < 0] = 0
                    #if inverted:
                    #    output_mrc.set_data(-temp)
                    #else:
                    output_mrc.set_data(temp)

    
    def predict_tomo(self, args, one_tomo, output_file=None):
    #predict one tomogram in mrc format INPUT: mrc_file string OUTPUT: output_file(str) or <root_name>_corrected.mrc

        root_name = one_tomo.split('/')[-1].split('.')[0]

        if output_file is None:
            if os.path.isdir(args.output_file):
                output_file = args.output_file+'/'+root_name+'_corrected.mrc'
            else:
                output_file = root_name+'_corrected.mrc'

        logging.info('predicting:{}'.format(root_name))

        with mrcfile.open(one_tomo) as mrcData:
            real_data = mrcData.data.astype(np.float32)*-1
            voxelsize = mrcData.voxel_size

        real_data = normalize(real_data,percentile=args.normalize_percentile)
        data=np.expand_dims(real_data,axis=-1)
        reform_ins = reform3D(data)
        data = reform_ins.pad_and_crop_new(args.cube_size,args.crop_size)

        N = args.batch_size
        num_patches = data.shape[0]
        if num_patches%N == 0:
            append_number = 0
        else:
            append_number = N - num_patches%N
        data = np.append(data, data[0:append_number], axis = 0)
        num_big_batch = data.shape[0]//N
        outData = np.zeros(data.shape)

        logging.info("total batches: {}".format(num_big_batch))


        model = torch.nn.DataParallel(self.model.cuda())
        model.eval()
        with torch.no_grad():
            for i in tqdm(range(num_big_batch), file=sys.stdout):#track(range(num_big_batch), description="Processing..."):
                in_data = torch.from_numpy(np.transpose(data[i*N:(i+1)*N],(0,4,1,2,3)))
                output = model(in_data)
                outData[i*N:(i+1)*N] = np.transpose(output.cpu().detach().numpy().astype(np.float32), (0,2,3,4,1) )

        outData = outData[0:num_patches]

        outData=reform_ins.restore_from_cubes_new(outData.reshape(outData.shape[0:-1]), args.cube_size, args.crop_size)

        outData = normalize(outData,percentile=args.normalize_percentile)
        with mrcfile.new(output_file, overwrite=True) as output_mrc:
            output_mrc.set_data(-outData)
            output_mrc.voxel_size = voxelsize

        logging.info('Done predicting')
    
    def predict_map(self, halfmap,halfmap_origional, mask, fsc3d_full, fsc3d, output_file, cube_size = 64, crop_size=96, batch_size = 4, voxel_size = 1.1):
    #predict one tomogram in mrc format INPUT: mrc_file string OUTPUT: output_file(str) or <root_name>_corrected.mrc


        #logging.info('Inference')
        #pad_width = 16
        #real_data = np.pad(halfmap, pad_width, mode='edge')

        real_data = halfmap.copy()
        d = real_data.shape[0]
        r = np.arange(d)-d//2
        [Z,Y,X] = np.meshgrid(r,r,r)
        index = np.round(np.sqrt(Z**2+Y**2+X**2))
        real_data[index>r] = halfmap_origional[index>r]

        data=np.expand_dims(real_data,axis=-1)
        reform_ins = reform3D(data)
        data = reform_ins.pad_and_crop_new(cube_size,crop_size)

        N = batch_size
        num_patches = data.shape[0]
        if num_patches%N == 0:
            append_number = 0
        else:
            append_number = N - num_patches%N
        data = np.append(data, data[0:append_number], axis = 0)
        num_big_batch = data.shape[0]//N
        outData = np.zeros(data.shape)

        logging.info("total batches: {}".format(num_big_batch))


        model = torch.nn.DataParallel(self.model.cuda())
        model.to(f'cuda:{model.device_ids[0]}')
        model.eval()
        with torch.no_grad():
            for i in tqdm(range(num_big_batch), file=sys.stdout):#track(range(num_big_batch), description="Processing..."):
                in_data = torch.from_numpy(np.transpose(data[i*N:(i+1)*N],(0,4,1,2,3)))
                #print(in_data)
                in_data.to(f'cuda:{model.device_ids[0]}')
                output = model(in_data)
                out_tmp = output.cpu().detach().numpy().astype(np.float32)
                #out_tmp = apply_wedge_dcube(out_tmp, mw3d=fsc3d,ld1=0, ld2=1)
                out_tmp = np.transpose(out_tmp, (0,2,3,4,1) )

                #out_data_tmp = np.transpose(data[i*N:(i+1)*N], (0,4,1,2,3))
                #out_data_tmp = apply_wedge_dcube(out_data_tmp, mw3d=fsc3d,ld1=1, ld2=0)
                #out_data_tmp = np.transpose(out_data_tmp, (0,2,3,4,1) )


                outData[i*N:(i+1)*N] = out_tmp#  + out_data_tmp

        outData = outData[0:num_patches]

        outData=reform_ins.restore_from_cubes_new(outData.reshape(outData.shape[0:-1]), cube_size, crop_size)

        #outData = outData[pad_width:-pad_width,pad_width:-pad_width,pad_width:-pad_width]
        with mrcfile.new(output_file[2], overwrite=True) as output_mrc:
            output_mrc.set_data((outData).astype(np.float32))
            output_mrc.voxel_size = voxel_size
        #outData = apply_wedge(normalize(outData),mw3d=fsc3d_full, ld1=0, ld2=1)
        
        #outData = apply_wedge(outData,mw3d=fsc3d_full, ld1=0, ld2=1)

        # print(np.std(outData))
        diff_map = (outData - halfmap)#*mask
        # print('diff_sd', np.std(diff_map))
        outData = diff_map + halfmap_origional# apply_wedge(normalize(halfmap),mw3d=fsc3d_full, ld1=1, ld2=0) #0.5*real_data#
        #outData += apply_wedge(halfmap_origional,mw3d=fsc3d_full, ld1=1, ld2=0)
        # print(np.std(outData))
        # print(np.std(halfmap))
        # print(np.std(halfmap_origional))


        #outData = normalize(outData,percentile=args.normalize_percentile)
        with mrcfile.new(output_file[0], overwrite=True) as output_mrc:
            output_mrc.set_data(outData.astype(np.float32))
            output_mrc.voxel_size = voxel_size
        with mrcfile.new(output_file[1], overwrite=True) as output_mrc:
            output_mrc.set_data(halfmap.astype(np.float32))
            output_mrc.voxel_size = voxel_size



        logging.info('Done predicting')

    def predict_map_sigma(self, halfmap,halfmap_origional,fsc3d_full, fsc3d, output_file, cube_size = 64, crop_size=96, batch_size = 4, voxel_size = 1.1, output_sigma_file=None):
        #predict one tomogram in mrc format INPUT: mrc_file string OUTPUT: output_file(str) or <root_name>_corrected.mrc


            logging.info('Inference')

            real_data = halfmap
            data=np.expand_dims(real_data,axis=-1)
            reform_ins = reform3D(data)
            data = reform_ins.pad_and_crop_new(cube_size,crop_size)

            N = batch_size
            num_patches = data.shape[0]
            if num_patches%N == 0:
                append_number = 0
            else:
                append_number = N - num_patches%N
            data = np.append(data, data[0:append_number], axis = 0)
            num_big_batch = data.shape[0]//N
            outData = np.zeros(data.shape)
            out_sigma = np.zeros(data.shape)

            logging.info("total batches: {}".format(num_big_batch))


            model = torch.nn.DataParallel(self.model.cuda())
            model.eval()
            with torch.no_grad():
                for i in tqdm(range(num_big_batch), file=sys.stdout):#track(range(num_big_batch), description="Processing..."):
                    in_data = torch.from_numpy(np.transpose(data[i*N:(i+1)*N],(0,4,1,2,3)))
                    #print(in_data)
                    output = model(in_data)
                    out_tmp = output[0].cpu().detach().numpy().astype(np.float32)
                    #out_tmp = apply_wedge_dcube(out_tmp, mw3d=fsc3d,ld1=0, ld2=1)
                    out_tmp = np.transpose(out_tmp, (0,2,3,4,1) )
                    out_sigma_tmp = output[1].cpu().detach().numpy().astype(np.float32)
                    out_sigma_tmp = np.transpose(out_sigma_tmp, (0,2,3,4,1) )
                    #out_data_tmp = np.transpose(data[i*N:(i+1)*N], (0,4,1,2,3))
                    #out_data_tmp = apply_wedge_dcube(out_data_tmp, mw3d=fsc3d,ld1=1, ld2=0)
                    #out_data_tmp = np.transpose(out_data_tmp, (0,2,3,4,1) )


                    outData[i*N:(i+1)*N] = out_tmp#  + out_data_tmp
                    out_sigma[i*N:(i+1)*N] = out_sigma_tmp#  + out_data_tmp

            outData = outData[0:num_patches]
            out_sigma = out_sigma[0:num_patches]
            outData=reform_ins.restore_from_cubes_new(outData.reshape(outData.shape[0:-1]), cube_size, crop_size)
            out_sigma=reform_ins.restore_from_cubes_new(out_sigma.reshape(out_sigma.shape[0:-1]), cube_size, crop_size)
            print(np.std(outData))
            #outData = apply_wedge(normalize(outData),mw3d=fsc3d_full, ld1=0, ld2=1)
            
            #outData = apply_wedge(outData,mw3d=fsc3d_full, ld1=0, ld2=1)
            print(np.std(outData))
            outData += halfmap_origional# apply_wedge(normalize(halfmap),mw3d=fsc3d_full, ld1=1, ld2=0) #0.5*real_data#
            print(np.std(outData))
            print(np.std(real_data))

            #outData = normalize(outData,percentile=args.normalize_percentile)
            with mrcfile.new(output_file, overwrite=True) as output_mrc:
                output_mrc.set_data(outData.astype(np.float32))
                output_mrc.voxel_size = voxel_size

            if output_sigma_file is not None:
                with mrcfile.new(output_sigma_file, overwrite=True) as output_mrc:
                    output_mrc.set_data(out_sigma.astype(np.float32))
                    output_mrc.voxel_size = voxel_size

            logging.info('Done predicting')
