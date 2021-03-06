import torch
# import torch.nn as nn
import torch.nn.functional as F
from load_data_tar import Custom_dataset
from torch.utils.data import DataLoader
import numpy as np
from traditional_attention_classifier import classifier
import collections as cls
from sklearn.metrics import roc_auc_score, accuracy_score, average_precision_score
import multiprocessing as mp
import networkx as nx
import os
import itertools as its


HOME = os.environ['HOME']



class my_model( ):

    def __init__(self,  dynamic ='HR',n=100,  gc=0.2,  length=10000 , noise_std=0.2, seed=12, num=5 ):

        self.lr = 1e-3
        self.batch_size = 10 #5000
        if dynamic == 'Morris':
            self.epoch = 1000
            self.dyn_dim = 1
        elif dynamic=='HR':
            self.epoch = 1000
            self.dyn_dim = 1
        elif dynamic == 'Izh':
            self.epoch = 1000
            self.dyn_dim = 1
        elif dynamic == 'Rulkov':
            self.epoch = 1000
            self.dyn_dim = 1
        elif dynamic == 'FHN':
            self.epoch = 1000
            self.dyn_dim = 1


        self.dynamic = dynamic
        self.gc = gc
        self.n = n
        self.length = length
        self.noise_std = noise_std
        self.seed = seed
        self.num=num

        self.path = HOME + '/cause/model_saver/{0}/trad_att/gc={1}/nodes={2}/noise_std={3}/seed={4}/length={5}' \
                           '/num={6}'.format(dynamic, gc, n, noise_std, seed, length, num)
        # self.path = HOME + '/cause/model_saver/{0}/trad_att/gc={1}/nodes={2}/noise_std={3}/seed={4}/length={5}' \
        #                    '/num={6}'.format(dynamic, gc, n,  noise_std, 0, length, num)
        if not os.path.exists(self.path):
            os.makedirs(self.path)




    def optimizer( self, model, model_name ):
        optimizer = torch.optim.Adam( model.parameters(), lr= self.lr, betas=(0.9,0.98), eps=1e-9 )#, weight_decay=5e-4 )
        checkpoint_dir = self.path + '/{0}.pth'.format( model_name )
        return optimizer, checkpoint_dir


    def loss( self,  logit, label ):
        return F.binary_cross_entropy_with_logits( logit, label )


    def load_model(self, model, optimizer, checkpoint_dir ):
        checkpoint = torch.load( checkpoint_dir )
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        step = checkpoint['epoch']
        return step


    def save_model(self, model, optimizer, epoch, checkpoint_dir  ):
        state = {'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'epoch': epoch }
        torch.save( state, checkpoint_dir )



    def train( self, load=False ):

        train_dataset = Custom_dataset( self.dynamic, gc=self.gc, n=self.n, cat='train'  , seed=self.seed,
                                        length=self.length, noise_std = self.noise_std, num=self.num, dyn_dim=self.dyn_dim ) #seed?????????percent????????????????????????
        train_loader = DataLoader(dataset=train_dataset, batch_size=self.batch_size, shuffle=True, num_workers=1,
                                  persistent_workers=True)  # , pin_memory=True )#, drop_last=True )
        test_dataset = Custom_dataset( self.dynamic, gc=self.gc, n=self.n, cat='test', seed=self.seed,
                                       length=self.length, noise_std = self.noise_std, num=self.num, dyn_dim=self.dyn_dim )  # seed?????????percent????????????????????????
        test_loader = DataLoader(dataset=test_dataset, batch_size=self.batch_size, num_workers=1,
                                 persistent_workers=True)  # , pin_memory=True )#, drop_last=True )



        c = classifier( in_dim=self.dyn_dim ).cuda()

        op_c_cp, cd_c_cp = self.optimizer( c, 'classifier' )


        if load:
            step = self.load_model( c, op_c_cp, cd_c_cp )
            print(step)
            pred, Label = [], []
            for sample, label in test_loader:  # sample [bs,2]
                sample = sample.to('cuda')  # [bs,2,indexs]
                # print( sample_batch.shape )
                logit, a = c(sample)

                pred.extend(torch.sigmoid(logit).detach().cpu().numpy())
                Label.extend(label.numpy())

            auc = roc_auc_score(np.array(Label), np.array(pred))
            auprc = average_precision_score(np.array(Label), np.array(pred))
            print('dynamic:{0} gc:{1} noise_std:{2} test auc:{3} test auprc:{4}'.format(self.dynamic,
                                                                                        self.gc,
                                                                                        self.noise_std,
                                                                                        auc, auprc))

            return auc, auprc
        else:
            step = 0


        for i in range(step, self.epoch + 1):
            LOSS = []
            pred, label = [], []
            for sample_batch, label_batch in train_loader:
                sample_batch = sample_batch.to('cuda')  # [bs,2,indexs]
                label_batch = label_batch.to('cuda')  # [bs]

                op_c_cp.zero_grad()

                # print( sample_batch.shape )
                logit, _ = c(sample_batch)

                loss = self.loss(logit, label_batch)  # , label_batch )
                loss.backward()

                op_c_cp.step()

                loss = loss.cpu().detach().numpy()

                LOSS.append(loss)
                pred.extend(torch.sigmoid(logit).detach().cpu().numpy())
                label.extend(label_batch.detach().cpu().numpy())

            LOSS = np.mean(LOSS)
            auc = roc_auc_score(np.array(label), np.array(pred))
            auprc = average_precision_score(np.array(label), np.array(pred))
            print(
                'dynamic:{0}  gc:{1} noise_std:{2} seed:{3} train epoch:{4} loss:{5} auc:{6} auprc:{7}'.format(
                    self.dynamic,
                    self.gc,
                    self.noise_std, self.seed,
                    i, LOSS, auc, auprc))

            if i % 100 == 0 and i > 0:

                pred, label = [], []
                for sample_batch, label_batch in test_loader:
                    sample_batch = sample_batch.to('cuda')  # [bs,2,indexs]
                    # print( sample_batch.shape )
                    logit, _ = c(sample_batch)
                    pred.extend(torch.sigmoid(logit).detach().cpu().numpy())
                    label.extend(label_batch.numpy())

                auc = roc_auc_score(np.array(label), np.array(pred))
                auprc = average_precision_score(np.array(label), np.array(pred))

                self.save_model(c, op_c_cp, i, cd_c_cp)

                print('dynamic:{0} gc:{1} noise_std:{2} test auc:{3} '
                      'auprc:{4}'.format(self.dynamic,  self.gc, self.noise_std, auc, auprc ))

        return auc, auprc




def run(gc=0.1, gpu_num=0, dynamic='HR', n=100, load=False, length=2000, noise_std=0.1, seed=12, num=10):

    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_num)
    model = my_model(dynamic=dynamic, n=n, gc=gc,  length=length, noise_std=noise_std, seed=seed, num=num)
    print(
        'dynamic:{0} gc:{1} noise_std:{2} seed:{3} num:{4} length:{5}'.format(dynamic, gc, noise_std,
                                                                              seed, num, length))
    auc, auprc = model.train(load)
    return auc, auprc






