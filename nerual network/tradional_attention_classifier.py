import torch
import torch.nn as nn
import torch.nn.functional as F


class classifier( nn.Module ):
    def __init__( self, in_dim=1 ):
        super( classifier, self ).__init__()

        self.cls = nn.Sequential(
            nn.Conv2d( in_channels=in_dim, out_channels=128, kernel_size=(2, 7), padding=(0, 3), stride=(1, 1) ),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d( in_channels=128, out_channels=128, kernel_size=(1,15), padding=(0,7), stride=(1,1) ),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d( in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1) ),
            nn.BatchNorm2d( 128 ), nn.ReLU(),
            # nn.Conv2d( in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1) ),
            # nn.BatchNorm2d(128), nn.ReLU(),

            nn.Conv2d( in_channels=128, out_channels=1, kernel_size=(1, 1), padding=(0, 0), stride=(1, 1) )
        )
        #CBAM
        self.att = nn.Sequential(
            nn.Conv2d(in_channels=in_dim, out_channels=128, kernel_size=(2, 7), padding=(0, 3), stride=(1, 1)),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1)),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1)),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1)),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1)),
            nn.BatchNorm2d(128), nn.ReLU(),
            # nn.Conv2d(in_channels=128, out_channels=128, kernel_size=(1, 15), padding=(0, 7), stride=(1, 1)),
            # nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(in_channels=128, out_channels=1, kernel_size=(1, 1), padding=(0, 0), stride=(1, 1)),
            nn.Sigmoid()
        )



    def forward( self, inputs ):

        x = inputs  #[bs, channels, nodes, length ]

        a = self.att(x)  #[bs,1,1,lenght]
        x = self.cls( x )
        logit = torch.mean(  a * x , dim=-1)

        return torch.squeeze( torch.squeeze( logit,dim=1 ), dim=1 ),\
               torch.squeeze( torch.squeeze( a,dim=1 ), dim=1 ) #[bs,1,1]-[bs], [bs, 1, 1,l] - [bs,l]








