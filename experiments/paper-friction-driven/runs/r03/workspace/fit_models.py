import numpy as np, pandas as pd, json, time
from numba import njit
from scipy.optimize import least_squares
@njit
def accel(t,w,u,p,mode):
 g,b,c,k,s=p[:5]
 F=k*u-g*np.sin(t)-b*w
 lo=-c;hi=c
 if mode==3:
  lo=-p[5]; hi=c
 if mode==4: F=k*u-g*np.sin(t)*(1+p[5]*np.cos(t))-b*w
 if mode==5: F=k*u-g*np.sin(t)-b*w-p[5]*np.tanh(w/p[6])
 if mode==6: F=k*u+p[5]*u*abs(u)-g*np.sin(t)-b*w
 if mode==7: F=k*u-g*np.sin(t)*(1+p[5]*np.cos(t))-b*w;lo=-p[6];hi=c
 if mode==8: F=k*u-g*np.sin(t)-b*w-p[5]*w*abs(w)
 if mode==2: return F-c*np.tanh(w/s)
 if mode==1: return F-c*np.tanh(w/s)-np.exp(-(w/s)**2)*min(c,max(-c,F))
 return F-min(hi,max(lo,F+w/s))
@njit
def sim(a,p,mode):
 n=len(a); out=np.empty(n);out[0]=a[0,0]; t=a[0,0];w=a[0,1];h=.01
 for j in range(n-1):
  u=a[j,2]; A=accel(t,w,u,p,mode);B=accel(t+h*w/2,w+h*A/2,u,p,mode);C=accel(t+h*(w+h*A/2)/2,w+h*B/2,u,p,mode);D=accel(t+h*(w+h*B/2),w+h*C,u,p,mode)
  t+=h*(w+2*(w+h*A/2)+2*(w+h*B/2)+(w+h*C))/6;w+=h*(A+2*B+2*C+D)/6;out[j+1]=t
 return out

def load(f):
 return [g[['theta','omega','u','domega']].to_numpy() for _,g in pd.read_csv('data/'+f+'.csv').groupby('trajectory',sort=False)]
train=load('train');val=load('val')
def residual(p,mode,data=train): return np.concatenate([(sim(a,p,mode)-a[:,0])[1:] for a in data])
def metrics(p,mode,data):return [float(np.sqrt(np.mean((sim(a,p,mode)[1:]-a[1:,0])**2))) for a in data]

def run(mode,label,start,lower,upper):
 begin=time.time(); runs=[]
 for x in start:
  r=least_squares(residual,x,args=(mode,),bounds=(lower,upper),x_scale='jac',max_nfev=500,ftol=1e-10,xtol=1e-10,gtol=1e-8,diff_step=1e-4)
  runs.append((np.sum(r.fun**2),r.x,r.nfev));print(label,'fit',runs[-1],flush=True)
 _,p,nfev=min(runs,key=lambda z:z[0]); result=dict(mode=mode,label=label,parameters=p.tolist(),starts=start,lower=lower,upper=upper,nfev=int(nfev),train_rmse=float(np.sqrt(np.mean(residual(p,mode)**2))),val_rmse=float(np.sqrt(np.mean(residual(p,mode,val)**2))),train_by=metrics(p,mode,train),val_by=metrics(p,mode,val),seconds=time.time()-begin)
 print(json.dumps(result),flush=True);return result
if __name__=='__main__':
 results=[]
 specs=[(0,'Projected',[[108,1.6,19,26.5,.02],[108,1.6,19,26.5,.05]],[70,.05,5,15,.006],[150,6,40,40,.12]),(1,'Compensated',[[108,1.6,19,26.5,.5],[108,1.6,19,26.5,1.]],[70,.05,5,15,.25],[150,6,40,40,2.]),(2,'Smooth',[[108,1.6,19,26.5,.3]],[70,.05,5,15,.25],[150,6,40,40,2.]),(3,'Asymmetric',[[108,1.6,18,26.5,.02,21]],[70,.05,5,15,.006,5],[150,6,40,40,.12,40]),(4,'Harmonic',[[108,1.6,19,26.5,.02,.03]],[70,.05,5,15,.006,-.5],[150,6,40,40,.12,.5]),(5,'SaturatingDamping',[[108,.8,17,26.5,.02,4,3]],[70,.01,5,15,.006,0,.5],[150,6,40,40,.12,20,15]),(6,'NonlinearMotor',[[108,1.6,19,26.5,.02,.2]],[70,.05,5,15,.006,0],[150,6,40,40,.12,2])]
 for spec in specs:
  results.append(run(*spec));json.dump(results,open('fit_results.json','w'),indent=2)
