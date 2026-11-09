import numpy as np,pandas as pd
from scipy.optimize import least_squares
from scipy.integrate import solve_ivp
D=pd.read_csv('data/train.csv'); V=pd.read_csv('data/val.csv')
def feats(d):
 y,v,u=d[['y','x1','x2']].to_numpy().T
 return {'one':np.ones(len(y)),'y':y,'v':v,'u':u,'sin':np.sin(y),'y3':y**3,'y5':y**5,'sign':np.sign(v),'tanh':np.tanh(v),'vabs':v*abs(v),'u3':u**3,'sin2':np.sin(2*y),'y2v':y*y*v,'yv2':y*v*v,'uabs':u*abs(u),'cosv':np.cos(y)*v}
F=feats(D);FV=feats(V)
families=[['y','v','u'],['sin','v','u'],['y','v','u','sign'],['sin','v','u','sign'],['sin','v','u','tanh'],['y','y3','v','u','sign'],['y','y3','y5','v','u','sign'],['sin','v','vabs','u','sign'],['sin','v','u','sign','one'],['sin','v','u','sign','u3'],['sin','v','u','sign','y2v'],['sin','v','u','sign','sin2']]
for names in families:
 A=np.stack([F[n] for n in names],1);B=np.stack([FV[n] for n in names],1)
 p=np.linalg.lstsq(A,D.dx1,rcond=None)[0];err=D.dx1-A@p
 print(names,np.round(p,5),'rmse',np.sqrt(np.mean(err**2)),np.sqrt(np.mean((V.dx1-B@p)**2)))
 if names==['sin','v','u','sign']:
  D['res']=err
  for c in ['y','x1','x2']:
   print(D.groupby(pd.cut(D[c],10),observed=True)['res'].agg(['mean','std','count']).to_string())
# check timing convention output kinematics
for d in [D,V]:
 aa=[];bb=[]
 for _,g in d.groupby('trajectory'):
  aa.extend(np.diff(g.y)/.01);bb.extend(np.column_stack([g.x1.to_numpy()[:-1],g.x1.to_numpy()[1:]]))
 p=np.linalg.lstsq(bb,aa,rcond=None)[0];print('kinematic',p,'rmse',np.sqrt(np.mean((np.array(aa)-np.array(bb)@p)**2)))
