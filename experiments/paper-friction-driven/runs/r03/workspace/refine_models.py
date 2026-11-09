import fit_models as fm
import numpy as np,json
from scipy.optimize import least_squares
# Extend compiled force function with further physically constrained structures.
from numba import njit
@njit
def accel(t,w,u,p,mode):
 g,b,c,k,s=p[:5];F=k*u-g*np.sin(t)-b*w;lo=-c;hi=c
 if mode==3: lo=-p[5]
 if mode==4: F=k*u-g*np.sin(t)*(1+p[5]*np.cos(t))-b*w
 if mode==5: F=k*u-g*np.sin(t)-b*w-p[5]*np.tanh(w/p[6])
 if mode==7: F=k*u-g*np.sin(t)*(1+p[5]*np.cos(t))-b*w;lo=-p[6]
 if mode==9: F=k*u/(1+p[5]*abs(u))-g*np.sin(t)-b*w
 if mode==10: lo=-c*(1+p[5]*np.cos(t));hi=-lo
 if mode==11: F=k*u-g*np.sin(t)*(1+p[5]*np.cos(t))-b*w-p[6]*np.tanh(w/p[7])
 if mode==12: F=k*u/(1+p[5]*abs(u))-g*np.sin(t)*(1+p[6]*np.cos(t))-b*w;lo=-p[7]
 if mode==13: F=k*u-g*np.sin(t)*(1+p[5]*np.tanh(t))-b*w
 if mode==2:return F-c*np.tanh(w/s)
 if mode==1:return F-c*np.tanh(w/s)-np.exp(-(w/s)**2)*min(c,max(-c,F))
 return F-min(hi,max(lo,F+w/s))
fm.accel=accel
# rebuild simulator with same code and new globals
exec(fm.sim.py_func.__code__.co_consts[0] if False else 'pass')
@njit
def sim(a,p,mode):
 n=len(a);out=np.empty(n);out[0]=a[0,0];t=a[0,0];w=a[0,1];h=.01
 for j in range(n-1):
  u=a[j,2];A=accel(t,w,u,p,mode);B=accel(t+h*w/2,w+h*A/2,u,p,mode);C=accel(t+h*(w+h*A/2)/2,w+h*B/2,u,p,mode);D=accel(t+h*(w+h*B/2),w+h*C,u,p,mode)
  t+=h*(w+2*(w+h*A/2)+2*(w+h*B/2)+(w+h*C))/6;w+=h*(A+2*B+2*C+D)/6;out[j+1]=t
 return out
fm.sim=sim
all_data=fm.train+fm.val
specs=[(0,'Projected',[108,1.6,19,26.5,.02],[70,.05,5,15,.004],[150,6,40,40,.12]),(1,'Compensated',[108,1.6,19,26.5,.5],[70,.05,5,15,.2],[150,6,40,40,2]),(3,'Asymmetric',[108,1.6,18,26.5,.02,21],[70,.05,5,15,.004,5],[150,6,40,40,.12,40]),(4,'Harmonic',[108,1.6,19,26.5,.02,.03],[70,.05,5,15,.004,-.5],[150,6,40,40,.12,.5]),(5,'SaturatingDamping',[108,.8,17,26.5,.02,4,3],[70,.01,5,15,.004,0,.5],[150,6,40,40,.12,20,15]),(7,'HarmonicAsymmetric',[108,1.6,18,26.5,.02,.03,21],[70,.05,5,15,.004,-.5,5],[150,6,40,40,.12,.5,40]),(9,'SaturatingMotor',[108,1.6,19,26.5,.02,.05],[70,.05,5,15,.004,0],[150,6,40,60,.12,.4]),(10,'AngleFriction',[108,1.6,19,26.5,.02,.05],[70,.05,5,15,.004,-.7],[150,6,40,40,.12,.7]),(11,'HarmonicDamping',[108,.8,17,26.5,.02,.03,4,3],[70,.01,5,15,.004,-.5,0,.5],[150,6,40,40,.12,.5,20,15]),(12,'HarmonicMotorAsymmetric',[108,1.6,18,26.5,.02,.05,.03,21],[70,.05,5,15,.004,0,-.5,5],[150,6,40,60,.12,.4,.5,40]),(13,'AsymmetricGravity',[108,1.6,19,26.5,.02,.03],[70,.05,5,15,.004,-.5],[150,6,40,40,.12,.5])]
def fit(spec,data,start=None):
 mode,label,x,lo,hi=spec
 if start is not None:x=start
 r=least_squares(fm.residual,x,args=(mode,data),bounds=(lo,hi),x_scale='jac',max_nfev=400,ftol=1e-9,xtol=1e-9,gtol=1e-7,diff_step=1e-4)
 return r
if __name__=='__main__':
 results=[]
 for spec in specs:
  mode,label,x,lo,hi=spec
  r=fit(spec,fm.train);p=r.x
  rec=dict(mode=mode,label=label,start=x,lower=lo,upper=hi,train_parameters=p.tolist(),train_rmse=float(np.sqrt(np.mean(r.fun**2))),val_rmse=float(np.sqrt(np.mean(fm.residual(p,mode,fm.val)**2))))
  r=fit(spec,all_data);p=r.x
  rec.update(parameters=p.tolist(),all_rmse=float(np.sqrt(np.mean(r.fun**2))),train_by=fm.metrics(p,mode,fm.train),val_by=fm.metrics(p,mode,fm.val))
  # Leave-one-trajectory-out test, each fit starts from full-data optimum but excludes held trajectory from its criterion.
  cv=[];cvp=[]
  for j,a in enumerate(all_data):
   r=fit(spec,all_data[:j]+all_data[j+1:],p)
   cv.append(float(np.sqrt(np.mean((sim(a,r.x,mode)[1:]-a[1:,0])**2))));cvp.append(r.x.tolist())
  rec.update(cv_by=cv,cv_parameters=cvp,cv_rmse=float(np.sqrt(np.average(np.array(cv)**2,weights=[len(a)-1 for a in all_data]))))
  results.append(rec);json.dump(results,open('refine_results.json','w'),indent=2)
  print(label,'train',rec['train_rmse'],'val',rec['val_rmse'],'all',rec['all_rmse'],'CV',rec['cv_rmse'],'p',p,flush=True)
