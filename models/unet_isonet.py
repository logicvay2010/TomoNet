from typing import List
import torch
import torch.nn as nn
import pytorch_lightning as pl

class ConvBlock(pl.LightningModule):
    def __init__(self, in_channels, out_channels, n_conv, kernel_size=3, stride=1, padding=1):
        super(ConvBlock, self).__init__()
        layers = [
            nn.Conv3d(in_channels=in_channels, out_channels=out_channels,
                    kernel_size=kernel_size, stride=stride, padding=padding, bias=True), 
            #nn.InstanceNorm3d(num_features = out_channels),
            nn.BatchNorm3d(num_features=out_channels),
            nn.LeakyReLU(),
        ]
        for _ in range(max(n_conv-1, 0)):
            layers.append(nn.Conv3d(in_channels=out_channels, out_channels=out_channels,
                    kernel_size=kernel_size, stride=stride, padding=padding, bias=True))
            #layers.append(nn.InstanceNorm3d(num_features = out_channels))
            layers.append(nn.BatchNorm3d(num_features=out_channels))
            layers.append(nn.LeakyReLU())

        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)

class EncoderBlock(pl.LightningModule):
    def __init__(self, filter_base, unet_depth, n_conv):
        super(EncoderBlock, self).__init__()
        self.module_dict = nn.ModuleDict()
        self.module_dict['first_conv'] = nn.Conv3d(in_channels=1, out_channels=filter_base[0], kernel_size=3, stride=1, padding=1)

        for n in range(unet_depth):
            self.module_dict["conv_stack_{}".format(n)] = ConvBlock(in_channels=filter_base[n], out_channels=filter_base[n], n_conv=n_conv)
            self.module_dict["stride_conv_{}".format(n)] = ConvBlock(in_channels=filter_base[n], out_channels=filter_base[n+1], n_conv=1, kernel_size=2, stride=2, padding=0)
        
        self.module_dict["bottleneck"] = ConvBlock(in_channels=filter_base[n+1], out_channels=filter_base[n+1], n_conv=n_conv-1)
    
    def forward(self, x):
        down_sampling_features = []
        for k, op in self.module_dict.items():
            x = op(x)
            if k.startswith('conv'):
                down_sampling_features.append(x)
        return x, down_sampling_features

class DecoderBlock(pl.LightningModule):
    def __init__(self, filter_base, unet_depth, n_conv):
        super(DecoderBlock, self).__init__()
        self.module_dict = nn.ModuleDict()
        for n in reversed(range(unet_depth)):
            self.module_dict["deconv_{}".format(n)] = nn.ConvTranspose3d(in_channels=filter_base[n+1],
                                                                         out_channels=filter_base[n],
                                                                         kernel_size=2,
                                                                         stride=2,
                                                                         padding=0)
            self.module_dict["activation_{}".format(n)] = nn.LeakyReLU()
            self.module_dict["conv_stack_{}".format(n)] = ConvBlock(filter_base[n]*2, filter_base[n],n_conv=n_conv)
        
    def forward(self, x,
        down_sampling_features: List[torch.Tensor]):
        for k, op in self.module_dict.items():
            x=op(x)
            if k.startswith("deconv"):
                x = torch.cat((down_sampling_features[int(k[-1])], x), dim=1)
        return x

class Unet(pl.LightningModule):
    def __init__(self, filter_base = 64, out_channels=1, learning_rate = 3e-4, add_last=False, metrics=None):
        super(Unet, self).__init__()
        self.add_last = add_last
        if filter_base == 64:
            filter_base = [64,128,256,320,320,320]
        elif filter_base == 32:
            filter_base = [32,64,128,256,320,320]
        elif filter_base == 16:
            filter_base = [16,32,64,128,256,320]
        
        unet_depth = 3
        n_conv = 3
        self.encoder = EncoderBlock(filter_base=filter_base, unet_depth=unet_depth, n_conv=n_conv)
        self.decoder = DecoderBlock(filter_base=filter_base, unet_depth=unet_depth, n_conv=n_conv)
        self.final = nn.Conv3d(in_channels=filter_base[0], out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        
        self.learning_rate = learning_rate
        if metrics is None:
            self.metrics = {'train_loss':[], 'val_loss':[]}
        else:
            self.metrics = metrics
    
    def forward(self, x):
        x_org = x
        x, down_sampling_features = self.encoder(x)
        x = self.decoder(x, down_sampling_features)
        y_hat = self.final(x)
        if self.add_last:
            y_hat += x_org
        return y_hat

    def training_step(self, batch, batch_idx):
        x, y = batch
        out = self(x)
        loss = nn.L1Loss()(out, y)
        return loss
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(self.parameters(), lr=self.learning_rate)
        return optimizer 

    def validation_step(self, batch, batch_idx):
        with torch.no_grad():
            x, y = batch
            out = self(x)
            loss = nn.L1Loss()(out, y)
            return loss
    
    def training_epoch_end(self, outputs):
        loss = torch.stack([x['loss'] for x in outputs]).mean().item()
        self.metrics["train_loss"].append(loss)
 
    def validation_epoch_end(self, outputs):
        loss = torch.stack(outputs).mean().item()
        self.metrics["val_loss"].append(loss)
        self.log("val_loss", loss, prog_bar=True, on_epoch=True)