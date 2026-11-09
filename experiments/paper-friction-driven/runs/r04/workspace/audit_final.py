import json,numpy as np,pandas as pd
from fit_models import accel,pack,simulate
from crossvalidate import combined
D=combined();D['row']=D.groupby('trajectory').cumcount();R=json.load(open('final_results.json'));report={}
for name in ['angle_asym','angle_smooth','equal_blend','speed_weakening']:
 r=R[name]['selected'];p=np.array(r['p']);fam=r['family'];dat=pack(D);out=simulate(p,fam,*dat[:3]);dp=np.array([accel(t,w,u,p,fam) for t,w,u in D[['theta','omega','u']].to_numpy()]);rr=D.domega.to_numpy()-dp;moving=(abs(D.omega)>.8)&(D.row>=5)
 report[name]={'derivative_rmse_moving':float(np.sqrt(np.mean(rr[moving]**2))),'derivative_mean_moving':float(np.mean(rr[moving])),'angle_endpoint_errors':[float(out[j,n-1]-dat[3][j,n-1]) for j,n in enumerate(dat[2])]}
# Local sampled checks are supplementary, not proofs.
rng=np.random.default_rng(314159);t=rng.uniform(-np.pi,np.pi,30000);w=rng.uniform(-23,23,30000);u=rng.uniform(-10,10,30000)
for name in report:
 r=R[name]['selected'];p=np.array(r['p']);fam=r['family'];z=np.array([accel(a,0.,0.,p,fam)*a for a in np.r_[t,-np.pi,np.pi,0.]])
 low=np.array([accel(a,b,c,p,fam) for a,b,c in zip(t,w,u)]);high=np.array([accel(a,b,c+1e-5,p,fam) for a,b,c in zip(t,w,u)])
 report[name]['max_R2_product']=float(z.max());report[name]['min_input_increment']=float((high-low).min());report[name]['all_finite']=bool(np.isfinite(low).all())
json.dump(report,open('final_audit.json','w'),indent=2);print(json.dumps(report,indent=2))
