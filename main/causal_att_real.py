import torch
# import torch.nn as nn
import torch.nn.functional as F
from load_data_car import Custom_dataset
from torch.utils.data import DataLoader
import numpy as np
from classifier import classifier
from attention_model import attention
from MI_estimator import estimator
import collections as cls
from sklearn.metrics import roc_auc_score, accuracy_score, average_precision_score
import multiprocessing as mp
import networkx as nx
import os
import itertools as its
from torch.optim import lr_scheduler

HOME = os.environ['HOME']





class my_model():

    def __init__(self, dynamic='HR', n=100, gc=0.2, length=10000, noise_std=0.2, seed=12, num=10):

        self.batch_size_a = 10
        self.batch_size_c = 10
        if dynamic == 'Morris':
            self.epoch_att = 500
            self.epoch_cla = 2000
            self.lr_a = 1e-4  # self.lr*(1/self.lammda)
            self.lr_c = 1e-3
            self.dyn_dim = 1
        elif dynamic == 'HR':
            self.epoch_att = 500#1000
            self.epoch_cla = 2000
            self.lr_a = 1e-4  # self.lr*(1/self.lammda)
            self.lr_c = 1e-3
            self.dyn_dim = 1
        elif dynamic == 'Izh':
            self.epoch_att = 500#1000
            self.epoch_cla = 2000
            self.lr_a = 1e-4  # self.lr*(1/self.lammda)
            self.lr_c = 1e-3
            self.dyn_dim = 1
        elif dynamic == 'Rulkov':
            self.epoch_att = 500
            self.epoch_cla = 2000
            self.lr_a = 1e-4  # self.lr*(1/self.lammda)
            self.lr_c = 1e-3
            self.dyn_dim = 1
            self.TE_thre = 1.
        elif dynamic == 'FHN':
            self.epoch_att = 500
            self.epoch_cla = 2000
            self.lr_a =1e-4   # self.lr*(1/self.lammda)
            self.lr_c = 1e-3
            self.dyn_dim = 1


        self.dynamic = dynamic
        self.gc = gc
        self.n = n
        self.length = length
        self.noise_std = noise_std
        self.seed = seed
        self.num = num

        self.past = 3
        self.future = 1


        self.path = HOME + '/cause/model_saver/{0}/causal_att/gc={1}/nodes={2}/noise_std={3}/seed={4}/length={5}/num={6}'.format(
            dynamic, gc, n, noise_std, seed, length, num)

        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def optimizer(self, model, model_name, lr):
        optimizer = torch.optim.Adam(model.parameters(), lr=lr, betas=(0.9, 0.98), eps=1e-9)  # , weight_decay=5e-4 )
        checkpoint_dir = self.path + '/{0}.pth'.format(model_name)
        return optimizer, checkpoint_dir

    def C_loss(self, logit, label):
        return F.binary_cross_entropy_with_logits(logit, label)

    def KL_loss(self, logit_joint, logit_indep, att):  # , label ):
        logit_joint = torch.mean(logit_joint * att, dim=-1)
        logit_indep = torch.log(torch.mean(torch.exp(logit_indep * att), dim=-1) + 1e-12)
        KL = logit_joint - logit_indep  # eq(12)
        return KL
        # return logit_joint, logit_indep

    def load_model(self, model, optimizer, checkpoint_dir):
        checkpoint = torch.load(checkpoint_dir)
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        step = checkpoint['epoch']
        return step

    def save_model(self, model, optimizer, epoch, checkpoint_dir):
        state = {'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'epoch': epoch}
        torch.save(state, checkpoint_dir)

    def train(self,load):

        train_dataset = Custom_dataset(self.dynamic, gc=self.gc, n=self.n, cat='train', seed=self.seed,
                                       length=self.length, noise_std=self.noise_std,
                                       num=self.num, past=self.past, future=self.future, dyn_dim=self.dyn_dim )  # seed?????????percent????????????????????????
        train_loader = DataLoader(dataset=train_dataset, batch_size=self.batch_size_a, shuffle=True, num_workers=1,
                                  persistent_workers=True)  # , pin_memory=True )#, drop_last=True )

        self.a = attention(self.dyn_dim).cuda()
        d = estimator(in_dim=self.past*self.dyn_dim * 2 + self.future*self.dyn_dim).cuda()
        d2 = estimator(in_dim=self.past*self.dyn_dim  + self.future*self.dyn_dim ).cuda()

        op_a, cd_a = self.optimizer(self.a, 'attention', self.lr_a)
        scheduler_a = lr_scheduler.ExponentialLR(op_a, gamma=0.999)
        op_d, cd_d = self.optimizer(d, 'mi_estimator1', self.lr_a)
        scheduler_d = lr_scheduler.ExponentialLR(op_d, gamma=0.999)
        op_d2, cd_d2 = self.optimizer(d2, 'mi_estimator2', self.lr_a)
        scheduler_d2 = lr_scheduler.ExponentialLR(op_d2, gamma=0.999)

        if load:
            step = self.load_model(self.a, op_a, cd_a)
            _ = self.load_model( d, op_d,  cd_d)
            _ = self.load_model( d2, op_d,  cd_d2)
            print( 'load_step:{0}'.format(step) )

            return

        else:
            step = 1

        TE_his = []
        for i in range(step, self.epoch_att + 1):
            TE, CF, ATT = [], [], []
            for sample, joint, indep, joint2, indep2 in train_loader:  # sample [bs,2]
                sample = sample.to('cuda')  # [bs,ch,2,l]
                joint = joint.to('cuda')  # [bs,l,21]
                indep = indep.to('cuda')  # [bs,l,21]
                joint2 = joint2.to('cuda')  # [bs,l,11]
                indep2 = indep2.to('cuda')  # [bs,l,11]

                op_d.zero_grad(), op_d2.zero_grad()
                with torch.no_grad():
                    att = self.a(sample)  # [bs, l]
                cp = torch.cat([joint, indep], dim=0)
                logit_cp = d(cp)  # [2bs,l]
                # print( logit_cp.shape )
                logit_cp_joint, logit_cp_indep = logit_cp[:joint.shape[0]], logit_cp[-joint.shape[
                    0]:]  # [bs,l],[bs,le]
                sf = torch.cat([joint2, indep2], dim=0)
                logit_sf = d2(sf)
                logit_sf_joint, logit_sf_indep = logit_sf[:joint2.shape[0]], logit_sf[
                                                                             -joint2.shape[0]:]  # [bs,l]

                indep_cp = (logit_cp_indep < 70)
                indep_sf = (logit_sf_indep < 70)
                logit_cp_joint = logit_cp_joint[indep_cp]  # [bs,length2]
                logit_cp_indep = logit_cp_indep[indep_cp ]  # [bs,length2]
                logit_sf_joint = logit_sf_joint[indep_sf ]
                logit_sf_indep = logit_sf_indep[indep_sf ]

                # KL_cp = self.KL_loss(logit_cp_joint, logit_cp_indep, att[:joint.shape[0]][indep_cp])  # , label_batch )
                # KL_sf = self.KL_loss(logit_sf_joint, logit_sf_indep, att[:joint.shape[0]][indep_sf])  # , label_batch )
                KL_cp = self.KL_loss(logit_cp_joint, logit_cp_indep, att[indep_cp])  # , label_batch )
                KL_sf = self.KL_loss(logit_sf_joint, logit_sf_indep, att[indep_sf])  # , label_batch )

                KL_cp = KL_cp[ torch.isfinite( KL_cp ) ]
                KL_sf = KL_sf[ torch.isfinite(KL_sf) ]

                loss = -(torch.mean(KL_cp) + torch.mean(KL_sf))  #

                loss.backward()
                op_d.step(), op_d2.step()

                op_a.zero_grad()#
                att = self.a(sample)  # [2bs, length ]

                with torch.no_grad():
                    logit_cp = d(cp)  # [2bs,l]
                    logit_sf = d2(sf)

                logit_cp_joint, logit_cp_indep = logit_cp[:joint.shape[0]], logit_cp[-joint.shape[0]:]
                logit_sf_joint, logit_sf_indep = logit_sf[:joint2.shape[0]], logit_sf[
                                                                             -joint2.shape[0]:]  # [bs,length-10]

                indep = (logit_cp_indep < 70) & (logit_sf_indep < 70)
                logit_cp_joint = logit_cp_joint[indep]
                logit_cp_indep = logit_cp_indep[indep]
                logit_sf_joint = logit_sf_joint[indep]
                logit_sf_indep = logit_sf_indep[indep]
                KL_cp = self.KL_loss(logit_cp_joint, logit_cp_indep, att[indep])
                KL_sf = self.KL_loss(logit_sf_joint, logit_sf_indep, att[indep])

                finite = torch.isfinite(KL_cp) & torch.isfinite(KL_sf)
                KL_cp = KL_cp[finite]
                KL_sf = KL_sf[finite]

                te = torch.mean(KL_cp - KL_sf)  # transfer entropy

                loss = -te
                loss.backward( )
                op_a.step()

                TE.append(te.cpu().detach().numpy())
                ATT.append( torch.mean(att).cpu().detach().numpy()  )


            TE = np.mean(TE)
            ATT = np.mean( ATT )
            TE_his.append( TE )

            scheduler_a.step(), scheduler_d.step(), scheduler_d2.step()

            print(
                'dynamic:{0} meandegree:{1} gc:{2} noise_std:{3} seed:{4} train epoch:{5} TE:{6} att:{7}'.format(
                    self.dynamic,
                    self.md, self.gc,
                    self.noise_std, self.seed,
                    i, TE,  ATT))

            if i%100 == 0:
                self.save_model(self.a, op_a, i, cd_a)
                self.save_model(d, op_d, i, cd_d)
                self.save_model(d2, op_d, i, cd_d2)

            # if i == self.epoch_att or ( np.array(TE_his[-20:]) > self.TE_thre ).all()  and ATT< self.ATT_max and  ATT>self.ATT_min:
            #     self.save_model(self.a, op_a, i, cd_a)
            #     self.save_model(d, op_d, i, cd_d)
            #     self.save_model(d2, op_d, i, cd_d2)
            #     return

    def train2( self, load=False ):
        train_dataset = Custom_dataset(self.dynamic, gc=self.gc, n=self.n, cat='train2', seed=self.seed,
                                       length=self.length, noise_std=self.noise_std,
                                       num=self.num, past=self.past, future=self.future,
                                       dyn_dim=self.dyn_dim)  #
        train_loader = DataLoader(dataset=train_dataset, batch_size=self.batch_size_c, shuffle=True, num_workers=1,
                                  persistent_workers=True)  # , pin_memory=True )#, drop_last=True )
        test_dataset = Custom_dataset(self.dynamic, gc=self.gc, n=self.n, cat='test', seed=self.seed,
                                      length=self.length, noise_std=self.noise_std,
                                      num=self.num, past=self.past, future=self.future,
                                      dyn_dim=self.dyn_dim)  #
        test_loader = DataLoader(dataset=test_dataset, batch_size=5, num_workers=1,
                                 persistent_workers=True)  # , pin_memory=True )#, drop_last=True )


        self.c = classifier(in_dim=self.dyn_dim).cuda()
        op_c, cd_c = self.optimizer(self.c, 'classifier2', self.lr_c)


        if load:
            step = self.load_model(self.c, op_c, cd_c )
            print(step)

            pred, Label = [], []
            for sample, label in test_loader:
                sample = sample.to('cuda')
                att = self.a(sample)
                logit = self.c(sample)
                logit = torch.sum(logit * att, dim=-1)

                pred.extend(torch.sigmoid(logit).detach().cpu().numpy())
                Label.extend(label.numpy())

            Label, pred = np.array(Label), np.array(pred)
            print(Label, pred)
            auc_best = roc_auc_score(np.array(Label), np.array(pred))
            auprc_best = average_precision_score(np.array(Label), np.array(pred))

            return auc_best, auprc_best


        for i in range(1,self.epoch_cla + 1):
            TE, CF = [], []
            pred, Label = [], []
            for sample, label in train_loader:  # sample [bs,2]
                sample = sample.to('cuda')  # [bs,2,indexs]
                label = label.to('cuda')  # [bs,2,indexs]
                # print( sample_batch.shape )

                op_c.zero_grad()
                with torch.no_grad():
                    att = self.a(sample)  # [2bs, length ]
                logit = self.c(sample)  # [2bs,l]
                logit = torch.sum(logit * att, dim=-1)
                cf = self.C_loss(logit, label)  # #ce loss

                loss = cf  #
                loss.backward()
                op_c.step()

                CF.append(cf.cpu().detach().numpy())
                pred.extend(torch.sigmoid(logit).detach().cpu().numpy())
                Label.extend(label.detach().cpu().numpy())

            # LOSS = np.mean(LOSS)
            CF = np.mean(CF)
            auc = roc_auc_score(np.array(Label), np.array(pred))
            auprc = average_precision_score(np.array(Label), np.array(pred))
            print(
                'dynamic:{0} meandegree:{1} gc:{2} noise_std:{3} seed:{4} train epoch:{5} CF:{6} auc:{7} auprc:{8}'.format(
                    self.dynamic,
                    self.md, self.gc,
                    self.noise_std, self.seed,
                    i, CF, auc, auprc))

            if i % 100 == 0 and i > 0:
                # if i == self.epoch:
                pred, Label = [], []
                for sample, label in test_loader:  # sample [bs,2]
                    sample = sample.to('cuda')  # [bs,2,indexs]
                    # print( sample_batch.shape )
                    att = self.a(sample)
                    logit = self.c(sample)
                    logit = torch.sum(logit * att, dim=-1)
                    # logit = torch.mean( logit* att, dim=-1 )

                    pred.extend(torch.sigmoid(logit).detach().cpu().numpy())
                    Label.extend(label.numpy())


                Label, pred = np.array(Label), np.array(pred)
                print(Label, pred)
                auc = roc_auc_score(np.array(Label), np.array(pred))
                auprc = average_precision_score(np.array(Label), np.array(pred))
                self.save_model(self.c, op_c, i, cd_c)

                print('dynamic:{0} meandegree:{1} gc:{2} noise_std:{3} test auc:{4} '
                      'auprc:{5}'.format(self.dynamic, self.md, self.gc, self.noise_std, auc, auprc))


        return auc, auprc



def run(gc=0.1, gpu_num=0, dynamic='HR', n=100, load=False, length=2000, noise_std=0.1, seed=12, num=10):
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_num)

    model = my_model(dynamic=dynamic, n=n, gc=gc, length=length, noise_std=noise_std, seed=seed, num=num)
    print(
        'dynamic:{0} gc:{1} noise_std:{2} seed:{3} num:{4} length:{5}'.format(dynamic, gc, noise_std,
                                                                                             seed, num, length))

    model.train(load)
    auc, auprc = model.train2(load)

    return auc, auprc



if __name__ == '__main__':
    NUM = { 'mouse':10, 'cat':10,'macaque':50, 'celegans':50, 'rat':100   }
    GC = {'HR': 0.1, 'Rulkov': 0.002, 'FHN': 0.1, 'Izh': 0.3, 'Morris': 0.5}
    # for name in ['cat','macaque', 'celegans', 'rat']:#'mouse',
    for name in ['mouse']:
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
                auc, auprc = run( gc=gc,  gpu_num=0, dynamic=dyn, length=50000,  n=name, noise_std=0.1,
                                      load=False, seed=seed, num=num )
                # if name == 'rat':
                #     auc,auprc = run( gc=0.0008, gpu_num=0, dynamic='Rulkov', length=50000,  n=name,
                #                         noise_std=0.1, load=False, seed=seed , num=num)

                AUC[dyn].append([auc, auprc])

                print( AUC )
