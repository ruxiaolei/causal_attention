import networkx as nx
import numpy as np
import os
import scale_free_graph as sf

HOME = os.environ['HOME']

a = 0.2
b = 2
c = -56
d = -16
I0 = -99
Vpeak = 30

#生成节点关系图
def graph( md, n=20, seed=12 ):
    # g = nx.erdos_renyi_graph( n=n, p=md/(2*(n-1)), directed=True, seed=seed ) #n=10,seed=1234: mean_dergree=4.4, seed=12: mean_dergree=3.8
    g = sf.scale_free(n, md, seed)

    adj = nx.to_numpy_array( g ).T

    return g, adj



def dynamic( v, u,  adj, deltaT, gc ):


    v_fired = v.copy()
    v_fired[v_fired < Vpeak] = 0
    v_fired[v_fired >= Vpeak] = 1
    D = gc * np.matmul(adj, v_fired)


    u[v >= Vpeak] += d
    v[v >= Vpeak] = c

    v = v + 0.5 * deltaT * (  0.04 * v **2 + 5*v + 140 -u +I0  ) + D
    v = v + 0.5 * deltaT * ( 0.04 * v ** 2 + 5 * v + 140 - u + I0 ) + D
    u = u + deltaT * a * ( b*v - u )
    # print(v,u)

    return v, u




#生成时间序列
def time_series( n, deltaT,  md ,gc, seed ):
    # 动力学系统
    g, adj = graph( md, n, seed )

    np.random.seed( seed )
    v = c + ( Vpeak- c ) * np.random.random_sample( len(g) )
    u = b * v
    ts = []
    t = np.linspace(0, 5500, 5500* int(1/deltaT) + 1 )
    for _ in t:
        ts.append( [v.copy(),u.copy()] )
        v, u = dynamic( v, u,  adj, deltaT, gc )

    ts = np.array(ts) #[t,2,len(g)]
    ts = ts[-5000 * int(1/deltaT):] #steady state
    ts = np.transpose( ts, [2,0,1] ) #[ nodes, t, 2 ]
    print( ts.shape, ts[-5:,-5:,0] )

    return ts, g#, np.array( dy.data )



#生成训练样本
def sample( n =100, deltaT=1.,  md = 20,gc =1., seed=12 ):

    print( n, deltaT, gc, md, seed )
    ts, g = time_series(n, deltaT, md, gc, seed=seed )

    # np.save( HOME + '/cause/data/Izh/ER/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed), ts )
    np.save( HOME + '/cause/data/Izh/SF/nodes={0}_timeseries_coupling={1}_md={2}_seed{3}.npy'.format(n, gc, md, seed),
            ts )



if __name__ == '__main__':
    for md in np.linspace( 5, 40 + 1, 10 ):
        for seed in range(5):
            sample( n=100, deltaT=0.1, gc=0.5, md = md, seed = seed )