import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');B=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in D.groupby('trajectory')]
for j,b in enumerate(B):
 th=np.unwrap(b[:,2]); u=b[:-1,3:]; dt=np.diff(th); feat=np.c_[np.ones(len(u)),u[:,1],u[:,0]*u[:,1],u[:,1]**3]; cs=np.vstack([np.zeros(4),np.cumsum(feat,axis=0)]); p=np.linalg.lstsq(cs,th-th[0],rcond=None)[0];print(j,'yaw integrated fit',p,'err',np.sqrt(np.mean((cs@p-th+th[0])**2)));print('linear yaw',np.linalg.lstsq(cs[:,:2],th-th[0],rcond=None)[0]);
 ds=np.diff(b[:,:2],axis=0); mid=(th[1:]+th[:-1])/2; fwd=ds[:,0]*np.cos(mid)+ds[:,1]*np.sin(mid); lat=-ds[:,0]*np.sin(mid)+ds[:,1]*np.cos(mid);print('forward mean',fwd.mean(),'lat rms',np.std(lat),'lat max',np.max(np.abs(lat)));print('speed coeff',np.linalg.lstsq(np.c_[np.ones(len(u)),u[:,0]],fwd,rcond=None)[0]);print('speed chunks',[(round(np.mean(fwd[i:i+25]-u[i:i+25,0]/6),5), round(np.mean(dt[i:i+25]-.14*u[i:i+25,1]),5)) for i in range(0,len(u),25)])
# yaw regression cumulative global
for features in [lambda u:np.c_[u[:,1]],lambda u:np.c_[np.ones(len(u)),u[:,1]],lambda u:np.c_[np.ones(len(u)),u[:,1],u[:,0]*u[:,1]],lambda u:np.c_[np.ones(len(u)),u[:,1],u[:,0]*u[:,1],u[:,1]**3]]:
 X=[];Y=[]
 for b in B:
  X.append(np.cumsum(features(b[:-1,3:]),axis=0));Y.append(np.unwrap(b[1:,2])-b[0,2])
 X=np.vstack(X);Y=np.hstack(Y);p=np.linalg.lstsq(X,Y,rcond=None)[0];print('global cumulative yaw',p,'rms',np.sqrt(np.mean((X@p-Y)**2)))
