import numpy as np,pandas as pd
from scipy.optimize import least_squares
from pathlib import Path
D={s:pd.read_csv('data/'+s+'.csv') for s in ['train','val']};L=[]
def out(s):print(s);L.append(s)
def f(t,p,v,q):
 a,c1,c2,c3,m=t[:5];g=c1*(1-v**3)+c2*(1-3*v*v+2*v**3)+c3*(1-v)**3
 return a*q-g*np.sign(p-1)*np.abs(p-1)**m

def rk(t,p,v,q):
 k1=f(t,p,v,q);k2=f(t,p+2.5*k1,v,q);k3=f(t,p+2.5*k2,v,q);k4=f(t,p+5*k3,v,q)
 return p+5/6*(k1+2*k2+2*k3+k4)
def inp(d,wv,wq):
 v=d.valve.to_numpy()/100;q=d.flow.to_numpy();return v[:-1]+wv*np.diff(v),q[:-1]+wq*np.diff(q)
for mode,wv,wq in [('currentval_nextflow',0,1),('nextval_currentflow',1,0),('currentval_avgflow',0,.5),('avgval_currentflow',.5,0),('learnmix',None,None)]:
 d=D['train'];p=d.p.to_numpy()
 def res(t):
  v,q=inp(d,t[5] if wv is None else wv,t[6] if wq is None else wq)
  return rk(t,p[:-1],v,q)-p[1:]
 init=[.0013,.064,.055,.00001,.55]+([0,.5] if mode=='learnmix' else [])
 lb=[0,0,0,0,.1]+([0,0] if mode=='learnmix' else [])
 ub=[.02,1,1,1,1.5]+([1,1] if mode=='learnmix' else [])
 fit=least_squares(res,init,bounds=(lb,ub),x_scale='jac',max_nfev=500)
 out(f'{mode} parameters {fit.x}')
 for name,d in D.items():
  t=fit.x;v,q=inp(d,t[5] if wv is None else wv,t[6] if wq is None else wq);p=d.p.to_numpy();res=rk(t,p[:-1],v,q)-p[1:]
  out(f'{name} one-step RMSE {np.sqrt(np.mean(res**2)):.9g} bar correlation next-current flow {np.corrcoef(res,np.diff(d.flow))[0,1]:.6g} valve {np.corrcoef(res,np.diff(d.valve))[0,1]:.6g}')
Path('helper_mixed.md').write_text('\n'.join(L))
