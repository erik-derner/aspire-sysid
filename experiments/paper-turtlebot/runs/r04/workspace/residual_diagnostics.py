import theta_models as tm,fit_models as fm
import numpy as np,json
R=json.load(open('theta_results.json'));p=np.array(R['rectified_euler']['parameters']);fam='rectified_euler'
report={}
for H in [1,5,25]:
 data=fm.make_windows([0,1,2],H);r=fm.rollout(p,fam,data)-data[1]
 report['horizon_'+str(H)]={'rmse':np.sqrt(np.mean(r*r,axis=(0,1))).tolist(),'mean':np.mean(r,axis=(0,1)).tolist(),'endpoint_rmse':np.sqrt(np.mean(r[:,-1]**2,axis=0)).tolist()}
r=[];a=[];v=[];phase=[];corr=[]
for z,u in fm.G:
 d=(z[:-1],z[1:,None,:],u[:-1,None,:]);e=fm.rollout(p,fam,d)[:,0]-z[1:]
 r.extend(e);a.extend(u[:-1,1]);v.extend(u[:-1,0]);phase.extend(np.arange(len(z)-1)%5)
 corr.append([np.corrcoef(e[:-1,j],e[1:,j])[0,1] for j in range(3)])
r=np.array(r);a=np.array(a);v=np.array(v);phase=np.array(phase)
report['one_step_phase_means']={str(i):np.mean(r[phase==i],axis=0).tolist() for i in range(5)}
report['one_step_phase_rmse']={str(i):np.sqrt(np.mean(r[phase==i]**2,axis=0)).tolist() for i in range(5)}
report['one_step_lag_one_correlation_by_trajectory']=corr
report['residual_command_correlation']={'vf':[float(np.corrcoef(r[:,j],v)[0,1]) for j in range(3)],'va':[float(np.corrcoef(r[:,j],a)[0,1]) for j in range(3)]}
print(json.dumps(report,indent=2));json.dump(report,open('residual_report.json','w'),indent=2)
