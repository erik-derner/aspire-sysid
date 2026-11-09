import json,math,numpy as np,pandas as pd
from pathlib import Path
from fit_models import D,f,rollout
R=json.loads(Path('fixed_results.json').read_text())['pooled']; lines=[]
for r in R:
 m=json.loads(Path('models/'+r['label']+'.json').read_text());env={q['name']:q['value'] for q in m['parameters']};env.update({'Max':max,'Min':min,'sqrt':math.sqrt});code=compile(m['expressions']['dp'],'<model>','eval')
 def fn(p,v,q):return eval(code,{'__builtins__':{}},dict(env,p=p,valve=v,flow=q))
 def rk(p,v,q):
  k1=fn(p,v,q);k2=fn(p+2.5*k1,v,q);k3=fn(p+2.5*k2,v,q);k4=fn(p+5*k3,v,q)
  return p+5/6*(k1+2*k2+2*k3+k4)
 lines.append(r['label'])
 for name,d in D.items():
  difference=max(abs(fn(p,v,q)-f(np.array(r['parameters']),p,v,q,r['family'],0)) for p,v,q,dp in d)
  y=[d[0,0]]
  for row in d[:-1]:y.append(rk(y[-1],row[1],row[2]))
  e=np.array(y)-d[:,0];lines.append(f'{name}: max JSON-to-fit RHS difference {difference:.9g} bar/s; JSON rollout RMSE {np.sqrt(np.mean(e[1:]**2)):.9g} bar; range {min(y):.9g} to {max(y):.9g} bar.')
  df=pd.DataFrame(d[:-1],columns=['p','valve','flow','dp']);df['free_run_error']=e[:-1]
  tr=np.array([rk(p,v,q)-d[i+1,0] for i,(p,v,q,dp) in enumerate(d[:-1])]);df['transition_error']=tr
  for col,bins in [('p',[.97,1.1,1.3,1.5,1.7,1.9,2.3]),('valve',[0,30,50,65,75,85,100]),('flow',[0,10,15,20,25,35])]:
   lines.append(df.groupby(pd.cut(df[col],bins),observed=True)[['free_run_error','transition_error']].agg(['mean','std','count']).to_string())
  lines.append('Consecutive sixth-trajectory block free-run RMSE in bar: '+str([float(np.sqrt(np.mean(ee**2))) for ee in np.array_split(e[1:],6)]))
 ps=[-.1,.5,.999,1,1.0001,1.01,1.1,1.5,2.3,5];vs=np.linspace(0,100,101)
 min_flow_diff=min(fn(p,v,30)-fn(p,v,0) for p in ps for v in vs)
 min_closure_diff=min(fn(p,v+1,10)-fn(p,v,10) for p in ps for v in vs[:-1])
 zero_equilibrium=max(abs(fn(1,v,0)) for v in vs)
 assert min_flow_diff>=0 and min_closure_diff>=-1e-14 and zero_equilibrium==0
 assert all(fn(p,100,q)>=0 for p in ps for q in [0,10,30])
 lines.append(f'Grid checks: minimum flow increment RHS {min_flow_diff:.9g} bar/s; minimum 1%-closure increment RHS {min_closure_diff:.9g} bar/s; atmospheric zero-flow RHS {zero_equilibrium:.9g} bar/s. Sealed nondecrease checks pass.')
 errors=[]
 for start in [.7,1.0001,2.3]:
  for valve in [0,30,90]:
   p=start
   for i in range(400):p=rk(p,valve,0)
   errors.append(abs(p-1))
 lines.append(f'Zero-flow relaxation stress: nine starts/strokes simulated for 2000 s; maximum final atmospheric error {max(errors):.9g} bar.')
 # open-valve restoring slope over low and high pressures
 pgrid=np.r_[np.linspace(1,1.5,2001),np.linspace(1.5,10,1000)];slopes=[-(fn(p+1e-7,0,0)-fn(p,0,0))/1e-7 for p in pgrid]
 lines.append(f'Numerical open-valve pressure restoring slopes on 1 to 10 bar grid: {min(slopes):.9g} to {max(slopes):.9g} 1/s.')
Path('final_diagnostics.txt').write_text('\n'.join(lines));print('\n'.join([s for s in lines if not '\n' in s]))
