import json,numpy as np
from scipy.optimize import least_squares
from fit_rollout import D,rollout
from fit_stable import choked_slopes
P=json.load(open('pooled_fits.json'));S=json.load(open('stable_fits.json'))
def run():
 results=[]
 for fam in ['linear','series','power','choked']:
  if fam in ['series','choked']:base=next(r for r in S if r['name']==fam);start=np.array(base['fit_t'])
  else:base=next(r for r in P if r['name']==fam);start=np.array(base['t'])
  start[4]=1.;active=[0,1,2,3]+([] if fam=='linear' else [5])+([6] if fam=='power' else [])
  lo=np.array([.0001,.0001,.2,.003,1,.01,.3]);hi=np.array([.005,3,15,3,1,.6,1.])
  if fam=='series':hi[5]=.5
  if fam=='choked':lo[5]=.015;hi[5]=.4
  def physical(t):
   tt=t.copy()
   if fam=='series':tt[5]=t[1]*(1/(1+t[3]))**t[2]/t[5]
   return tt
  def sim(t,d):return rollout(physical(t),d,fam,'saturated')
  def fit(st,data):
   def unpack(x):t=st.copy();t[active]=x;return t
   def residual(x):
    t=unpack(x);res=np.concatenate([sim(t,d)[1:]-d[1:,0] for d in data])
    if fam=='choked':res=np.r_[res,100*np.maximum(choked_slopes(t)-.48,0)]
    elif fam=='power':res=np.r_[res,100*max(t[1]*(1/(1+t[3]))**t[2]*t[5]**(t[6]-1)-.5,0)]
    return res
   r=least_squares(residual,st[active],bounds=(lo[active],hi[active]),max_nfev=240,x_scale='jac',ftol=1e-9,xtol=1e-9)
   return unpack(r.x),r
  pre,rpre=fit(start,[d[:1000] for d in D.values()]);suffix={s:float(np.sqrt(np.mean((sim(pre,d[1000:])[1:]-d[1001:,0])**2))) for s,d in D.items()}
  full,rfull=fit(pre,list(D.values()));metrics={s:float(np.sqrt(np.mean((sim(full,d)[1:]-d[1:,0])**2))) for s,d in D.items()}
  rec=dict(name=fam,fit_t=full.tolist(),t=physical(full).tolist(),start=start.tolist(),prefix_t=pre.tolist(),active=active,lo=lo.tolist(),hi=hi.tolist(),prefix_nfev=rpre.nfev,full_nfev=rfull.nfev,suffix_metrics=suffix,full_metrics=metrics)
  results.append(rec);json.dump(results,open('atmospheric_fits.json','w'),indent=2);print(rec,flush=True)
if __name__=='__main__':run()
