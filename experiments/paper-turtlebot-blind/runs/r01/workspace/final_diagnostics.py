import json,numpy as np
import fit_regularized as K
import fit_fourier as F
from fit_kinematic import trajs,wrap
R=json.load(open('regularized_results.json'));Q=json.load(open('fourier_results.json'))
allres={}
for label,key,mod in [('RigidDeadzone','deadzone_mid_100',K),('RigidPower','power_mid_100',K),('FourierMap','100',F)]:
 r=R[key] if mod==K else Q[key];p=np.array(r['parameters']);pred=[];one=[]
 for a in trajs:
  if mod==K:b=K.simulate(p,a,r['family']);q=np.vstack([K.simulate(p,a[i:i+2],r['family'])[1] for i in range(len(a)-1)])
  else:b=F.sim(p,a);q=np.vstack([F.sim(p,a[i:i+2])[1] for i in range(len(a)-1)])
  pred.append(b);e=q-a[1:,:3];e[:,2]=wrap(e[:,2]);one.append(e)
 e=np.concatenate(one);phase=np.tile(np.arange(149)%5,3);stats={'one_step_rmse':np.sqrt(np.mean(e**2,axis=0)).tolist(),'phase0_one_step_rmse':np.sqrt(np.mean(e[phase==0]**2,axis=0)).tolist(),'interior_one_step_rmse':np.sqrt(np.mean(e[phase>=2]**2,axis=0)).tolist(),'lag1_one_step_correlation':[float(np.corrcoef(np.concatenate([z[:-1,j] for z in one]),np.concatenate([z[1:,j] for z in one]))[0,1]) for j in range(3)]}
 if mod==K:q,_=K.fit([a[:100] for a in trajs],r['family'],100);pp=[K.simulate(q,a,r['family']) for a in trajs]
 else:q,_=F.fit([a[:100] for a in trajs],100);pp=[F.sim(q,a) for a in trajs]
 e=np.concatenate([(b-a[:,:3])[100:] for a,b in zip(trajs,pp)]);e[:,2]=wrap(e[:,2]);stats['tail50_rmse']=np.sqrt(np.mean(e**2,axis=0)).tolist()
 stats['train_rmse']=r['train_rmse'];stats['loo_rmse']=r['loo_rmse'];stats['aggregate_loo_y_rmse']=float(np.sqrt(np.mean(np.array(r['loo_rmse'])[:,0]**2)))
 print(label,stats);allres[label]=stats
json.dump(allres,open('final_diagnostics.json','w'),indent=2)
