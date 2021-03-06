import torch
from torch.utils.data import Dataset
import numpy as np
import random
import networkx as nx
import itertools as its
import collections as cls
import torch.nn.functional as F
import os

HOME = os.environ['HOME']

class Custom_dataset(Dataset):

    def __init__(self, dynamic='HR', n='cat', gc=0.2, length=10000, cat='train',noise_std = 0.2, seed=12, num=10,
                 past=3, future=1, dyn_dim=1 ):

        node_timeseries = np.load(
            HOME + '/cause/data/{0}/nodes={1}_timeseries_coupling={2}_md={3}_seed{4}.npy'.format(dynamic, n, gc, 0, seed)).astype(np.float32)
        node_timeseries = node_timeseries[:, :length, :dyn_dim] #[n,length,channels]

        np.random.seed(seed)
        noise_std = np.mean(np.abs(node_timeseries), axis=(0,1) ) * noise_std #[channels] # mean * density
        for c,std in enumerate(noise_std):
            noise = np.random.normal(loc=0, scale=std, size=node_timeseries[:,:,c].shape)
            node_timeseries[:,:,c] += noise


        node_timeseries_past = []
        node_timeseries_future = []
        for nt in node_timeseries: #[lenght,channels]
            temp, temp2 = [], []
            for i in range(past, length - future + 1):  # i从3开始
                temp.append(nt[i - past:i,:].reshape(-1))
                temp2.append(nt[i:i + future,:].reshape(-1))  # i是future的首位index
            node_timeseries_past.append(temp)
            node_timeseries_future.append(temp2)
        self.node_timeseries_past = np.array(node_timeseries_past)  # [ nodes, length-past-future+1,past*ch ]
        self.node_timeseries_future = np.array(node_timeseries_future)  # [ nodes, length-past-future+1,future*ch]
        self.node_timeseries = node_timeseries[:, past:length - future + 1,:]  # [ nodes, length-past-future+1 ,ch]
        self.length = length - past - future + 1
        print( self.node_timeseries.shape, self.length )

        test_num = int(1000 / 2)
        if n =='cat':
            fname = 'mixed.species_brain_1.graphml'
        if n == 'macaque':
            fname = 'rhesus_brain_2.graphml'
        if n == 'celegans':
            fname = 'c.elegans_neural.male_1.graphml'
        if n == 'rat':
            fname = 'rattus.norvegicus_brain_1.graphml'
        if n == 'mouse':
            fname = 'mouse_visual.cortex_2.graphml'
            test_num = int(180 / 2)
        if n == 'fly':
            fname = 'drosophila_medulla_1.graphml'

        g = nx.read_graphml(fname)
        mapping = dict(zip(g, range(0, len(g.nodes()) )))
        g = nx.relabel_nodes(g, mapping)
        self.adj = nx.to_numpy_array(g)  # adj
        self.adj[self.adj>1.0]=1 #remove the weight of edges

        if dynamic == 'FHN': #time series of FHN generated on nodes with degree<=1 may be error
            m = self.node_timeseries[:,:,0].max(axis=1)
            valid_node = np.where(m > 0)[0]
            g = g.subgraph(valid_node)
        edges = set( g.edges() )
        no_edges = set( its.permutations( g.nodes(),2 ) ) - edges
        edges, no_edges = np.array( list(edges) ),  np.array( list(no_edges) )
        # print(edges)

        np.random.seed(seed)
        edges = edges[np.random.choice(len(edges), num, replace=False)]
        # np.random.seed(seed)
        no_edges = no_edges[ np.random.choice( len(no_edges),int( len(edges)*1.0 ), replace=False  ) ]
        # self.no_edges = no_edges[np.random.choice(len(no_edges), num, replace=False)]

        if cat == 'train' or cat =='train2':
            self.pairs = np.concatenate([edges, no_edges], axis=0)
            self.edges = edges
            self.no_edges = no_edges
            if cat == 'train': #for att
                self.sample_length = 5000
            else: #cat =='train2' #for class
                if dynamic =='Izh':
                    self.sample_length = 300
                else:
                    self.sample_length = 2000

            self.sample_num = self.edges.shape[0]

            print('train_smaples_shape:{0}, gc:{1}, noise_std:{2}, edges:{3}, no_edges:{4} '.format(self.pairs.shape,
                                                                                                    gc,
                                                                                                    noise_std, edges,
                                                                                                    no_edges))


        else: #test
            have_edges = set( g.edges() ) - {tuple(i) for i in edges}
            havenot_edges = set(its.permutations( g.nodes(), 2 ) ) - set( g.edges() ) - {tuple(i) for i in no_edges}

            have_edges, havenot_edges = np.array(list(have_edges)), np.array(list(havenot_edges))

            np.random.seed(seed)
            # have_edges = have_edges[np.random.choice(len(have_edges), int(0.1*len(have_edges)), replace=False)]
            have_edges = have_edges[np.random.choice(len(have_edges), test_num, replace=False)]
            #np.random.seed(seed)
            # havenot_edges = havenot_edges[np.random.choice(len(havenot_edges), int(1.0*len(have_edges)), replace=False)]
            havenot_edges = havenot_edges[np.random.choice(len(havenot_edges), test_num, replace=False)]
            self.pairs = np.concatenate([have_edges, havenot_edges], axis=0)

            # self.pairs = np.concatenate([self.pairs, edges, no_edges], axis=0)
            self.sample_length = self.length
            # self.node_timeseries = torch.Tensor( self.node_timeseries )
            self.sample_num = len(self.pairs)
            print('test_smaples_shape:{0}, gc:{1}, noise_std:{2}'.format(self.pairs.shape, gc, noise_std,))



        print( 'sample_legnth;{0}'.format(self.sample_length) )
        self.cat =cat
        np.random.seed()




    def __getitem__(self, index ):

        if self.cat == 'train':
            index = np.random.choice(len(self.edges))
            n1, n2 = self.edges[index]

        elif self.cat == 'train2':
            index = np.random.choice(len(self.pairs))
            n1, n2 = self.pairs[index]

        else: #test
            n1, n2 = self.pairs[index]

        start = np.random.choice(self.length - self.sample_length + 1)
        # print(start)
        sample = np.transpose(self.node_timeseries[[n2, n1], start: start + self.sample_length,:], ( 2,0,1 ) )  # [2,sample_length,ch] -- [ch,2.sample_len]



        if self.cat == 'train':

            target_future = self.node_timeseries_future[n2,
                            start: start + self.sample_length].copy()  # ,[length-past-future,future]
            target_past = self.node_timeseries_past[n2, start: start + self.sample_length]
            source_past = self.node_timeseries_past[n1, start: start + self.sample_length]

            joint = np.concatenate([source_past, target_past, target_future], axis=1)
            # [l,past],[l,past],[l,future] -- [l,2p+f]
            joint2 = np.concatenate([target_past, target_future], axis=1)

            np.random.shuffle(target_future)  # [length-past-future+1,future]
            # indep = np.concatenate([self.node_timeseries_past[n2], target], axis=1)
            indep = np.concatenate([source_past, target_past, target_future], axis=1)
            # [l,10],[l,10],[l,1]
            indep2 = np.concatenate([target_past, target_future], axis=1)

            return sample, \
                   torch.Tensor(joint), torch.Tensor(indep), \
                   torch.Tensor(joint2), torch.Tensor(indep2)
        #
        else:

            return sample,  self.adj[n1,n2]



    def __len__(self):

        if self.cat == 'train' or  self.cat=='train2':
            return self.sample_num * 10
        elif self.cat == 'test' :
            return self.sample_num




