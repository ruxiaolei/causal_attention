import networkx as nx
import numpy as np
import os
from scipy.integrate import odeint
import scale_free_graph as sf

HOME = os.environ['HOME']

a = 0.28
b = 0.5
c = 0.04




def graph( md, n=20, seed=12 ):

    # g = nx.erdos_renyi_graph( n=n, p=md/(2*(n-1)), directed=True, seed=seed ) #n=10,seed=1234: mean_dergree=4.4, seed=12: mean_dergree=3.8
    g = sf.scale_free( n, md, seed  )

    adj = nx.to_numpy_array( g ).T

    return g, adj


class dynamic(  ):

    def __init__(self):

        self. data= []


    def __call__(self, y, t,  adj, gc ):

        p, q = np.split(y ,2) #[n],[n]

        tmp = np.sum((p - p.reshape([-1, 1])) * adj, axis=1)
        # count = np.sum(adj, axis=1)

        dp = p - p ** 3 - q - gc * tmp
        # dp = p - p ** 3 - q - gc / count * tmp
        dq = a + b * p - c * q

        return np.concatenate( [dp, dq ] )




def time_series( n, deltaT, gc, md ,seed ):

    g, adj = graph( md, n, seed )
    dy = dynamic()

    np.random.seed( seed )
    y0 = np.random.random_sample( 2*len(g) )
    t = np.linspace(0, 10500, 10500* int(1/deltaT) + 1 )
    ts = odeint( dy, y0, t, args=(adj, gc) )
    ts = ts[-10000 * int(1/deltaT):] #steady state
    ts = ts.reshape( -1, 2, len(g) ) #[t,2,n]
    ts = np.transpose( ts, [2,0,1] ) #[ nodes, t, 2 ]
    print( ts.shape, ts[-1] )

    return ts, g#, np.array( dy.data )




def sample( n =100, deltaT=1., gc=0.4, md = 20, seed=12 ):

    print( n, deltaT, gc,md, seed )

    ts, g = time_series(n, deltaT, gc, md, seed=seed )

    # np.save( HOME + '/cause/data/FHN/ER/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed), ts )
    np.save(HOME + '/cause/data/FHN/SF/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed), ts)

#
#
for md in np.linspace( 5, 40 + 1, 10 ):
    for seed in range(5):
        sample( n=100, deltaT=0.1, gc=0.2, md = md, seed = seed )