import json,numpy as np,pandas as pd
from scipy.optimize import least_squares
from numba import njit
import explore as e
R=json.load(open('explore_results.json'));out={}
@njit
def step_errors(d,t,kind,drive):
 z=np.empty(len(d)-1)
 for i in range(len(z)):
  p,v,f=d[i,:3];k1=e.rhs(p,v,f,t,kind,drive);k2=e.rhs(p+2.5*k1,v,f,t,kind,drive);k3=e.rhs(p+2.5*k2,v,f,t,kind,drive);k4=e.rhs(p+5*k3,v,f,t,kind,drive)
  z[i]=(p+5*(k1+2*k2+2*k3+k4)/6-d[i+1,0])/5
 return z
best=min(R,key=lambda r:r['rmse']['val']);out['best']=best
out['family_table']=[{'kind':r['kind'],'drive':r['drive'],'rmse':r['rmse'],'params':r['params']} for r in R]
for s,d in e.D.items():
 changes={c:np.where(np.abs(np.diff(d[:,j]))>.01)[0]+1 for c,j in [('valve',1),('flow',2)]}
 stats={'range':{c:[float(d[:,j].min()),float(d[:,j].max())] for j,c in enumerate(['p','valve','flow','dp'])},'input_change_count':{c:len(k) for c,k in changes.items()},'input_levels':{c:np.unique(np.round(d[:,j],3)).tolist() for c,j in [('valve',1),('flow',2)]}}
 stats['dp_vs_difference']=[]
 for shift in range(-4,5):
  idx=np.arange(5,len(d)-6);fd=(d[idx+shift+1,0]-d[idx+shift,0])/5
  stats['dp_vs_difference'].append({'shift':shift,'rmse':float(np.sqrt(np.mean((d[idx,3]-fd)**2))),'corr':float(np.corrcoef(d[idx,3],fd)[0,1])})
 t=np.array(best['params']);pred=e.simulate(d,t,best['kind'],best['drive']);res=pred-d[:,0];one=step_errors(d,t,best['kind'],best['drive']);der=e.dr(d,t,best['kind'],best['drive'])
 stats['residual']={'bias':float(res[1:].mean()),'one_step_rmse_bar_s':float(np.sqrt(np.mean(one**2))),'derivative_rmse_bar_s':float(np.sqrt(np.mean(der**2))),'lag1_sim_corr':float(np.corrcoef(res[1:-1],res[2:])[0,1])}
 stats['bins']={}
 for c,j,edges in [('p',0,[.9,1.05,1.1,1.2,1.4,1.7,2.1,3]),('valve',1,[0,20,40,60,70,80,90,100.1]),('flow',2,[0,5,10,15,20,25,30,40,100])]:
  z=[]
  for a,b in zip(edges[:-1],edges[1:]):
   mask=(d[:-1,j]>=a)&(d[:-1,j]<b)
   if mask.sum():z.append({'range':[a,b],'count':int(mask.sum()),'sim_bias_bar':float(res[:-1][mask].mean()),'one_bias_bar_s':float(one[mask].mean()),'one_rmse_bar_s':float(np.sqrt(np.mean(one[mask]**2)))})
  stats['bins'][c]=z
 stats['events']={}
 for c,inds in changes.items():
  inds=inds[(inds>5)&(inds<len(d)-8)]
  other=changes['flow' if c=='valve' else 'valve'];inds=np.array([k for k in inds if np.all(np.abs(other-k)>5)],dtype=int)
  stats['events'][c]={'isolated_count':len(inds),'mean_signed_step_error':[]}
  j=1 if c=='valve' else 2
  for lag in range(-3,7):
   errs=one[inds+lag]*np.sign(d[inds,j]-d[inds-1,j]) if len(inds) else []
   stats['events'][c]['mean_signed_step_error'].append([lag,float(np.mean(errs)) if len(errs) else None])
 out[s]=stats
# Fit local integrated residual to avoid filtered dp. Input shift +1 uses next logged input.
kind,drive=2,2;t0=np.array(next(r for r in R if r['kind']==kind and r['drive']==drive)['params']);_,lo,hi,active=e.setup(kind,drive)
def shifted(d,vs,fs):
 q=d.copy();idx=np.arange(len(d));q[:,1]=d[np.clip(idx+vs,0,len(d)-1),1];q[:,2]=d[np.clip(idx+fs,0,len(d)-1),2];return q
out['timing_grid']=[]
for vs in range(-2,3):
 for fs in range(-3,4):
  ds={s:shifted(d,vs,fs) for s,d in e.D.items()}
  def obj(x):
   t=t0.copy();t[active]=x;return step_errors(ds['train'],t,kind,drive)[5:-5]
  fit=least_squares(obj,t0[active],bounds=(lo[active],hi[active]),max_nfev=90,x_scale='jac')
  t=t0.copy();t[active]=fit.x
  metrics={s:float(np.sqrt(np.mean(step_errors(d,t,kind,drive)[5:-5]**2))) for s,d in ds.items()}
  sims={s:float(np.sqrt(np.mean((e.simulate(d,t,kind,drive)[1:]-d[1:,0])**2))) for s,d in ds.items()}
  out['timing_grid'].append({'valve_shift':vs,'flow_shift':fs,'local_rmse_bar_s':metrics,'sim_rmse_bar':sims,'params':t.tolist()})
  print('timing',vs,fs,metrics,flush=True)
json.dump(out,open('helper_diagnostics.json','w'),indent=2)
print('BEST',best['kind'],best['drive'],best['rmse'])
for s in e.D:print(s,out[s]['range'],out[s]['input_change_count'],out[s]['residual'],out[s]['events'])
print('TIMING BEST',sorted(out['timing_grid'],key=lambda x:x['local_rmse_bar_s']['train'])[:5])
