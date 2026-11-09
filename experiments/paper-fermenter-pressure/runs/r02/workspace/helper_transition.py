import numpy as np,pandas as pd
from scipy.optimize import least_squares
from pathlib import Path
D={s:pd.read_csv('data/'+s+'.csv') for s in ['train','val']};lines=[]
def out(s): print(s);lines.append(s)
def inputs(d,align):
 v=d.valve.to_numpy()/100;q=d.flow.to_numpy()
 if align=='current':return v[:-1],q[:-1]
 if align=='next':return v[1:],q[1:]
 return (v[:-1]+v[1:])/2,(q[:-1]+q[1:])/2
# positive Bernstein increments enforce monotonic conductance vs opening
def f(t,p,v,q,hkind):
 a,c1,c2,c3,m=t
 g=c1*(1-v**3)+c2*(1-3*v*v+2*v**3)+c3*(1-v)**3
 x=p-1
 if hkind=='power':h=np.sign(x)*np.abs(x)**m
 elif hkind=='linear':h=x
 elif hkind=='root':h=np.sign(x)*np.sqrt(np.abs(x))
 elif hkind=='compressible':h=np.sign(x)*np.sqrt(np.abs(p*p-1))
 elif hkind=='smoothroot':h=x/(x*x+.0001)**.25
 return a*q-g*h

def rk(t,p,v,q,kind):
 k1=f(t,p,v,q,kind);k2=f(t,p+2.5*k1,v,q,kind);k3=f(t,p+2.5*k2,v,q,kind);k4=f(t,p+5*k3,v,q,kind)
 return p+5/6*(k1+2*k2+2*k3+k4)
for kind in ['power','linear','root','compressible','smoothroot']:
 for align in ['current','next','average']:
  d=D['train'];p=d.p.to_numpy();v,q=inputs(d,align)
  init=[.001,.06,.04,.04,.6]
  # unconstrained m ignored for fixed variants, remove it from fit
  def full(t): return t if kind=='power' else np.r_[t,.5]
  x0=init if kind=='power' else init[:-1]
  lb=[0,0,0,0,.1] if kind=='power' else [0]*4
  ub=[.02,1,1,1,1.5] if kind=='power' else [.02,1,1,1]
  fit=least_squares(lambda t:rk(full(t),p[:-1],v,q,kind)-p[1:],x0,bounds=(lb,ub),x_scale='jac',max_nfev=300)
  t=full(fit.x);out(f'kind={kind} align={align} train fit parameters a,c1,c2,c3,m: {t}')
  for name,d in D.items():
   v,q=inputs(d,align);p=d.p.to_numpy();res=rk(t,p[:-1],v,q,kind)-p[1:]
   delta_v=np.diff(d.valve);delta_q=np.diff(d.flow)
   changed=(abs(delta_v)>3)|(abs(delta_q)>1)
   out(f'{name} one step RMSE={np.sqrt(np.mean(res*res)):.9g} bar; major-change RMSE={np.sqrt(np.mean(res[changed]**2)):.9g} bar n={changed.sum()}; other RMSE={np.sqrt(np.mean(res[~changed]**2)):.9g} bar n={(~changed).sum()}')
   if align=='current':
    ps=np.empty_like(p);ps[0]=p[0]
    for j in range(len(v)):ps[j+1]=rk(t,ps[j],v[j],q[j],kind)
    out(f'{name} autonomous RK4 rollout RMSE={np.sqrt(np.mean((ps[1:]-p[1:])**2)):.9g} bar; min={ps.min():.9g} bar max={ps.max():.9g} bar')
    dvres=np.corrcoef(res,delta_v)[0,1];dqres=np.corrcoef(res,delta_q)[0,1]
    out(f'{name} one-step residual correlation with next-current valve={dvres:.6g}, flow={dqres:.6g}')
Path('helper_transition.md').write_text('\n'.join(lines))
