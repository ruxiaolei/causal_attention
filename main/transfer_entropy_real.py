import torch
from load_data_ter import Custom_dataset
from torch.utils.data import DataLoader
import numpy as np
from MI_estimator import estimator
import collections as cls
from sklearn.metrics import roc_auc_score, accuracy_score, average_precision_score
import os


HOME = os.environ['HOME']




class my_model( ):

    def __init__(self,  dynamic ='HR',n='cat',  gc=0.2, length=10000,  noise_std=0.2, seed=12 ):

        self.batch_size = 10
        self.dyn_dim = 1

        if dynamic == 'FHN':
            self.epoch = 30
            self.lr = 1e-4
        elif dynamic=='HR':
            self.epoch = 30
            self.lr = 1e-4
        elif dynamic=='Izh':
            self.epoch = 30
            self.lr = 1e-4
        elif dynamic =='Rulkov':
            self.epoch = 30
            self.lr = 1e-4
        elif dynamic =='Morris':
            self.epoch = 30
            self.lr = 1e-4

        self.dynamic = dynamic
        self.gc = gc
        self.n = n
        self.length = length
        self.noise_std = noise_std
        self.seed = seed

        self.past = 3
        self.future = 1


        self.path = HOME + '/cause/model_saver/{0}/Transfer_Entropy/gc={1}/nodes={2}/noise_std={3}/seed={4}'.format(
            dynamic, gc, n,  noise_std, seed)

        if not os.path.exists(self.path):
            os.makedirs(self.path)


    def optimizer( self, model, model_name ):
        optimizer = torch.optim.Adam( model.parameters(), lr= self.lr, betas=(0.9,0.98), eps=1e-9 )#, weight_decay=5e-4 )
        checkpoint_dir = self.path + '/{0}.pth'.format( model_name )
        return optimizer, checkpoint_dir




    def KL_loss( self,  logit_joint, logit_indep ):
        logit_joint = torch.mean( logit_joint , dim=-1 )
        logit_indep = torch.log( torch.mean( torch.exp(logit_indep  ) ,dim=-1) )
        KL = logit_joint - logit_indep
        return KL



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

        test_dataset = Custom_dataset( self.dynamic, gc=self.gc, n=self.n, cat='test', seed=self.seed,
                                       length=self.length, noise_std = self.noise_std  )
        test_loader = DataLoader(dataset=test_dataset, batch_size=self.batch_size, num_workers=1,
                                 persistent_workers=True,shuffle=True,)  # , pin_memory=True )#, drop_last=True )

        d = estimator(in_dim=self.past * self.dyn_dim * 2 + self.future * self.dyn_dim).cuda()
        d2 = estimator(in_dim=self.past * self.dyn_dim + self.future * self.dyn_dim).cuda()

        op_d, cd_d = self.optimizer(d, 'mi_estimator1')
        op_d2, cd_d2 = self.optimizer(d2, 'mi_estimator2')


        if load:
            step = self.load_model( d, op_d, cd_d )
            step = self.load_model(d2, op_d2, cd_d2)
            print(step)
            TE, Label = [], []
            for joint, indep, joint2, indep2, label in test_loader:  # sample [bs,2]
                joint = joint.to('cuda')  # [bs,l,2p+f]
                indep = indep.to('cuda')  # [bs,l,2p+f]
                joint2 = joint2.to('cuda')  # [bs,l,p+f]
                indep2 = indep2.to('cuda')  # [bs,l,p+f]

                op_d.zero_grad(), op_d2.zero_grad()
                cp = torch.cat([joint, indep], dim=0)
                logit_cp = d(cp)  # [2bs,l]
                logit_cp_joint, logit_cp_indep = logit_cp[:joint.shape[0]], logit_cp[-joint.shape[0]:]  # [bs,l],[bs,length-10]
                sf = torch.cat([joint2, indep2], dim=0)
                logit_sf = d2(sf)
                logit_sf_joint, logit_sf_indep = logit_sf[:joint2.shape[0]], logit_sf[-joint2.shape[0]:]  # [bs,l]
                KL_cp = self.KL_loss(logit_cp_joint, logit_cp_indep)  # , label_batch )
                KL_sf = self.KL_loss(logit_sf_joint, logit_sf_indep)  # , label_batch )
                te = KL_cp - KL_sf
                TE.extend( te.cpu().detach().numpy() )
                Label.extend( label.numpy() )
            auc = roc_auc_score(np.array(Label), np.array(TE))
            auprc = average_precision_score(np.array(Label), np.array(TE))
            return auc, auprc

        else:
            step = 1



        for i in range( step, self.epoch+1 ):
            TE= []
            Label = []
            for joint, indep, joint2, indep2, label in test_loader:  # sample [bs,2]
                joint = joint.to('cuda')  # [bs,l,2p+f]
                indep = indep.to('cuda')  # [bs,l,2p+f]
                joint2 = joint2.to('cuda')  # [bs,l,p+f]
                indep2 = indep2.to('cuda')  # [bs,l,p+f]


                op_d.zero_grad(), op_d2.zero_grad()
                cp = torch.cat([joint, indep], dim=0)
                logit_cp = d(cp)  # [2bs,l]
                # print( logit_cp.shape )
                logit_cp_joint, logit_cp_indep = logit_cp[:joint.shape[0]], logit_cp[-joint.shape[0]:]  # [bs,l],[bs,length-10]
                sf = torch.cat([joint2, indep2], dim=0)
                logit_sf = d2(sf)
                logit_sf_joint, logit_sf_indep = logit_sf[:joint2.shape[0]], logit_sf[-joint2.shape[0]:]  # [bs,l]
                KL_cp = self.KL_loss(logit_cp_joint, logit_cp_indep)  # , label_batch )
                KL_sf = self.KL_loss(logit_sf_joint, logit_sf_indep)  # , label_batch )
                loss = -torch.mean( KL_cp + KL_sf )
                loss.backward()
                op_d.step(), op_d2.step()

                te = KL_cp - KL_sf

                TE.extend( te.cpu().detach().numpy() )
                Label.extend(label.numpy())

            # print( np.unique( np.array(Label) ))
            auc = roc_auc_score(np.array(Label), np.array(TE))
            auprc = average_precision_score(np.array(Label), np.array(TE))
            TE = np.mean(TE)
            print('dynamic:{0} gc:{1} noise_std:{2} seed:{3} train epoch:{4} TE:{5} auc:{6}'.format( self.dynamic,
                                                                                                     self.gc,
                                                                                                     self.noise_std, self.seed,
                                                                                                     i, TE, auc ) )


        self.save_model(d, op_d, i, cd_d)
        self.save_model(d2, op_d2, i, cd_d2)

        return auc, auprc




