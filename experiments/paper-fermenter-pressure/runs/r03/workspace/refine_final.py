import json,numpy as np
from scipy.optimize import least_squares
from fit_rollout import D
from fit_mixed import simulate
r=json.load(open('mixed_fits.json'))[0];lo=np.array(r['lo']);hi=np.array(r['hi']);t0=np.array(r['prefix_t']);t0[5]=0.;active=[0,1,2,3,4,6]
def fit(start,data):
 def unpack(x):t=start.copy();t[active]=x;return t
 result=least_squares(lambda x:np.concatenate([simulate(unpack(x),d)[1:]-d[1:,0] for d in data]),start[active],bounds=(lo[active],hi[active]),max_nfev=240,x_scale='jac',ftol=1e-9,xtol=1e-9)
 return unpack(result.x),result
pre,rpre=fit(t0,[d[:1000] for d in D.values()]);full,rfull=fit(pre,list(D.values()))
suffix={s:float(np.sqrt(np.mean((simulate(pre,d[1000:])[1:]-d[1001:,0])**2))) for s,d in D.items()};metrics={s:float(np.sqrt(np.mean((simulate(full,d)[1:]-d[1:,0])**2))) for s,d in D.items()}
out=dict(t=full.tolist(),prefix_t=pre.tolist(),start=t0.tolist(),active=active,lo=lo.tolist(),hi=hi.tolist(),suffix_metrics=suffix,full_metrics=metrics,prefix_nfev=rpre.nfev,full_nfev=rfull.nfev)
json.dump(out,open('final_mixed_fit.json','w'),indent=2);print(out)
