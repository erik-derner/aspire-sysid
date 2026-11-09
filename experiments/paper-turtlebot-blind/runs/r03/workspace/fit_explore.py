import pandas as pd,numpy as np
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); X=[]; Q=[]; ids=[]; phases=[]
for t,g in D.groupby('trajectory'):
 a=g[['y','x1','x2','x3','x4']].values; b=a[1:,:3]-a[:-1,:3]; b[:,2]=np.arctan2(np.sin(b[:,2]),np.cos(b[:,2])); theta=a[:-1,2]+b[:,2]/2
 speed=(b[:,0]*np.cos(theta)+b[:,1]*np.sin(theta))/.2
 X.append(a[:-1]); Q.append(np.c_[speed,b[:,2]]); ids.extend([t]*len(b)); phases.extend(np.arange(len(b))%5)
X=np.vstack(X); Q=np.vstack(Q); ids=np.array(ids); phases=np.array(phases)
np.savez('kinematic.npz',X=X,Q=Q,ids=ids,phase=phases)
u=X[:,3]; w=X[:,4]
for mask,name in [(np.ones(len(u),bool),'all'),(phases>=2,'settled')]:
 print('\n',name)
 terms=[np.ones(len(u)),u,w,abs(w),u*abs(w),u**2,w**2,u*w,w**3,np.sign(w),np.sign(w)*u]
 names=['1','u','w','absw','uabsw','u2','w2','uw','w3','signw','signwu']
 for j in range(2):
  for sel in ([0,1,3,4],[0,2,9],[0,1,2,3,4,5,6,7,8,9,10]):
   F=np.array(terms).T[:,sel]; c=np.linalg.lstsq(F[mask],Q[mask,j],rcond=None)[0]; print(j,[names[k] for k in sel],c,'rmse',np.sqrt(np.mean((F[mask]@c-Q[mask,j])**2)))
 print('speedratio w corr',np.corrcoef((Q[:,0]/u)[mask],abs(w)[mask])[0,1])
print('steady block means u,w,speed,turn')
for t in np.unique(ids):
 for k in range(0,149,5):
  mask=(ids==t)&(np.arange(len(u))%149>=k+2)&(np.arange(len(u))%149<k+5)
  print(t,k, np.round(np.r_[X[mask,3:5].mean(axis=0),Q[mask].mean(axis=0)],6))