def run( gc=0.1,  gpu_num=0, dynamic='HR', n='cat',  load=False, length=2000 , noise_std = 0.1, seed=12 ):

    os.environ["CUDA_VISIBLE_DEVICES"] = str( gpu_num )
    model = my_model( dynamic=dynamic, n=n, gc=gc, length=length, noise_std = noise_std, seed = seed )

    print(
        'dynamic:{0} n:{1} gc:{2} noise_std:{3} seed:{4} length:{5}'.format(dynamic, n, gc, noise_std,
                                                                       seed,  length))
    auc, auprc = model.train(load )
    return auc, auprc





if __name__ == '__main__':

    GC = {'HR': 0.1, 'Rulkov': 0.002, 'FHN': 0.1, 'Izh': 0.3, 'Morris': 0.5}
    # for name in ['cat', 'macaque', 'celegans', 'rat']:  # 'mouse',
    for name in ['cat','mouse','macaque']:
        # for name in ['mouse']:
        # for name in ['macaque']:
        # for name in [ 'celegans' ]:
        # for name in ['rat']:

        AUC = cls.defaultdict(list)
        # for dyn in ['HR']:
        # for dyn in ['Izh']:
            # for dyn in ['Rulkov']:
            # for dyn in ['FHN']:
            # for dyn in ['Morris']:
        for dyn in [ 'HR','Izh','Rulkov', 'FHN','Morris' ]:
            gc = GC[dyn]

            for seed in range(1):
                if name == 'rat' and dyn=='Rulkov':
                    auc,auprc = run( gc=0.0008, gpu_num=0, dynamic='Rulkov', length=50000,  n=name,
                                     noise_std=0.1, load=False, seed=seed )
                else:
                    auc, auprc = run(gc=gc, gpu_num=0, dynamic=dyn, length=50000, n=name, noise_std=0.1,
                                     load=False, seed=seed)

                AUC[dyn].append([auc, auprc])

                print(AUC)



    print( AUC)