import networkx as nx
import numpy as np
# import collections as cls
import itertools as its
import os
from scipy.integrate import odeint
import scale_free_graph as sf

HOME = os.environ['HOME']

beta = 4.4
v = 0.001
o = 0.001

Vs = 20
Osyn = 0.25
lam = -10





#生成节点关系图
def graph( md, n=20, seed=12 ):

    # g = nx.erdos_renyi_graph(n=n, p=md / (2 * (n - 1)), directed=True,
    #                          seed=seed)  # n=10,seed=1234: mean_dergree=4.4, seed=12: mean_dergree=3.8
    g = sf.scale_free( n, md, seed  )

    adj = nx.to_numpy_array( g ).T

    return g, adj




def dynamic( u, w,  adj, gc ):

    Tu = 1 / (1 + np.exp( lam * (u - Osyn)))
    cp = gc * (u-Vs) * (adj.dot(Tu))

    du = beta / ( 1 + u**2 ) + w + cp
    dw = w - v*u - o

    return du,dw




def time_series( n, length, gc, md ,seed ):
    g, adj = graph( md, n, seed )

    np.random.seed(seed)
    u0, w0 = np.random.random_sample( [2,len(g)] )
    u, w = u0, w0


    U, W = [], []  # [t,nods]
    for _ in range( length+5000 ):
        u,w = dynamic( u, w, adj, gc )
        U.append( u )
        W.append( w )


    U = np.expand_dims( np.transpose( U, [1,0] ), axis=-1 ) #[t,nodes]--[nodes,t,1]
    W = np.expand_dims( np.transpose( W, [1,0] ), axis=-1 )  # [t,nodes]--[nodes,t,1]

    ts = np.concatenate( [U,W], axis=-1 ) #[nodes,t,2]
    ts = ts[:,-length:,:]
    print(ts.shape, ts[-1])

    return ts, g#, np.array( dy.data )



#生成训练样本
def sample( n =100, length=1., gc=0.4, md = 20, seed = 0 ):

    print( n, length, gc, md,seed )

    ts, g = time_series(n, length, gc, md, seed=seed )

    # np.save( HOME + '/cause/data/Rulkov/ER/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed), ts )
    np.save(HOME + '/cause/data/Rulkov/SF/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed),
            ts)


if __name__ == '__main__':
    for md in np.linspace( 5, 40 + 1, 10 ):
        for seed in range(5):
            sample( n=100, length=20000, gc=0.002, md = md, seed = seed )