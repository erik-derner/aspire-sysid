import numpy as np,pandas as pd
from scipy.optimize import least_squares
from scipy.stats import pearsonr
from pathlib import Path
D={s:pd.read_csv('data/'+s+'.csv') for s in ['train','val']}
lines=[]
def out(x):
 print(x);lines.append(str(x))
for name,d in D.items():
 out('\n'+name+' '+str(d.shape)+' columns '+str(list(d.columns)))
 out(d.describe().to_string())
 p=d.p.to_numpy();dp=d.dp.to_numpy();fd=np.diff(p)/5
 for lag in range(-3,4):
  idx=np.arange(len(fd));idx=idx[(idx+lag>=0)&(idx+lag<len(dp))]
  x=fd[idx];y=dp[idx+lag]
  out(f'dp comparison lag {lag}: RMSE {np.sqrt(np.mean((x-y)**2)):.9g} bar/s corr {np.corrcoef(x,y)[0,1]:.9g}')
 for col in ['valve','flow']:
  a=d[col].to_numpy(); delta=np.diff(a)
  out(col+' changes '+str(np.sum(abs(delta)>1e-8))+' unique '+str(len(np.unique(a)))+' largest changes '+str(sorted(abs(delta),reverse=True)[:10]))
# physically structured separable outflow: a flow - b g(valve) h(p), g=(1-valve/100)^n or exp(-kv)-exp(-k)
def pred(theta,p,v,q,kind):
 a,b,n,m=theta
 z=np.maximum(1-v/100,0)
 g=z**n if kind=='power' else (np.exp(-n*v/100)-np.exp(-n))
 h=np.sign(p-1)*np.abs(p-1)**m
 return a*q-b*g*h
for kind in ['power','exponential']:
 for align in ['current','next','average']:
  tr=D['train'];p=tr.p.to_numpy()[:-1];target=np.diff(tr.p)/5
  def inputs(d):
   v=d.valve.to_numpy();q=d.flow.to_numpy()
   return (v[:-1],q[:-1]) if align=='current' else ((v[1:],q[1:]) if align=='next' else ((v[:-1]+v[1:])/2,(q[:-1]+q[1:])/2))
  v,q=inputs(tr)
  fit=least_squares(lambda t:pred(t,p,v,q,kind)-target,[.001,.02,2,.5],bounds=([0,0,.05,.05],[.1,10,20,3]),x_scale='jac',max_nfev=1000)
  out(f'\n{kind} {align} parameters a,b,n,m {fit.x}')
  for name,d in D.items():
   v,q=inputs(d);p=d.p.to_numpy()[:-1];target=np.diff(d.p)/5;res=pred(fit.x,p,v,q,kind)-target
   changed=(abs(np.diff(d.valve))>.01)|(abs(np.diff(d.flow))>.01)
   out(f'{name} derivative RMSE {np.sqrt(np.mean(res**2)):.9g} bar/s change {np.sqrt(np.mean(res[changed]**2)):.9g} unchanged {np.sqrt(np.mean(res[~changed]**2)):.9g} bias {res.mean():.9g} bar/s')
   if align=='current':
    x=d.p.iloc[0];ps=[x]
    for vv,qq in zip(d.valve.to_numpy()[:-1],d.flow.to_numpy()[:-1]):
     f=lambda xx:pred(fit.x,xx,vv,qq,kind)
     k1=f(x);k2=f(x+2.5*k1);k3=f(x+2.5*k2);k4=f(x+5*k3);x=x+5/6*(k1+2*k2+2*k3+k4);ps.append(x)
    out(f'{name} rollout RMSE {np.sqrt(np.mean((np.array(ps[1:])-d.p.to_numpy()[1:])**2)):.9g} bar')
    bins=pd.DataFrame({'p':p,'v':v,'res':res})
    out('residual pressure bins '+str(bins.groupby(pd.cut(bins.p,5),observed=False).res.agg(['mean','std']).to_dict()))
    out('residual valve bins '+str(bins.groupby(pd.cut(bins.v,5),observed=False).res.agg(['mean','std']).to_dict()))
Path('helper_inspect.md').write_text('\n'.join(lines))
