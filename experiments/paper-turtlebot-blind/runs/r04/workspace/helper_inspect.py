import numpy as np,pandas as pd
D=pd.read_csv('data/train.csv'); print(D.head(12).to_string(index=False));print(D.describe().to_string())
A=[];B=[]
for _,g in D.groupby('trajectory'):
 a=g[['y','x1','x2','x3','x4']].values; A.append(a[:-1]);B.append(a[1:,:3]);print('traj',_, 'start',a[0], 'end',a[-1])
A=np.vstack(A);B=np.vstack(B);delta=B-A[:,:3];wrap=(delta[:,2]+np.pi)%(2*np.pi)-np.pi; print('raw deltas',np.quantile(delta,[0,.01,.5,.99,1],axis=0));print('wrap deltas',np.quantile(wrap,[0,.01,.5,.99,1]));print('wrap jumps',np.where(abs(delta[:,2])>3)[0]);
y,v,t,u,w=A.T
F=np.array([np.ones(len(A)),y,v,t,u,w,np.sin(t),np.cos(t),u*np.sin(t),u*np.cos(t),w*np.sin(t),w*np.cos(t),v*np.sin(t),v*np.cos(t),u*np.tan(w),u*w,u/(1+abs(w))]).T
names=['1','y','x1','x2','x3','x4','sin(x2)','cos(x2)','x3*sin(x2)','x3*cos(x2)','x4*sin(x2)','x4*cos(x2)','x1*sin(x2)','x1*cos(x2)','x3*tan(x4)','x3*x4','x3/(1+abs(x4))']
for k,d in enumerate([delta[:,0],delta[:,1],wrap]):
 print('\nDELTA',k)
 for j in range(len(names)):
  c=np.linalg.lstsq(F[:,[0,j]],d,rcond=None)[0];r=d-F[:,[0,j]]@c;print(names[j],c,np.sqrt(np.mean(r*r)))
 c=np.linalg.lstsq(F,d,rcond=None)[0];print('full',list(zip(names,c)),'rmse',np.sqrt(np.mean((d-F@c)**2)))
np.savez('helper_arrays.npz',A=A,B=B,delta=delta,wrap=wrap)
