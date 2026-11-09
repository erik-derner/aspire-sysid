import numpy as np,pandas as pd
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
def pack(d):
 gs=[g for _,g in d.groupby('trajectory')];return np.concatenate([g[['y','x1','x2']].values for g in gs]),np.array([len(g) for g in gs])
T,nt=pack(tr);V,nv=pack(va)
mT=np.ones(len(T),bool);mT[np.r_[0,np.cumsum(nt)[:-1]]]=False
mV=np.ones(len(V),bool);mV[np.r_[0,np.cumsum(nv)[:-1]]]=False
