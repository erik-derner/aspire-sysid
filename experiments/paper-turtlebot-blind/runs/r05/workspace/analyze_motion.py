import numpy as np,pandas as pd
from scipy.optimize import least_squares
z=np.load('kinematics.npz');X=z['X'];Y=z['Y'];G=z['G'];t=X[:,2];v=X[:,3];u=X[:,4];w=z['dth'];s=Y[:,0]*np.cos(t)+Y[:,1]*np.sin(t);lat=-Y[:,0]*np.sin(t)+Y[:,1]*np.cos(t)
steady=np.ones(len(v),bool)
for i in range(len(v)):
 steady[i]=i>1 and G[i]==G[i-2] and np.all(X[i,3:]==X[i-2,3:])
print('steady',steady.sum())
for mask in [np.ones(len(v),bool),steady]:
 print('\nsubset',mask.sum())
 for target in [s,w,lat]:
  A=np.array([np.ones(len(v)),v,u,abs(u),v*v,u*u,v*u,v*abs(u),np.sign(u),np.sign(u)*v]).T
  c=np.linalg.lstsq(A[mask],target[mask],rcond=None)[0]
  print('coeff',np.round(c,6),'rmse',np.sqrt(np.mean((target[mask]-A[mask]@c)**2)))
# show steady segment means
D=pd.read_csv('data/train.csv')
for g,d in D.groupby('trajectory'):
 a=d.values
 for start in range(0,150,5):
  ids=np.where(G==g)[0][start+2:min(start+5,149)]
  if len(ids):print(g,start,round(v[ids[0]],4),round(u[ids[0]],4),round(s[ids].mean(),5),round(w[ids].mean(),5))
np.savez('motion.npz',s=s,lat=lat,w=w,steady=steady)
