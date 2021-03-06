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

    def __init__(self, dynamic='HR', n=200, gc=0.2,  length=10000, cat='train',noise_std = 0.1,  seed=12, num=10, dyn_dim=1 ):

        node_timeseries = np.load(
            HOME + '/cause/data/{0}/nodes={1}_timeseries_coupling={2}_md={3}_seed{4}.npy'.format(dynamic, n, gc, 0, seed))
        node_timeseries = node_timeseries[:, :length, :dyn_dim]


        np.random.seed(seed)
        noise_std = np.mean(np.abs(node_timeseries), axis=(0,1) ) * noise_std #[channels] # mean * density
        for c,std in enumerate(noise_std):
            noise = np.random.normal(loc=0, scale=std, size=node_timeseries[:,:,c].shape)
            node_timeseries[:,:,c] += noise


        test_num = int(1000 / 2)
        if n == 'cat':
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
        mapping = dict(zip(g, range(0, len(g.nodes()))))
        g = nx.relabel_nodes(g, mapping)
        self.adj = nx.to_numpy_array(g)  # adj
        self.adj[self.adj>1] =1 #remove the weight of edges

        if dynamic == 'FHN': #time series of FHN generated on nodes with degree<=1 may be error
            m = node_timeseries[:,:,0].max(axis=1)
            valid_node = np.where(m > 0)[0]
            g = g.subgraph(valid_node)

        edges = set( g.edges() )
        no_edges = set( its.permutations( g.nodes(),2 ) ) - edges
        edges, no_edges = np.array( list(edges) ),  np.array( list(no_edges) )
        # print(edges)

        self.node_timeseries = torch.Tensor( np.transpose(node_timeseries, (2,0,1) ) )  # [channels,nodes,length]


        np.random.seed(seed)
        edges = edges[np.random.choice(len(edges), num, replace=False)]
        #np.random.seed( seed )
        no_edges = no_edges[ np.random.choice( len(no_edges),int( len(edges)*1.0 ), replace=False  ) ]
        # self.no_edges = no_edges[np.random.choice(len(no_edges), num, replace=False)]


        if cat == 'train':
            self.pairs = np.concatenate([edges, no_edges], axis=0)

            print('train_smaples_shape:{0}, gc:{1}, noise_std:{2}, edges:{3}, no_edges:{4} '.format(
                self.pairs.shape,
                gc,
                noise_std, edges,
                no_edges))

        else:


            have_edges = set( g.edges() ) - {tuple(i) for i in edges}
            havenot_edges = set(its.permutations( g.nodes(), 2 ) ) - set( g.edges() ) - {tuple(i) for i in no_edges}

            have_edges, havenot_edges = np.array(list(have_edges)), np.array(list(havenot_edges))

            np.random.seed(seed)
            # have_edges = have_edges[np.random.choice(len(have_edges), int(0.1*len(have_edges)), replace=False)]
            have_edges = have_edges[np.random.choice(len(have_edges), test_num, replace=False)]

            #np.random.seed(seed)
            havenot_edges = havenot_edges[np.random.choice(len(havenot_edges), test_num, replace=False)]

            self.pairs = np.concatenate([have_edges, havenot_edges], axis=0)
            print(
                'test_smaples_shape:{0}, gc:{1}, noise_std:{2}, '.format(self.pairs.shape, gc,  noise_std, ))


        self.sample_num = self.pairs.shape[0]
        self.length = length

        np.random.seed()

        # print('expermeint_sample_num:{0}'.format( self.sample_num ) )





    def __getitem__(self, index ):

        # index  = np.random.choice( self.sample_num )
        n1,n2 = self.pairs[index]

        sample  = self.node_timeseries[:,[n2,n1],:] # [channel,2,lenght]

        return sample, self.adj[n1,n2]



    def __len__(self):

        return self.sample_num #* 10




