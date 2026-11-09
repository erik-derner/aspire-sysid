import pandas as pd,numpy as np
from scipy.optimize import least_squares
tr=pd.read_csv('data/train.csv');v=pd.read_csv('data/val.csv')
t,w,u,y=[tr[c].to_numpy() for c in ['theta','omega','u','domega']]
m=abs(w)>1
X=np.array([u,-np.sin(t),-w,-np.sign(w)]).T
p=np.linalg.lstsq(X[m],y[m],rcond=None)[0]; print('OLS moving [motor gravity visc coulomb]',p)
r=y-X@p
for name,values,bins in [('omega',w,[-23,-10,-5,-2,-1,-.1,.1,1,2,5,10,23]),('theta',t,[-3.2,-2,-1,-.5,0,.5,1,2,3.2]),('u',u,[-5,-3,-1,-.1,.1,1,3,5])]:
 print(name)
 for lo,hi in zip(bins[:-1],bins[1:]):
  mm=m&(values>=lo)&(values<hi);print(lo,hi,mm.sum(),np.mean(r[mm]) if mm.sum() else '')
for k,g in tr.groupby('trajectory'):
 print('traj',k,'start',g.iloc[0].to_dict(),'end',g.iloc[-1].to_dict(),'rest angles',np.unique(g.loc[g.omega==0,'theta'].round(5))[-15:])
print('kinematic error',np.sqrt(np.mean(np.concatenate([np.diff(g.theta)-.005*(g.omega.to_numpy()[1:]+g.omega.to_numpy()[:-1]) for _,g in tr.groupby('trajectory')])**2)))
