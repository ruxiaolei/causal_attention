import networkx as nx
import numpy as np
# import collections as cls
import matplotlib.pyplot as plt
import itertools as its
import os
from scipy.integrate import odeint
import scale_free_graph as sf

HOME = os.environ['HOME']

gca = 1.01
Vca = 1
gk=2.01
Vk=-0.7
gL=0.51
VL=-0.5

V1 = -0.01
V2 = 0.15
V3 = 0.0
V4= 0.3
C = 0.2
OI=0.2

# T = 1
I0 = 0.085
# Jmax = 1.0
Vs=0.1
b=5
# O = 0

#生成节点关系图
def graph( md, n=20, seed=12 ):
    
    g = nx.erdos_renyi_graph(n=n, p=md / (2 * (n - 1)), directed=True,
                             seed=seed)  # n=10,seed=1234: mean_dergree=4.4, seed=12: mean_dergree=3.8

    adj = nx.to_numpy_array( g ).T

    return g, adj


class dynamic(  ):

    def __init__(self):

        self. data= []


    def __call__(self, y, t,  adj, gc ):

        V,w = np.split(y, 2)  # [n],[n]

        m_ = 0.5* ( 1+ np.tanh( (V-V1)/V2 ) )
        w_ = 0.5* ( 1+ np.tanh( (V-V3)/V4 ) )
        Tw = 1 / ( np.cosh(( V-V3 )/(2*V4) ))
        # N = adj.shape[0]
        # Isyn = gc  * ( Vs - V) * adj.dot(1 / (1 + np.exp(-b * V )))
        I = I0 #+ Isyn


        dV = ( -( gL * ( V - VL ) + gca * m_ * ( V-Vca ) + gk * w *( V-Vk ) ) + I ) / C
        dw = OI * ( w_ - w ) / Tw


        return np.concatenate([dV, dw])



def time_series( n, deltaT, gc, md ,seed ):
    g, adj = graph( md, n, seed )
    dy = dynamic()

    np.random.seed( seed )
    y0 = np.random.random_sample( 2*len(g) ) #[3n]
    t = np.linspace(0, 10500, 10500* int(1/deltaT) + 1 )
    ts = odeint( dy, y0, t, args=(adj, gc) )
    ts = ts[-10000 * int(1/deltaT):] #steady state
    ts = ts.reshape( -1, 2, len(g) ) #[t,3,n]
    ts = np.transpose(ts, [2, 0, 1])  # [ nodes, t, 3/4 ]
    print( ts.shape, ts[-1] )

    return ts, g



#生成训练样本
def sample( n =100, deltaT=1., gc=0.4, md = 20, seed=12 ):

    print( n, deltaT, gc, md, seed )

    ts, g = time_series(n, deltaT, gc, md, seed=seed )

    np.save( HOME + '/cause/data/ML/ER/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md,seed), ts )

#



if __name__ == '__main__':
    for md in np.linspace( 5, 40 + 1, 10 ):
        for seed in range(5):
            sample( n=100, deltaT=0.1, gc=0.1, md = md, seed = seed )

