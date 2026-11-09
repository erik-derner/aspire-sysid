import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
train=pd.read_csv('data/train.csv');val=pd.read_csv('data/val.csv')
def pack(d):
 gs=list(d.groupby('trajectory',sort=False));n=max(len(g) for _,g in gs);m=len(gs)
 Y=np.zeros((n,m));V=Y.copy();U=Y.copy();mask=np.zeros((n,m),bool)
 for j,(k,g) in enumerate(gs):
  l=len(g);Y[:l,j]=g.y;V[:l,j]=g.x1;U[:l,j]=g.x2;mask[1:l,j]=True
 return Y,V,U,mask,[int(k) for k,g in gs]
TR=pack(train);VA=pack(val)
def force(y,v,u,p,form):
 b,k,c,f,g,s=p[:6]
 restoring=k*np.sin(y) if form not in ['duffing','quintic','linear'] else k*y
 F=b+restoring+c*v+g*u
 if form=='duffing':F+=p[6]*y**3
 if form=='quintic':F+=p[6]*y**3+p[7]*y**5
 if form=='linear':return F
 friction=f*np.tanh(v/s)
 if form=='harmonic':F+=p[6]*(np.cos(y)-1)+p[7]*np.sin(2*y)
 if form=='drag':F+=p[6]*v*np.abs(v)
 if form=='asym':friction+=p[6]*np.tanh(v/s)**2;F+=p[7]*v*np.tanh(v/s)
 if form=='stribeck':friction+=p[6]*np.exp(-(v/p[7])**2)*np.tanh(v/s)
 if form=='positiondamp':F+=p[6]*y*y*v
 if form=='stiction':
  # activation by speed; static branch removes forces below breakaway magnitude.
  w=np.exp(-(v/p[6])**2)
  drive=b+restoring+g*u
  stat=np.sign(drive)*np.maximum(np.abs(drive)-p[7],0)+c*v
  return (1-w)*(F-friction)+w*stat
 return F-friction

def rollout(p,form,D,full=False):
 Y,V,U,mask,ids=D;y=Y[0].copy();v=V[0].copy();py=np.zeros_like(Y);pv=np.zeros_like(Y);py[0]=y;pv[0]=v
 with np.errstate(over='ignore',invalid='ignore'):
  for i in range(len(Y)-1):
   u=U[i];a1=force(y,v,u,p,form);y2=y+.005*v;v2=v+.005*a1;a2=force(y2,v2,u,p,form);y3=y+.005*v2;v3=v+.005*a2;a3=force(y3,v3,u,p,form);y4=y+.01*v3;v4=v+.01*a3;a4=force(y4,v4,u,p,form)
   y+=.01*(v+2*v2+2*v3+v4)/6;v+=.01*(a1+2*a2+2*a3+a4)/6
   py[i+1]=y;pv[i+1]=v
   if not np.all(np.isfinite(y)) or np.max(np.abs(y))>1000:return np.ones(np.sum(mask))*1e3
 if full:return py,pv
 return (py-Y)[mask]

def metrics(p,form,D):
 e=rollout(p,form,D);Y,V,U,M,ids=D
 py,pv=rollout(p,form,D,True)
 return {'rmse':float(np.sqrt(np.mean(e*e))),'bytraj':{str(k):float(np.sqrt(np.mean((py[:,j]-Y[:,j])[M[:,j]]**2))) for j,k in enumerate(ids)}}

orig_train=train.copy();vv=val.copy();vv.trajectory+=100;ALL=pack(pd.concat([train,vv],ignore_index=True))
def force(y,v,u,p,form):
 b,k,c,f,g,s=p[:6]
 if form=='polynomial':return b+k*y+c*v+g*u+p[6]*y**3+p[7]*y**5-f*np.tanh(v/s)
 if form=='statepoly':
  F=b+k*y+c*v+g*u+p[8]*y**3+p[9]*y**5
  ff=f+p[6]*np.sin(y)+p[7]*(np.cos(y)-1)
  return F-ff*np.tanh(v/s)
 if form=='simple':return b+k*np.sin(y)+c*v+g*u-f*np.tanh(v/s)
 F=b+k*np.sin(y)+c*v+g*u+p[8]*(np.cos(y)-1)+p[9]*np.sin(2*y)
 ff=f+p[6]*np.sin(y)+p[7]*(np.cos(y)-1)
 if form=='inputcubic':F+=p[10]*u*np.abs(u)
 if form=='inputdead':F+=p[10]*np.tanh(u/p[11])
 if form=='projection':return F-np.clip(F+v/s,-ff,ff)
 return F-ff*np.tanh(v/s)

import sys
label=sys.argv[1] if len(sys.argv)>1 else 'HarmonicFriction'
mapping={'HarmonicFriction':'harmonic','BoundedStiction':'projection','QuinticOscillator':'polynomial'}
form=mapping[label];r=json.load(open('final_results.json'))[form]
opt=least_squares(lambda p:rollout(p,form,ALL),r['initial'],bounds=tuple(r['bounds']),x_scale='jac',max_nfev=100,ftol=1e-8,diff_step=1e-4)
if form=='harmonic':
 opt=least_squares(lambda p:rollout(p,form,ALL),opt.x,bounds=tuple(r['bounds']),x_scale='jac',max_nfev=70,ftol=1e-9,diff_step=1e-6)
print(label,opt.x,metrics(opt.x,form,TR),metrics(opt.x,form,VA))
json.dump({'label':label,'p':opt.x.tolist(),'train':metrics(opt.x,form,TR),'val':metrics(opt.x,form,VA)},open('reproduced_'+label+'.json','w'),indent=2)
