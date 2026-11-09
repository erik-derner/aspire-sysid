import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');G=[g[['y','x1','x2','x3','x4']].values for _,g in D.groupby('trajectory')];U=[np.unwrap(g[:,2]) for g in G]
S=[]
for i,g in enumerate(G):
 u,w=g[:-1,3:5].T;up,wp=np.vstack([g[0,3:5],g[:-2,3:5]]).T;dp=np.diff(g[:,:2],axis=0);loc=(dp[:,0]+1j*dp[:,1])*np.exp(-1j*g[:-1,2]);h=np.diff(U[i]);S.append(dict(u=u,w=w,up=up,wp=wp,v=loc.real,h=h,side=loc.imag))
NAMES=['linear','quadratic','cubic','friction','interaction','friction_interaction','wheelpoly']
def features(u,w,name):
 if name=='linear':return np.c_[np.ones(len(u)),w]
 if name=='quadratic':return np.c_[np.ones(len(u)),w,w*abs(w)]
 if name=='cubic':return np.c_[np.ones(len(u)),w,w**3]
 if name=='friction':return np.c_[np.ones(len(u)),w,np.tanh(w/.08)]
 if name=='interaction':return np.c_[np.ones(len(u)),w,w*u]
 if name=='friction_interaction':return np.c_[np.ones(len(u)),w,np.tanh(w/.08),w*u]
 if name=='wheelpoly':return np.c_[np.ones(len(u)),w,abs(u-.1*w)-abs(u+.1*w)]
def fit(name,ids,method):
 A=[];Y=[];V=[];Q=[]
 for i in ids:
  s=S[i];fc=features(s['u'],s['w'],name);fp=features(s['up'],s['wp'],name)
  if method=='lag':a=np.c_[fc,fp[:,1:]];sel=np.arange(149)>0
  if method=='steady':a=fc;sel=np.arange(149)%5>=2
  if method=='block':a=fc;sel=np.ones(149,dtype=bool);a=np.array([a[k:k+5].sum(axis=0) for k in range(0,145,5)]); yy=np.array([s['h'][k:k+5].sum() for k in range(0,145,5)])
  else: yy=s['h'][sel];a=a[sel]
  A.append(a);Y.append(yy)
  vf=np.c_[np.ones(149),s['u'],s['up']];vs=np.arange(149)>0
  V.append(vf[vs]);Q.append(s['v'][vs])
 co=np.linalg.lstsq(np.vstack(A),np.concatenate(Y),rcond=None)[0]
 if method=='lag': n=(len(co)+1)//2;co=np.r_[co[0],co[1:n]+co[n:]]
 vc=np.linalg.lstsq(np.vstack(V),np.concatenate(Q),rcond=None)[0];vc=np.r_[vc[0],vc[1]+vc[2]]
 return co,vc
def sim(name,co,vc,i,mid):
 g=G[i];u,w=g[:-1,3:5].T;h=features(u,w,name)@co;v=vc[0]+vc[1]*u;theta=g[0,2]+np.r_[0,np.cumsum(h)];pos=g[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[v*np.cos(theta[:-1]+mid*h),v*np.sin(theta[:-1]+mid*h)],axis=0)]);return np.c_[pos,theta]
R={}
for name in NAMES:
 for method in ['lag','steady','block']:
  co,vc=fit(name,[0,1,2],method);tr=[];cv=[]
  for i in range(3):
   ss=sim(name,co,vc,i,-.25);r=ss-G[i][:,:3];r[:,2]=ss[:,2]-U[i];tr.append(np.sqrt(np.mean(r[1:]**2,axis=0)).tolist())
   cc,vv=fit(name,[j for j in range(3) if j!=i],method);ss=sim(name,cc,vv,i,-.25);r=ss-G[i][:,:3];r[:,2]=ss[:,2]-U[i];cv.append(np.sqrt(np.mean(r[1:]**2,axis=0)).tolist())
  key=name+'_'+method;R[key]={'co':co.tolist(),'vc':vc.tolist(),'train':tr,'cv':cv};print(key,'h',np.round(co,5),'v',np.round(vc,5),'trainY',np.round(np.array(tr)[:,0],4),'cvY',np.round(np.array(cv)[:,0],4),'cvTheta',np.round(np.array(cv)[:,2],4),flush=True)
json.dump(R,open('reduced_results.json','w'),indent=2)
