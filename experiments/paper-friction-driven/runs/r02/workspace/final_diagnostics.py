import numpy as np,json,pandas as pd
from refit_pool import SPECS,simulate
out={};results=json.load(open('refit_results.json'))
for label,(mod,f,path) in SPECS.items():
 p=results[label]['p'];df=pd.concat([pd.read_csv('data/train.csv'),pd.read_csv('data/val.csv')],ignore_index=True)
 y=np.array([mod.accel(t,w,u,np.array(p),f) if hasattr(mod,'accel') else mod.acc(t,w,u,np.array(p),f) for t,w,u in df[['theta','omega','u']].to_numpy()])
 r=y-df.domega.to_numpy();m=abs(df.omega.to_numpy())>1
 d={'accel_rmse_all':float(np.sqrt(np.mean(r*r))),'accel_rmse_moving':float(np.sqrt(np.mean(r[m]**2))),'accel_mean_moving':float(np.mean(r[m]))}
 for key,mask in [('negative',m&(df.omega.to_numpy()<0)),('positive',m&(df.omega.to_numpy()>0)),('large_negative_angle',m&(df.theta.to_numpy()<-2))]:
  d[key]={'count':int(mask.sum()),'mean':float(np.mean(r[mask])),'rmse':float(np.sqrt(np.mean(r[mask]**2)))}
 # extended unforced persistence: stationary measured free response endpoints held for another 20 seconds
 endpoints=[]
 for file in ['data/train.csv','data/val.csv']:
  for _,gg in pd.read_csv(file).groupby('trajectory'):
   if max(abs(gg.u))==0 and abs(gg.iloc[-1].omega)<1e-5:endpoints.append(float(gg.iloc[-1].theta))
 drift=[]
 for th in endpoints:
  rows=np.zeros((2001,3));rows[0,0]=th
  pred=simulate(mod,np.array(p),f,rows,np.array([len(rows)]));drift.append(float(pred[-1]-th))
 d['20s_static_test_initial_angles']=endpoints;d['20s_static_test_drift']=drift
 out[label]=d
 print(label,json.dumps(d),flush=True)
json.dump(out,open('final_diagnostics.json','w'),indent=2)