if __name__ == '__main__':
    NUM = { 'mouse':10, 'cat':10,'macaque':50, 'celegans':50, 'rat':100   }
    GC = {'HR': 0.1, 'Rulkov': 0.002, 'FHN': 0.1, 'Izh': 0.3, 'Morris': 0.5}

    for name in ['cat']:
        # for name in ['mouse']:
        # for name in ['macaque']:
        # for name in [ 'celegans' ]:
        # for name in ['rat']:
        num = NUM[name]

        AUC = cls.defaultdict(list)
        # for dyn in ['HR']:
        for dyn in ['Izh']:
            # for dyn in ['Rulkov']:
            # for dyn in ['FHN']:
            # for dyn in ['Morris']:
            # for dyn in [ 'HR','Izh','Rulkov', 'FHN','Morris' ]:
            gc = GC[dyn]

            for seed in range(5):
                auc, auprc = run(gc=gc, gpu_num=0, dynamic=dyn, length=50000, n=name, noise_std=0.1,
                                 load=False, seed=seed, num=num)
                # if name == 'rat':
                #     auc,auprc = run( gc=0.0008, gpu_num=0, dynamic='Rulkov', length=50000,  n=name,
                #                         noise_std=0.1, load=False, seed=seed , num=num)

                AUC[dyn].append([auc, auprc])

                print(AUC)