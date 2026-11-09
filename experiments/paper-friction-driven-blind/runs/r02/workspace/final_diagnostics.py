import json,numpy as np
exec(open('refit_final.py').read().split('R=json.load')[0])
rr=json.load(open('final_results.json'));rr['harmonic']=json.load(open('refined_harmonic_results.json'))
out={}
for form in ['harmonic','projection','polynomial']:
 p=rr[form]['p'];out[form]={}
 for tag,D,d in [('train',TR,train),('val',VA,val)]:
  py,pv=rollout(p,form,D,True);Y,V,U,M,ids=D;e=(py-Y)[M]
  r=d.dx1.values-force(d.y.values,d.x1.values,d.x2.values,p,form);lag=[]
  for _,g in d.groupby('trajectory'):lag.extend(zip(r[g.index][:-1],r[g.index][1:]))
  out[form][tag]={'y_rmse':float(np.sqrt(np.mean(e*e))),'y_bias':float(np.mean(e)),'dx1_rmse':float(np.sqrt(np.mean(r*r))),'residual_lag1':float(np.corrcoef(np.array(lag).T)[0,1]),'residual_moving_rmse':float(np.sqrt(np.mean(r[np.abs(d.x1.values)>.5]**2))),'residual_stopped_rmse':float(np.sqrt(np.mean(r[d.x1.values==0]**2))),'max_simulated_abs_y':float(np.max(np.abs(py[M]))),'max_simulated_abs_x1':float(np.max(np.abs(pv[M]))),'y_rmse_per_trajectory':metrics(p,form,D)['bytraj']}
 print(form,out[form])
json.dump(out,open('final_diagnostics.json','w'),indent=2)
