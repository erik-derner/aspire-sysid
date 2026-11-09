import pandas as pd,numpy as np
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');y=D.y.to_numpy();v=D.x1.to_numpy();u=D.x2.to_numpy();z=D.dx1.to_numpy();m=abs(v)>.6
fs=[np.ones(len(y)),u,v,np.sin(y),np.sign(v),np.cos(y)-1,np.sin(2*y),np.cos(y)*np.sign(v),v*abs(v),u*abs(u),v*np.sin(y),v*np.cos(y),np.sin(y)*np.sign(v)]
names=['1','u','v','sin(y)','sign(v)','cos(y)-1','sin(2*y)','cos(y)*sign(v)','v*abs(v)','u*abs(u)','v*sin(y)','v*cos(y)','sin(y)*sign(v)']
X=np.array(fs).T
for inds in [[0,1,2,3,4],[0,1,2,3,4,5],[0,1,2,3,4,6],[0,1,2,3,4,7],[0,1,2,3,4,5,6,7,8,9,10,11,12]]:
 b=np.linalg.lstsq(X[m][:,inds],z[m],rcond=None)[0];r=z-X[:,inds]@b;print(dict(zip(np.array(names)[inds],b)),np.sqrt(np.mean(r[m]**2)))
 for k,g in D.groupby('trajectory'):
  ids=g.index[(abs(g.x1)>.6)];print(k,len(ids),'bias',np.mean(r[ids]),'rmse',np.sqrt(np.mean(r[ids]**2)))
