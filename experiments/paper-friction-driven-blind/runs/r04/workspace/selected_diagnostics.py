import numpy as np,json,pandas as pd
from fit_rollout import load
from fit_extra import simx,acc as accx
from fit_final import simf,acc as accf
from fit_friction import simh,acc as acch
S=[('ShiftedSine','extra_results.json','shifted',simx,accx),('Duffing','final_results.json','cubic_bias',simf,accf),('HarmonicLinear','final_results.json','sin_linear_cos',simf,accf),('Hybrid','friction_results.json','karnopp',simh,acch)]
report={}
for label,file,key,fun,afun in S:
 r=json.load(open(file))[key];p=np.array(r['p']);k=r['kind'];o={}
 for split in ['train','val']:
  tab=[];es=[];vs=[];ars=[]
  for i,a in enumerate(load('data/'+split+'.csv')):
   z=fun(a,p,k);e=z[1:,0]-a[1:,0];es.extend(e);vs.extend(a[1:,1]);ars.extend([afun(y,v,u,p,k)-dv for y,v,u,dv in a[1:]])
   tab.append({'trajectory':i+1,'rmse_y':float(np.sqrt(np.mean(e**2))),'mean_error_y':float(e.mean()),'final_error_y':float(e[-1]),'max_abs_sim_y':float(abs(z[:,0]).max()),'max_abs_sim_x1':float(abs(z[:,1]).max())})
  es=np.array(es);vs=np.array(vs);ars=np.array(ars)
  o[split]={'rmse_y':float(np.sqrt(np.mean(es**2))),'mean_error_y':float(es.mean()),'acceleration_rmse':float(np.sqrt(np.mean(ars**2))),'small_velocity_mean_y_error':float(es[abs(vs)<.5].mean()),'small_velocity_rmse_y':float(np.sqrt(np.mean(es[abs(vs)<.5]**2))),'trajectories':tab}
 report[label]=o
 print(label,o)
json.dump(report,open('selected_diagnostics.json','w'),indent=2)
