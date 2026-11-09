import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
from refine import PolyModel,RationalModel,StableModel,rollout,refine
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
class CosModel:
 def __init__(self):self.m=8;self.kind='cos';self.eps=.001
 def fg(self,z,u,v,c):
  b0,b1,d0,d1,h,p,q,r=c;s=z+1-h;W=s*s+self.eps**2;H=W**((p-1)/2);g=s*H;gz=H*(1+(p-1)*s*s/W)
  v=max(v,1e-12);angle=u*np.pi/3;co=max(np.cos(angle),1e-12);V=v**q;C=co**r;D=d0+d1*C
  f=b0+b1*V-D*g
  G=np.array([1,V,-g,-C*g,D*gz,-D*.5*g*np.log(W),b1*V*np.log(v),-d1*C*np.log(co)*g])
  return f,-D*gz,G
class PowerModel:
 def __init__(self):self.m=11;self.kind='power';self.eps=.001
 def fg(self,z,u,v,c):
  b0,b1,b2,b3,d0,d1,d2,h,p,q,r=c;s=z+1-h;W=s*s+self.eps**2;H=W**((p-1)/2);g=s*H;gz=H*(1+(p-1)*s*s/W)
  v=max(v,1e-12);V=v**q;B=d0+d1*u+d2*u*u;D=B*B
  # additional state-dependent damping r*g*z term; r bound >=0
  f=b0+b1*u+b2*u*u+b3*V-D*g-r*g*z
  G=np.array([1,u,u*u,V,-2*B*g,-2*B*u*g,-2*B*u*u*g,(D+r*z)*gz,-(D+r*z)*.5*g*np.log(W),b3*V*np.log(v),-g*z])
  return f,-(D+r*z)*gz-r*g,G

def derivative_fit(m,start,bounds):
 rows=tr[['y','x1','x2']].values
 def fun(c):return np.array([m.fg(y-1,u/60,v/20,c)[0] for y,u,v in rows])-tr.dy.values
 def jac(c):return np.array([m.fg(y-1,u/60,v/20,c)[2] for y,u,v in rows])
 return least_squares(fun,start,jac=jac,bounds=bounds,x_scale='jac',max_nfev=500,ftol=1e-10,xtol=1e-10,gtol=1e-10).x

def scores(m,c):
 return dict(roll=[float(np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2))) for d in [tr,va]],der=[float(np.sqrt(np.mean((np.array([m.fg(y-1,u/60,v/20,c)[0] for y,u,v in d[['y','x1','x2']].values])-d.dy.values)**2))) for d in [tr,va]])
if __name__=='__main__':
 res=[];specs=[]
 # Structure is fixed before these final fits. Existing train-only fits are deterministic initializations.
 for label in ['poly3']:
  z=next(z for z in json.load(open('refine_results.json')) if z['label']==label)
  specs.append((label,PolyModel(z['powers']),np.array(z['coef']),None,'refine_results.json:'+label))
 z=next(z for z in json.load(open('nonlinear_more_results.json')) if z['label']=='rational2')
 m=RationalModel(z['powers']);specs.append(('rational2',m,np.array(z['coef']),(np.r_[np.full(m.m-1,-np.inf),0],np.full(m.m,np.inf)),'nonlinear_more_results.json:rational2'))
 m=CosModel();z=next(z for z in json.load(open('valve_explore_results.json')) if z['label']=='cos');h,p,q,r=z['theta'];start=np.r_[z['coef'],h,p,q,r]
 bounds=(np.array([-np.inf,0,0,0,.8,.1,.1,.1]),np.array([np.inf,np.inf,np.inf,np.inf,1.02,2,4,5]))
 init=derivative_fit(m,start,bounds);c,opt=refine(m,init,[tr],bounds=bounds,maxn=100)
 print('cos train-only',scores(m,c),c,flush=True)
 specs.append(('cos_power',m,c,bounds,'train-only derivative then rollout fits in final_fit.py'))
 res.append(dict(label='cos_power_train',der_start=start.tolist(),der_coef=init.tolist(),coef=c.tolist(),scores=scores(m,c)))
 m=PowerModel();start=np.array([.003,-.01,.01,.02,.30,-.01,-.06,.99,.5,1,0]);bounds=(np.r_[np.full(7,-np.inf),.8,.1,.1,0],np.r_[np.full(7,np.inf),1.02,2,4,1])
 init=derivative_fit(m,start,bounds);c,opt=refine(m,init,[tr],bounds=bounds,maxn=100)
 print('power train-only',scores(m,c),c,flush=True)
 specs.append(('power_damping',m,c,bounds,'train-only derivative then rollout fits in final_fit.py'))
 res.append(dict(label='power_damping_train',der_start=start.tolist(),der_coef=init.tolist(),coef=c.tolist(),scores=scores(m,c)))
 # All final parameters minimize uninterrupted trajectory error on both provided files.
 for label,m,start,bounds,source in specs:
  begin=time.time();c,opt=refine(m,start,[tr,va],bounds=bounds,maxn=120)
  ss=scores(m,c)
  print('FINAL',label,'sec',time.time()-begin,'nfev',opt.nfev,ss,'coef',c,flush=True)
  res.append(dict(label=label,kind=m.kind,powers=m.p.tolist() if hasattr(m,'p') else None,start=start.tolist(),start_source=source,coef=c.tolist(),scores=ss,nfev=opt.nfev,bounds=None if bounds is None else [np.array(bounds[0]).tolist(),np.array(bounds[1]).tolist()]))
  json.dump(res,open('final_fit_results.json','w'),indent=2)
