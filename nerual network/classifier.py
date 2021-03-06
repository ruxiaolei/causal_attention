import torch
import torch.nn as nn
import torch.nn.functional as F

#用于0，1标签训练，不加注意力
class classifier( nn.Module ):
    def __init__( self, in_dim=1 ):
        super( classifier, self ).__init__()

        self.cls = nn.Sequential(
            nn.Conv2d(in_channels=in_dim, out_channels=128, kernel_size=(2, 7), padding=(0, 3), stride=(1, 1)),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d( in_channels=128, out_channels=128, kernel_size=(1,15), padding=(0,7), stride=(1,1) ),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d( in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1) ),
            nn.BatchNorm2d( 128 ), nn.ReLU(),
            # nn.Conv2d( in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1) ),
            # nn.BatchNorm2d(128), nn.ReLU(),

            nn.Conv2d( in_channels=128, out_channels=1, kernel_size=(1, 1), padding=(0, 0), stride=(1, 1) ),
        )



    def forward( self, inputs):


        x = inputs  #[bs, channels, nodes, length ]

        logit = self.cls( x )

        # logit = torch.mean(logit, dim=-1)  # [2bs]

        return torch.squeeze( torch.squeeze( logit,dim=1 ), dim=1 ) #[bs, 1, 1,l] - [bs,l]








