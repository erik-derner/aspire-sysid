import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');B=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in D.groupby('trajectory')]
START={'clipdead':[0,.18,.20,0,.025,.08], 'propdead':[.17,.20,0,.025,.08], 'harddead':[0,.18,.20,0,.1], 'softdeadbil':[0,.18,.20,0,.025,.08,0], 'smoothcoulomb':[0,.18,.20,0,.025]}
def law(p,u,f):
 v,w=u[:,0],u[:,1]
 if f=='propdead': return p[0]*v,p[1]*w+p[2]-p[3]*np.tanh(w/p[4])
 speed=np.maximum(0,p[0]+p[1]*v);z=p[2]*w+p[3]
 if f=='harddead':z=p[2]*np.sign(w)*np.maximum(0,np.abs(w)-p[4])+p[3]
 elif f=='smoothcoulomb':z-=p[4]*w/np.sqrt(w*w+.05**2)
 else:z-=p[4]*np.tanh(w/p[5])
 if f=='softdeadbil':z+=p[6]*v*w
 return speed,z
def sim(p,b,f):
 v,z=law(p,b[:-1,3:],f);th=b[0,2]+np.r_[0,np.cumsum(z)];mid=th[:-1]+z/2;xy=b[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[v*np.cos(mid),v*np.sin(mid)],axis=0)]);return np.c_[xy,th]
def residual(p,blocks,f,weight=1):
 return np.concatenate([((sim(p,b,f)[1:]-np.c_[b[1:,:2],np.unwrap(b[:,2])[1:]])*np.array([1,1,weight])).ravel() for b in blocks])
def fit(blocks,f,weight=1):
 p0=START[f];lo=np.full(len(p0),-np.inf);hi=-lo
 if f=='propdead':lo[3:]=[0,.02];hi[3:]=[.2,2]
 elif f=='harddead':lo[4]=0;hi[4]=.5
 elif f=='smoothcoulomb':lo[4]=0;hi[4]=.2
 else:lo[4:6]=[0,.02];hi[4:6]=[.2,2]
 return least_squares(residual,p0,args=(blocks,f,weight),bounds=(lo,hi),max_nfev=1500,ftol=1e-10,xtol=1e-10,gtol=1e-10).x
def rmse(s,b):return np.sqrt(np.mean((s[1:,0]-b[1:,0])**2))
R={}
for f in START:
 for weight in [0.3,1,3]:
  p=fit(B,f,weight);cv=[rmse(sim(fit([b for j,b in enumerate(B) if i!=j],f,weight),B[i],f),B[i]) for i in range(3)];train=[rmse(sim(p,b,f),b) for b in B]
  # prefix fit, forecast remaining 60 samples from measured start
  q=fit([b[:90] for b in B],f,weight);forecast=[rmse(sim(q,b[89:],f),b[89:]) for b in B]
  print(f,weight,'p',p,'train',np.round(train,5),'cv',np.round(cv,5),'CV',np.sqrt(np.mean(np.array(cv)**2)),'future',np.round(forecast,5))
  R[f+str(weight)]={'p':p.tolist(),'train':train,'cv':cv,'forecast':forecast}
json.dump(R,open('refinement_results.json','w'),indent=2)
