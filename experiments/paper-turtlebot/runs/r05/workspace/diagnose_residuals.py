import numpy as np,pandas as pd,json
import fit_explore as F
R=json.load(open('explore_results.json'))
records={}
for fam,kind in [('linear','x'),('wheel','xy'),('deadzone','joint'),('body','x'),('asymmetric','x')]:
 p=np.array(R[fam][kind]['parameters']); pack=F.windows([0,1,2],25,1)
 err=F.simulate(p,pack,fam)-pack[2]
 horizon_rmse=np.sqrt(np.mean(err*err,axis=0))
 step=[]; af=[]; av=[]; blockphase=[]
 for a in F.TRAJ:
  uu=a[:-1,3:]; vv,ww,_,_=F.response(p,uu,fam)
  delta=np.diff(a[:,:3],axis=0); mid=(a[:-1,2]+a[1:,2])/2
  forward=(delta[:,0]*np.cos(mid)+delta[:,1]*np.sin(mid))/.2
  lateral=(-delta[:,0]*np.sin(mid)+delta[:,1]*np.cos(mid))/.2
  step.append(np.column_stack([forward-vv,delta[:,2]/.2-ww,lateral])); af.extend(uu[:,0]); av.extend(uu[:,1]); blockphase.extend(np.arange(len(uu))%5)
 residual=np.concatenate(step); blockphase=np.array(blockphase)
 rec={'all_phase_window_rmse':np.sqrt(np.mean(err*err,axis=(0,1))).tolist(),'horizon_rmse':horizon_rmse.tolist(),'one_step_speed_residual_rmse':np.sqrt(np.mean(residual*residual,axis=0)).tolist(),'phase_speed_mean':{str(i):np.mean(residual[blockphase==i],axis=0).tolist() for i in range(5)},'phase_speed_rms':{str(i):np.sqrt(np.mean(residual[blockphase==i]**2,axis=0)).tolist() for i in range(5)},'speed_residual_corr_forward_command':np.corrcoef(residual[:,0],af)[0,1],'angular_residual_corr_angular_command':np.corrcoef(residual[:,1],av)[0,1]}
 lag=[]
 for st in step:
  lag.append([np.corrcoef(st[:-1,j],st[1:,j])[0,1] for j in range(2)])
 rec['lag1_speed_residual_correlations_by_trajectory']=lag
 records[fam]=rec
 print(fam,kind,'all phase RMSE',np.round(rec['all_phase_window_rmse'],6),'one-step residual speed RMS',np.round(rec['one_step_speed_residual_rmse'],6),'lag1',np.round(lag,3),flush=True)
 print('phase residual RMS',rec['phase_speed_rms'],flush=True)
json.dump(records,open('residual_report.json','w'),indent=2)
