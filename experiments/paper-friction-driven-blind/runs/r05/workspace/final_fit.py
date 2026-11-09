import fit_models as f,extend_fit as ex,fit_polynomial as pol
from scipy.optimize import least_squares
import numpy as np,json,os
# Reproduce the final joint refits from the saved training-only warm starts.
# Initial structure selection precedes this script and is recorded in results/*.json.
original=f.D.copy();f.D['all']=tuple(np.pad(original['train'][i],((0,max(len(original['train'][0]),len(original['val'][0]))-len(original['train'][0])),(0,0))) for i in range(4))
f.D['all']=tuple(np.concatenate([f.D['all'][i],np.pad(original['val'][i],((0,len(f.D['all'][0])-len(original['val'][0])),(0,0)))],axis=1) for i in range(4))
configs=[('TrigSmooth','sin_atan_cos_fsin_fcos',ex.accel),('ForceClamp','sin_clamp_cos_fsin_fcos',ex.accel),('Polynomial','polynomial',pol.accel)]
if __name__=='__main__':
 for label,fam,fun in configs:
  f.accel=fun;warm=json.load(open('results/'+fam+'.json'));p=np.array(warm['p']);lo,hi=np.array(warm['bounds']);
  r=least_squares(lambda p:f.simulate(p,fam,'all'),p,bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=180,ftol=1e-7,xtol=1e-7,gtol=1e-6)
  z={'label':label,'family':fam,'p':r.x.tolist(),'start':p.tolist(),'bounds':[lo.tolist(),hi.tolist()],'nfev':r.nfev,'status':r.message,'pre_refit_train_rmse':warm['train_rmse'],'pre_refit_val_rmse':warm['val_rmse']}
  for s in ['train','val','all']:
   z[s+'_rmse']=float(np.sqrt(np.mean(f.simulate(r.x,fam,s)**2)))
   Y,V,U,M=f.D[s];ys,vs=f.simulate(r.x,fam,s,True)
   z[s+'_per_traj']=[float(np.sqrt(np.mean((ys[:,j]-Y[:,j])[M[:,j]]**2))) for j in range(Y.shape[1])]
  print(json.dumps(z),flush=True);json.dump(z,open('results/final_'+label+'.json','w'),indent=2)
