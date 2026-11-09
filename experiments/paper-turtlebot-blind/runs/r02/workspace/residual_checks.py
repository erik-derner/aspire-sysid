import pandas as pd,numpy as np,json
D=pd.read_csv('data/train.csv');B=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in D.groupby('trajectory')]
R=json.load(open('refinement_results.json'));Q=json.load(open('experiment_results.json'))
for f,p in [('harddead',R['harddead0.3']['p']),('propdead',R['propdead0.3']['p']),('linear',Q['linear']['p'])]:
 E=[];X=[];S=[]
 for b in B:
  u,w=b[:-1,3],b[:-1,4]
  if f=='harddead':v=np.maximum(0,p[0]+p[1]*u);z=p[2]*np.sign(w)*np.maximum(0,np.abs(w)-p[4])+p[3]
  elif f=='propdead':v=p[0]*u;z=p[1]*w+p[2]-p[3]*np.tanh(w/p[4])
  else:v=p[0]+p[1]*u;z=p[2]*w+p[3]
  mid=b[:-1,2]+z/2;diff=np.diff(b[:,:3],axis=0);diff[:,2]=np.arctan2(np.sin(diff[:,2]),np.cos(diff[:,2]));e=diff-np.c_[v*np.cos(mid),v*np.sin(mid),z];E.append(e);X.append(b[:-1]);S.append(np.r_[True,np.any(np.diff(b[:-1,3:],axis=0)!=0,axis=1)])
 E=np.vstack(E);X=np.vstack(X);S=np.hstack(S)
 print(f,'rms',np.sqrt(np.mean(E*E,axis=0)),'mean',E.mean(axis=0))
 print('switch RMS',np.sqrt(np.mean(E[S]**2,axis=0)),'nonswitch RMS',np.sqrt(np.mean(E[~S]**2,axis=0)))
 print('input correlation',np.corrcoef(np.c_[E,X[:,3:]].T)[:3,3:])
 print('lag1 per state',[np.mean([np.corrcoef(e[:-1,j],e[1:,j])[0,1] for e in [E[:149],E[149:298],E[298:]]]) for j in range(3)])
 # observed midpoint cross-track vs parallel motion
mid=np.concatenate([(np.unwrap(b[:,2])[:-1]+np.unwrap(b[:,2])[1:])/2 for b in B]);xy=np.vstack([np.diff(b[:,:2],axis=0) for b in B]);lat=-xy[:,0]*np.sin(mid)+xy[:,1]*np.cos(mid)
print('measured midpoint cross-track RMS',np.sqrt(np.mean(lat**2)))
