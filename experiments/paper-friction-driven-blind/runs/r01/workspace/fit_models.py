import os,json,time
import numpy as np,pandas as pd
from scipy.optimize import least_squares
from numba import njit

# Family codes: affine, cubic, sine, sine/friction, cubic/friction,
# sine/state-dependent friction, sine/second-harmonic friction, sine/deadzone drive.
NAMES=['affine','cubic','sine','sine_friction','cubic_friction','state_friction','harmonic_friction','deadzone']
@njit
def acc(y,v,u,p,f):
 c,a,b,g=p[0:4]
 if f==0: return c-a*y-b*v+g*u
 if f==1: return c-a*y+p[4]*y**3-b*v+g*u
 if f==2: return c-a*np.sin(p[4]*y)-b*v+g*u
 if f==4: return c-a*y+p[4]*y**3-b*v+g*u-p[5]*np.tanh(v/p[6])
 force=c-a*np.sin(p[4]*y)+g*u
 if f==7:
  # Smooth static-friction drive deadzone. Width scale p[7] is fitted.
  d=p[5]; w=p[7]
  force=.5*((force-d)+np.sqrt((force-d)**2+w*w))-.5*((-force-d)+np.sqrt((-force-d)**2+w*w))
  return force-b*v-p[6]*np.tanh(v/p[8])
 fr=p[5]
 if f==5: fr=fr*(1+p[7]*y*y)
 if f==6: force += p[7]*np.sin(2*p[4]*y)
 return force-b*v-fr*np.tanh(v/p[6])

@njit
def sim(p,f,A,lengths):
 out=np.zeros((A.shape[0],A.shape[1],2))
 for j in range(A.shape[0]):
  y,v=A[j,0,0],A[j,0,1];out[j,0,0]=y;out[j,0,1]=v
  for k in range(lengths[j]-1):
   u=A[j,k,2]
   a1=acc(y,v,u,p,f); k1=v
   a2=acc(y+.005*k1,v+.005*a1,u,p,f);k2=v+.005*a1
   a3=acc(y+.005*k2,v+.005*a2,u,p,f);k3=v+.005*a2
   a4=acc(y+.01*k3,v+.01*a3,u,p,f);k4=v+.01*a3
   y+=.01/6*(k1+2*k2+2*k3+k4);v+=.01/6*(a1+2*a2+2*a3+a4)
   if not np.isfinite(y) or not np.isfinite(v) or abs(y)>1000 or abs(v)>1000:
    for kk in range(k+1,lengths[j]):out[j,kk,0]=1000;out[j,kk,1]=1000
    break
   out[j,k+1,0]=y;out[j,k+1,1]=v
 return out

def load(file):
 d=pd.read_csv(file);groups=list(d.groupby('trajectory',sort=False));L=np.array([len(g) for _,g in groups]);A=np.zeros((len(L),max(L),4));M=np.zeros(A.shape[:2],bool)
 for j,(_,g) in enumerate(groups):A[j,:len(g)]=g[['y','x1','x2','dx1']];M[j,1:len(g)]=1
 return d,A,L,M
D,A,L,M=load('data/train.csv');V,Av,Lv,Mv=load('data/val.csv')
y,v,u=D.y.values,D.x1.values,D.x2.values;target=D.dx1.values

def derivative_init(f):
 if f in (0,1,4): terms=[np.ones(len(y)),-y,-v,u]
 else: terms=[np.ones(len(y)),-np.sin(y),-v,u]
 if f in (1,4):terms.append(y**3)
 if f==2:pass
 if f in (3,5,6,7,4):terms.append(-np.tanh(v/.5))
 if f==5:terms.append(-y*y*np.tanh(v/.5))
 if f==6:terms.append(np.sin(2*y))
 q=np.linalg.lstsq(np.column_stack(terms),target,rcond=None)[0]
 if f==0:return q,([-10,1,0,1],[10,300,30,100])
 if f==1:return q,([-10,1,0,1,-100],[10,300,30,100,100])
 if f==2:return np.r_[q,1.],([-10,1,0,1,.4],[10,300,30,100,1.6])
 if f==4:return np.r_[q[:5],max(q[5],.1),.5],([-10,1,0,1,-100,0,.12],[10,300,30,100,100,60,5])
 if f==3:return np.r_[q[:4],1.,q[4],.5],([-10,1,0,1,.4,0,.12],[10,300,30,100,1.6,60,5])
 if f==5:return np.r_[q[:4],1.,max(q[4],.1),.5,max(q[5]/max(q[4],.1),0)],([-10,1,0,1,.4,0,.12,0],[10,300,30,100,1.6,60,5,2])
 if f==6:return np.r_[q[:4],1.,max(q[4],.1),.5,q[5]],([-10,1,0,1,.4,0,.12,-60],[10,300,30,100,1.6,60,5,60])
 return np.array([q[0],q[1],q[2],q[3],1.,10.,5.,2.,.5]),([-10,1,0,1,.4,0,0,.05,.12],[10,300,30,100,1.6,40,40,20,5])

def resid(p,f): return (sim(p,f,A,L)[:,:,0]-A[:,:,0])[M]
def metrics(p,f):
 tr=sim(p,f,A,L);va=sim(p,f,Av,Lv)
 return {'train_rmse':float(np.sqrt(np.mean((tr[:,:,0]-A[:,:,0])[M]**2))), 'val_rmse':float(np.sqrt(np.mean((va[:,:,0]-Av[:,:,0])[Mv]**2))), 'val_per_trajectory':[float(np.sqrt(np.mean((va[j,1:l,0]-Av[j,1:l,0])**2))) for j,l in enumerate(Lv)],'train_per_trajectory':[float(np.sqrt(np.mean((tr[j,1:l,0]-A[j,1:l,0])**2))) for j,l in enumerate(L)]}

if __name__=='__main__':
 results={}
 for f,name in enumerate(NAMES):
  p,bounds=derivative_init(f);p=np.maximum(np.minimum(p,np.array(bounds[1])-.00001),np.array(bounds[0])+.00001)
  print(name,'initial',p,metrics(p,f),flush=True)
  st=time.time(); opt=least_squares(resid,p,args=(f,),bounds=bounds,x_scale='jac',max_nfev=220,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  m=metrics(opt.x,f);print('FIT',name,opt.x,m,'time',time.time()-st,flush=True)
  results[name]={'family':f,'initial':p.tolist(),'bounds':bounds,'p':opt.x.tolist(),'nfev':opt.nfev,'cost':opt.cost,'metrics':m}
  with open('fit_results.json','w') as h:json.dump(results,h,indent=2)
