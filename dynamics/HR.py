import networkx as nx
import numpy as np
# import collections as cls
import matplotlib.pyplot as plt
import itertools as its
import os
from scipy.integrate import odeint
import scale_free_graph as sf

HOME = os.environ['HOME']

a = 1
b = 3
c = 1
d = 5
s = 4
r = 0.005
p0 = -1.6
I = 3.24
Osyn = 1
lam = 10
Vsyn1 = 2
Vsyn2 = -1.5





#生成节点关系图
def graph( md, n=20, seed=12 ):


    # g = nx.erdos_renyi_graph(n=n, p=md / (2 * (n - 1)), directed=True,
    #                          seed=seed)  # n=10,seed=1234: mean_dergree=4.4, seed=12: mean_dergree=3.8
    g = sf.scale_free( n, md, seed  )

    adj = nx.to_numpy_array( g ).T

    return g, adj


class dynamic(  ):

    def __init__(self):

        self. data= []


    def __call__(self, y, t,  adj, gc ):

        p, q, n = np.split(y ,3) #[n],[n],[n]

        Tp = 1 / (1 + np.exp(-lam * (p - Osyn)))
        cp = gc * ( Vsyn1- p  ) * ( adj.dot(Tp) ) # all are excited links
        # cp = gc * (Vsyn2 - p) * (adj.dot(Tp))  # all are inhibition links

        dp = q - a * (p ** 3) + b * (p ** 2) - n + I + cp #[n]
        dq = c - d * (p ** 2) - q
        dn = r * (s * (p - p0) - n)

        return np.concatenate( [dp, dq, dn ] )




def time_series( n, deltaT, gc, md ,seed ):

    g, adj = graph( md, n, seed )
    dy = dynamic()

    np.random.seed( seed )
    y0 = np.random.random_sample( 3*len(g) ) #[3n]
    t = np.linspace(0, 5500, 5500* int(1/deltaT) + 1 )
    ts = odeint( dy, y0, t, args=(adj, gc) )
    ts = ts[-5000 * int(1/deltaT):] #steady state
    ts = ts.reshape( -1, 3, len(g) ) #[t,3,n]
    ts = np.transpose(ts, [2, 0, 1])  # [ nodes, t, 3/4 ]
    print( ts.shape, ts[-1] )

    return ts, g#, np.array( dy.data )



#生成训练样本
def sample( n =100, deltaT=1., gc=0.4, md = 20, seed=12 ):

    print( n, deltaT, gc, md, seed )

    ts, g = time_series(n, deltaT, gc, md, seed=seed )


    # np.save( HOME + '/cause/data/HR/ER/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md,seed), ts )
    np.save(HOME + '/cause/data/HR/SF/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed), ts)




if __name__ == '__main__':

    for md in np.linspace( 5, 40 + 1, 10 ):

        for seed in range(10):

            sample( n=100, deltaT=0.1, gc=0.1, md = md, seed = seed )

