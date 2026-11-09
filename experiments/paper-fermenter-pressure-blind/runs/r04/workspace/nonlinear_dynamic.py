import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
tr=pd.read_csv('data/train.csv').values;va=pd.read_csv('data/val.csv').values
@njit
def f(p,y,u,w,kind):
 if kind==0:
  c=p[:6];h,b,a,d,e=p[6:];z=max(y-h,1e-6)**b;v=max(u,1e-6)**a*max(w,1e-6)**d;g=max(w,1e-6)**e
  return c[0]+c[1]*z+c[2]*v+c[3]*g+c[4]*v*z+c[5]*g*z
 if kind==1:
  c=p[:4];h,b,a,d,e=p[4:];z=max(y-h,1e-6)**b;v=max(u,1e-6)**a*max(w,1e-6)**d;g=max(w,1e-6)**e
  return c[0]+c[1]*z+c[2]*v+c[3]*g
 if kind==2:
  c=p[:10];z=(y-1.3)/.3
  return (c[0]+c[1]*z+c[2]*u+c[3]*w+c[4]*z*z+c[5]*z*u+c[6]*z*w+c[7]*u*u+c[8]*u*w+c[9]*w*w)/(1+p[10]*z*z)
 if kind==3:
  c=p[:5];z=np.sqrt(max(y-p[5],1e-6));v=np.exp(p[6]*(u-1))
  return c[0]+c[1]*z+c[2]*v+c[3]*w+c[4]*v*z
 if kind==4:
  c=p[:6];z=np.sqrt(max(y-p[6],1e-6));v=np.tanh(p[7]*(u-p[8]));g=np.tanh(p[9]*(w-p[10]))
  return c[0]+c[1]*z+c[2]*v+c[3]*g+c[4]*v*z+c[5]*g*z
@njit
def sim(p,d,kind,teacher=False):
 yp=np.empty(len(d));yp[0]=d[0,0]
 for k in range(len(d)-1):
  y=d[k,0] if teacher else yp[k];u=d[k,1]/70;w=d[k,2]/20
  a=f(p,y,u,w,kind);b=f(p,y+2.5*a,u,w,kind);c=f(p,y+2.5*b,u,w,kind);e=f(p,y+5*c,u,w,kind);yp[k+1]=y+5/6*(a+2*b+2*c+e)
  if not np.isfinite(yp[k+1]) or abs(yp[k+1])>100:yp[k+1:]=100;break
 return yp[1:]-d[1:,0]
@njit
def deriv(p,d,kind):
 return np.array([f(p,row[0],row[1]/70,row[2]/20,kind)-row[3] for row in d])
helpers=json.load(open('helper_refine_results.json'));poly=json.load(open('poly_results.json'));out=[]
for label,kind,p0,lo,hi in [
 ('power_cross',0,(lambda q:q['coefficients']+q['nonlinear_parameters'])(next(q for q in helpers if q['name']=='power_product_state_cross')),[-1]*6+[.8,.15,.1,0,.1],[1]*6+[.994,2,8,3,3]),
 ('power_additive',1,(lambda q:q['coefficients']+q['nonlinear_parameters'])(next(q for q in helpers if q['name']=='power_product_unbounded')),[-1]*4+[.8,.1,.1,0,.1],[1]*4+[.994,2,10,3,3]),
 ('rational',2,next(q for q in poly if q['kind']=='raw' and q['degree']==2)['coefficients']+[.1],[-2]*10+[0],[2]*10+[10]),
 ('exp_feedback',3,[.001,-.09,.004,.02,.025,.99,2],[-1]*5+[.8,0],[1]*5+[.994,8]),
 ('sigmoid_feedback',4,[0,-.1,.01,.02,.05,.01,.99,2,.8,2,.8],[-1]*6+[.8,.01,0,.01,0],[1]*6+[.994,20,2,20,2])]:
 print('starting',label,flush=True)
 start=np.array(p0);p0=least_squares(lambda p:deriv(p,tr,kind),start,bounds=(lo,hi),max_nfev=300).x
 one=least_squares(lambda p:sim(p,tr,kind,True),p0,bounds=(lo,hi),max_nfev=180).x
 for mode in ['train','both']:
  if mode=='train':fun=lambda p:sim(p,tr,kind)
  else:fun=lambda p:np.r_[sim(p,tr,kind),sim(p,va,kind)]
  res=least_squares(fun,one,bounds=(lo,hi),max_nfev=200,ftol=1e-8,xtol=1e-8,gtol=1e-8)
  p=res.x;rt=np.sqrt(np.mean(sim(p,tr,kind)**2));rv=np.sqrt(np.mean(sim(p,va,kind)**2));print(label,mode,rt,rv,'nfev',res.nfev,flush=True)
  out.append(dict(label=label+'_'+mode,kind=kind,initial=start.tolist(),derivative=p0.tolist(),onestep=one.tolist(),parameters=p.tolist(),rt=rt,rv=rv,lo=lo,hi=hi))
  json.dump(out,open('nonlinear_dynamic_results.json','w'),indent=2)
