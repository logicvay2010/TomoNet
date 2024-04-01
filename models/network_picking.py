import mrcfile

import numpy as np
import torch
import torch.nn as nn
import pytorch_lightning as pl

from .unet import Unet
from .data_sequence import get_datasets, Predict_sets

from TomoNet.util.io import log

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
        # Export to TorchScript
        model_scripted = torch.jit.script(self.model) 
        model_scripted.save(path) 

    def train(self, data_path, gpuID=[0,1,2,3], batch_size=None, 
              epochs = 10, steps_per_epoch=200, acc_batches =2,
              ncpus=8, precision=32, learning_rate=3e-4, enable_progress_bar=True):
        self.model.learning_rate = learning_rate

        train_batches = int(steps_per_epoch*0.9)
        val_batches = steps_per_epoch - train_batches
        
        if acc_batches > 1:
            batch_size = batch_size//acc_batches
            train_batches = train_batches * acc_batches
            val_batches = val_batches * acc_batches

        train_dataset, val_dataset = get_datasets(data_path)
        train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True, persistent_workers=True,
                                                num_workers=ncpus//2, pin_memory=True, drop_last=True)

        val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=True, persistent_workers=True,
                                                pin_memory=True, num_workers=ncpus//2, drop_last=True)
        
        self.model.train()
        if isinstance(gpuID, str):
            gpuID = list(map(int,gpuID.split(',')))
        
        if enable_progress_bar:
            callbacks = pl.callbacks.progress.ProgressBar(refresh_rate=5)
        else:
            callbacks = None
        
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
                            predicted.append(item)
            
            for i, mrc in enumerate(subset):
                root_name = mrc.split('/')[-1].split('.')[0]

                if iter_count == 0:
                    file_name = '{}/{}_pred.mrc'.format(result_dir, root_name)
                else:
                    file_name = '{}/{}_iter{:0>2d}.mrc'.format(result_dir, root_name, iter_count-1)
    
                with mrcfile.new(file_name, overwrite=True) as output_mrc:
                    temp = predicted[i]
                    tensor_temp = torch.from_numpy(temp)
                    temp = np.array(nn.Sigmoid()(tensor_temp))

                    p = 1/(10**filter_strength)
                    temp[temp < p] = 0
                    temp[temp >= p] = 1

                    output_mrc.set_data(temp)