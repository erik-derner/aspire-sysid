import pandas as pd, numpy as np
from scipy.signal import savgol_filter
for file in ['train','val']:
 d=pd.read_csv('data/'+file+'.csv');print(file,d.head(),d.describe().to_string())
 for tid,g in d.groupby('trajectory',sort=False):
  a=g[['y','x1','x2','dx1']].to_numpy();dy=np.gradient(a[:,0],.01);dx=np.gradient(a[:,1],.01)
  print(tid,len(g),'ranges',np.round(np.min(a,axis=0),4),np.round(np.max(a,axis=0),4),'dy-x1',np.sqrt(np.mean((dy-a[:,1])**2)),'dx1 diff',np.sqrt(np.mean((dx-a[:,3])**2)))
np.set_printoptions(precision=8,suppress=True)
d=pd.read_csv('data/train.csv');Y=[];X=[];DX=[]
for _,g in d.groupby('trajectory',sort=False):
 a=g[['y','x1','x2','dx1']].to_numpy();Y.extend(savgol_filter(a[:,0],11,4,deriv=1,delta=.01)[5:-5]);X.extend(a[5:-5,:3]);DX.extend(a[5:-5,3])
X=np.array(X);Y=np.array(Y);DX=np.array(DX)
for target,n in [(Y,'dy'),(DX,'dx1')]:
 A=np.c_[np.ones(len(X)),X];c=np.linalg.lstsq(A,target,rcond=None)[0];r=target-A@c;print(n,'affine',c,'rmse',np.std(r),'targetstd',np.std(target))
np.savez('initial_data.npz',X=X,Y=Y,DX=DX)
