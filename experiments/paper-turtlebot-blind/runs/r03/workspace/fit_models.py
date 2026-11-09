import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); G=[g[['y','x1','x2','x3','x4']].values for _,g in D.groupby('trajectory')]
K=np.load('kinematic.npz'); X=K['X']; Q=K['Q']; ids=K['ids']; phase=K['phase']
# All coefficients refer to displacement per sample, not derivative.
SPECS={
 'linear':([.16,0,.13,0],([-1,-.05,-.5,-.1],[1,.05,.5,.1])),
 'deadzone':([.16,0,.15,0,.08],([-1,-.05,-.5,-.1,0],[1,.05,.5,.1,.35])),
 'cubic':([.16,0,.14,0,.01,0],([-1,-.05,-.5,-.1,-.5,-.5],[1,.05,.5,.1,.5,.5])),
 'coupled':([.16,0,0,.14,0,.01,0],([-1,-.05,-1,-.5,-.1,-.5,-1],[1,.05,1,.5,.1,.5,1]))}
def inputs(p,u,w,f):
 v=p[0]*u+p[1]
 if f=='linear': h=p[2]*w+p[3]
 elif f=='deadzone': h=p[2]*np.sign(w)*np.maximum(abs(w)-p[4],0)+p[3]
 elif f=='cubic': h=p[2]*w+p[3]+p[4]*w**3+p[5]*u*w
 elif f=='coupled':
  v+=p[2]*u*abs(w); h=p[3]*w+p[4]+p[5]*w**3+p[6]*u*w
 return v,h
def sim(p,g,f):
 v,h=inputs(p,g[:-1,3],g[:-1,4],f); theta=g[0,2]+np.r_[0,np.cumsum(h)]; m=theta[:-1]+.5*h
 return np.c_[g[0,0]+np.r_[0,np.cumsum(v*np.cos(m))],g[0,1]+np.r_[0,np.cumsum(v*np.sin(m))],theta]
def residual(p,groups,f,weight):
 rr=[]
 for g in groups:
  pred=sim(p,g,f)[1:]; e=pred-g[1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); rr.append((e*np.array(weight)).ravel())
 return np.concatenate(rr)
def fit(f,groups,mask,mode='balanced'):
 init,bounds=SPECS[f];
 def one(p):
  v,h=inputs(p,X[mask,3],X[mask,4],f)
  return np.r_[(v-.2*Q[mask,0]),.3*(h-Q[mask,1])]
 first=least_squares(one,init,bounds=bounds,max_nfev=300,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 weights={'balanced':[1,1,.3],'y':[1,.15,.1],'heading':[.3,.3,1]}
 end=least_squares(residual,first.x,args=(groups,f,weights[mode]),bounds=bounds,max_nfev=400,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return first.x,end.x
results={}
for f in SPECS:
 results[f]={}
 for mode in ['balanced','y','heading']:
  allfirst,p=fit(f,G,np.ones(len(X),bool),mode); rms=[]; train=[]
  for g in G:
   e=sim(p,g,f)[1:]-g[1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); train.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  for j in range(3):
   _,pc=fit(f,[g for i,g in enumerate(G) if i!=j],ids!=j+1,mode); e=sim(pc,G[j],f)[1:]-G[j][1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); rms.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  print(f,mode,'p',p,'train',np.array(train).round(4),'CV',np.array(rms).round(4),flush=True)
  results[f][mode]={'initial':allfirst.tolist(),'params':p.tolist(),'train':train,'cv':rms}
json.dump(results,open('fit_results.json','w'),indent=2)
