import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
# a=x1/60, b=x2/20. Parameters rate k, feedback g, reference y0, source c, exponent n, then optional modifiers.
@njit
def fun(y,a,b,p,model):
 k,g,y0,c,n=p[:5]
 z=y-y0;source=c*max(b,0)**n
 if model==0:return -k*(1-g*a)*z+source
 if model==1:return -k*np.exp(-g*a)*z+source
 if model==2:return -k*(1-g*a)*np.log(max(y/y0,1e-10))+source
 if model==3:return -k*(1-g*a)*z/(1+p[5]*max(z,0))+source
 if model==4:return (-k*(1-g*a)*z+source)/(1+p[5]*max(z,0))
 if model==5:return -k*(1-g*a)*z+source+p[5]*a**3
 if model==6:return -k*(1-g*a-p[5]*b)*z+source
 if model==7:return -k*np.exp(-g*a-p[5]*b)*z+source
 if model==8:return -k*(1-g*a)*(max(y,1e-10)**p[5]-y0**p[5])+source
 if model==9:return -k*(1-g*a)*z+source/(1+p[5]*b*b)
 if model==10:return -k*(1-g*a)*z+source*np.exp(-p[5]*b)
 if model==11:return -k*(1-g*a)*np.tanh(p[5]*z)/p[5]+source
 if model==12:return (-k*(1-g*a)*z+source)/(1+p[5]*a)
 if model==13:return -k*np.exp(-g*a)*np.log(max(y/y0,1e-10))+source
 if model==14:return -k*(1-g*a-p[5]*b)*z+source+p[6]*a**3
 return 0.
@njit
def sim(p,model,yy,a,b):
 v=yy[0];r=np.empty(len(yy)-1)
 for i in range(len(r)):
  k1=fun(v,a[i],b[i],p,model);k2=fun(v+2.5*k1,a[i],b[i],p,model);k3=fun(v+2.5*k2,a[i],b[i],p,model);k4=fun(v+5*k3,a[i],b[i],p,model)
  v+=5/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(v) or abs(v)>100:
   for j in range(i,len(r)):r[j]=1000
   return r
  r[i]=v-yy[i+1]
 return r
@njit
def dr(p,model,y,a,b,target):
 r=np.empty(len(y))
 for i in range(len(y)):r[i]=fun(y[i],a[i],b[i],p,model)-target[i]
 return r
names=['affine_rate','exponential_rate','log_feedback','rational_feedback','rational_time','cubic_source','two_input_rate','exponential_two_input_rate','power_feedback','saturating_source','gamma_source','tanh_feedback','input_time','log_exp_rate','two_rate_cubic']
if __name__=='__main__':
 ds={'train':tr,'val':va};records=[];rng=np.random.default_rng(15)
 for model,name in enumerate(names):
  start=np.array([.15,.55,1.,.01,2.]+([.5] if model in [3,4,9,10,11,12] else ([1.] if model==8 else ([.05] if model in [6,7] else ([.001] if model==5 else ([] if model in [0,1,2,13] else [.05,.001]))))))
  lo=np.array([.0001,-5,.7,0,.2]+([0.] if model in [3,4,9,10,12] else ([.1] if model in [8,11] else ([-2.] if model in [5,6,7] else ([] if model in [0,1,2,13] else [-2.,-2.])))))
  hi=np.array([5.,5,1.3,.5,8.]+([10.] if model in [3,4,9,10,12] else ([5.] if model in [8,11] else ([2.] if model in [5,6,7] else ([] if model in [0,1,2,13] else [2.,2.])))))
  args=(model,tr.y.values,tr.x1.values/60,tr.x2.values/20)
  best=None;starts=[]
  for j in range(3):
   p=start.copy() if j==0 else np.clip(start*(1+rng.normal(0,.2,len(start))),lo+1e-8,hi-1e-8);starts.append(p.tolist())
   sol=least_squares(lambda p:dr(p,*args,tr.dy.values),p,bounds=(lo,hi),max_nfev=1200,ftol=1e-10,gtol=1e-10,xtol=1e-10)
   if best is None or sol.cost<best.cost:best=sol
  for stage in ['der','roll']:
   if stage=='der':p=best.x;init=starts
   else:
    init=p.tolist();sol=least_squares(lambda p:sim(p,*args),p,bounds=(lo,hi),max_nfev=500,x_scale='jac',ftol=1e-10,gtol=1e-10,xtol=1e-10);p=sol.x
   rec={'name':name,'model':model,'stage':stage,'p':p.tolist(),'starts':init,'bounds':[lo.tolist(),hi.tolist()]}
   for fn,d in ds.items():
    aa=(model,d.y.values,d.x1.values/60,d.x2.values/20);rec[fn+'_der']=float(np.mean(dr(p,*aa,d.dy.values)**2)**.5);rec[fn+'_roll']=float(np.mean(sim(p,*aa)**2)**.5)
   records.append(rec);print({k:v for k,v in rec.items() if k not in ['starts','bounds']});json.dump(records,open('nonlinear_results.json','w'),indent=2)
