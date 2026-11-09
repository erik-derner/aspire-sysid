import numpy as np,pandas as pd
D=pd.read_csv('data/train.csv');A=np.load('pairs.npz');X=A['X'];Y=A['Y']; dx=Y-X[:,:3];dx[:,2]=np.arctan2(np.sin(dx[:,2]),np.cos(dx[:,2]));r=np.hypot(dx[:,0],dx[:,1]);heading=np.arctan2(dx[:,1],dx[:,0]);dhead=np.arctan2(np.sin(heading-X[:,2]),np.cos(heading-X[:,2]));
print('r/input quantile',np.quantile(r/(X[:,3]+1e-8),[0,.1,.5,.9,1]));print('heading offset quantile',np.quantile(dhead,[0,.1,.5,.9,1]));
for g in [1,2,3]:
 d=D[D.trajectory==g].reset_index(drop=True);a=d[['y','x1','x2','x3','x4']].to_numpy();print('\ntraj',g)
 for i in range(20):
  dx=a[i+1,:3]-a[i,:3];dh=np.arctan2(np.sin(dx[2]),np.cos(dx[2]));print(i,'inputs',a[i,3:], 'dpos',dx[:2], 'length',np.linalg.norm(dx[:2]),'dtheta',dh,'direction_offset',np.arctan2(dx[1],dx[0])-a[i,2])
# trigonometric fit and heading candidates
features=[np.ones(len(X)),X[:,3]*np.cos(X[:,2]),X[:,3]*np.sin(X[:,2]),np.cos(X[:,2]),np.sin(X[:,2]),X[:,4]*np.cos(X[:,2]),X[:,4]*np.sin(X[:,2])]
F=np.array(features).T;c=np.linalg.lstsq(F,Y[:,:2]-X[:,:2],rcond=None)[0];print('trig fit',c,'err',np.sqrt(np.mean((F@c-(Y[:,:2]-X[:,:2]))**2,axis=0)))
u=X[:,3];v=X[:,4];F=np.array([np.ones(len(X)),u,v,u*v,u*np.tan(v),np.tan(v)]).T;c=np.linalg.lstsq(F,np.arctan2(np.sin(Y[:,2]-X[:,2]),np.cos(Y[:,2]-X[:,2])),rcond=None)[0];print('heading fit',c,'rmse',np.sqrt(np.mean((F@c-np.arctan2(np.sin(Y[:,2]-X[:,2]),np.cos(Y[:,2]-X[:,2])))**2)))
