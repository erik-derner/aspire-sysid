import numpy as np,pandas as pd,json
import fit_final as ff
fits=json.load(open('results/final.json'))
report={}
for label,rr in fits.items():
 r=rr['final'];fam=r.get('fam');t=np.array(r['params']);z=np.array(r['rhs_params']);res={}
 for name in ['train','val']:
  d=pd.read_csv('data/'+name+'.csv');nr=np.load('results/'+label+'_train_val_'+name+'.npz');d['res']=nr['res'];d['dres']=nr['dres'];d['time']=np.arange(len(d))*5
  res[name]={'simulation_mean':float(d.res.iloc[1:].mean()),'simulation_rmse':r[name+'_rmse'],'derivative_rmse':r[name+'_derivative_rmse'],'residual_lag_one_corr':float(d.res.autocorr()),'derivative_residual_lag_one_corr':float(d.dres.autocorr()),'max_abs':float(np.max(np.abs(d.res))), 'binned':{}}
  for col in ['p','valve','flow','time']:
   tb=d.groupby(pd.qcut(d[col],5,duplicates='drop'),observed=True)[['res','dres']].agg(['mean','std'])
   res[name]['binned'][col]=tb.to_string()
 # Stress tests with held inputs. These are diagnostics, not parameter fitting.
 failures=[];worst_err=0.;max_pressure=0.
 for v in [0.,25.,50.,75.,95.,100.]:
  for q in [0.,.1,1.,10.,30.]:
   for p0 in [.98,1.,2.2,5.]:
    d=np.zeros((1500,4));d[0,0]=p0;d[:,1]=v;d[:,2]=q
    pred=ff.tab.sim(z,d) if label=='TabulatedValve' else ff.ext.sim(z,d,fam)
    if np.any(~np.isfinite(pred)) or np.max(np.abs(pred))>=100:failures.append([v,q,p0])
    if q==0 and v<100:
     target=t[3] if label=='TabulatedValve' else t[6]
     worst_err=max(worst_err,abs(pred[-1]-target))
    max_pressure=max(max_pressure,float(pred.max()))
 res['stress']={'cases':600,'failure_cases':failures,'largest_zero_flow_open_equilibrium_error':float(worst_err),'largest_pressure':max_pressure,'length_samples':1500,'sampling_seconds':5}
 report[label]=res
 print(label,'RMSE',r['train_rmse'],r['val_rmse'],'stressfail',len(failures),'eqerr',worst_err,flush=True)
json.dump(report,open('results/diagnostics_final.json','w'),indent=2)
