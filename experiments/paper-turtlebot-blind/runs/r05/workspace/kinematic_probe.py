import numpy as np,pandas as pd
z=np.load('transitions.npz');X=z['X'];Y=z['Y'];G=z['G'];th=X[:,2];v=X[:,3];u=X[:,4];dth=np.arctan2(np.sin(Y[:,2]),np.cos(Y[:,2]));
print('first trajectory rows'); print(pd.read_csv('data/train.csv').head(25).to_string(index=False))
for name,A,target in [('position',np.column_stack([v*np.cos(th),v*np.sin(th),v*u*np.cos(th),v*u*np.sin(th),v**2*np.cos(th),v**2*np.sin(th),np.ones(len(v))]),Y[:,:2]),('angle',np.column_stack([np.ones(len(v)),v,u,v*u,v*np.tan(u),np.sin(u),th,X[:,0],X[:,1]]),dth)]:
 c=np.linalg.lstsq(A,target,rcond=None)[0];print(name,'coef',c,'rmse',np.sqrt(np.mean((target-A@c)**2,axis=0)))
print('dth quantiles',np.quantile(dth,[0,.01,.1,.5,.9,.99,1]))
# angular residual and kinematic displacement ratios
for i in range(20): print(i,'norm',np.linalg.norm(Y[i,:2])/v[i], 'dir delta',np.arctan2(Y[i,1],Y[i,0])-th[i],'dth',dth[i], 'u',u[i])
for feat in [u,v*u,v*np.tan(u)]:
 c=np.dot(feat,dth)/np.dot(feat,feat);e=dth-c*feat;print('angle simple',c,'rmse',np.sqrt(np.mean(e**2)), 'largest',np.argsort(abs(e))[-15:])
np.savez('kinematics.npz',X=X,Y=Y,G=G,dth=dth)
