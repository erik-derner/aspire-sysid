import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
D=pd.read_csv('helper_pairs.csv');print(D.columns.tolist());print(D.head().to_string())
A=np.load('pairs.npz');X=A['X'];Y=A['Y'];G=A['G'];dt=np.arctan2(np.sin(Y[:,2]-X[:,2]),np.cos(Y[:,2]-X[:,2]));s=(Y[:,0]-X[:,0])*np.cos(X[:,2]+dt/2)+(Y[:,1]-X[:,1])*np.sin(X[:,2]+dt/2)
phase=np.concatenate([np.arange(149)%5 for _ in range(3)]);sel=phase>=2
cols=['1','u','w','u*w','u^2','w^2','w^3','dead','cos(theta)','sin(theta)','cos(2theta)','sin(2theta)','y','x1','theta','u cos(theta)','u sin(theta)'];u=X[:,3];w=X[:,4];t=X[:,2];F=np.array([u*0+1,u,w,u*w,u**2,w**2,w**3,np.sign(w)*np.maximum(abs(w)-.09,0),np.cos(t),np.sin(t),np.cos(2*t),np.sin(2*t),X[:,0],X[:,1],t,u*np.cos(t),u*np.sin(t)]).T
for target,n in [(s,'speed'),(dt,'angle')]:
 base=[0,1] if n=='speed' else [0,7]
 c=np.linalg.lstsq(F[sel][:,base],target[sel],rcond=None)[0];r=target-F[:,base]@c;print(n,'base',c,'interior sd',np.std(r[sel]))
 for i in range(F.shape[1]):
  print(cols[i],round(np.corrcoef(F[sel,i],r[sel])[0,1],3),end='; ')
 print()
 for g in [1,2,3]:print('traj',g,'mean residual',np.mean(r[sel&(G==g)]),'sd',np.std(r[sel&(G==g)]))
 for extra in [[2],[4],[5],[1] if n=='angle' else [7],[8,9],[10,11],[12,13],[3],[8,9,10,11],[1,3,5]]:
  ids=list(dict.fromkeys(base+extra));c=np.linalg.lstsq(F[sel][:,ids],target[sel],rcond=None)[0];err=np.sqrt(np.mean((F[sel][:,ids]@c-target[sel])**2));loo=[]
  for g in [1,2,3]:
   fit=sel&(G!=g);val=sel&(G==g);q=np.linalg.lstsq(F[fit][:,ids],target[fit],rcond=None)[0];loo.append(np.sqrt(np.mean((F[val][:,ids]@q-target[val])**2)))
  print('extra',[cols[i] for i in extra],c,'RMSE',err,'LOO',loo)
