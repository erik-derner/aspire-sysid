import json,numpy as np,math
from scipy.optimize import least_squares
from fit_rollout import D,rollout
from fit_mixed import simulate
B=json.load(open('pooled_fits.json'));M=json.load(open('final_mixed_fit.json'))

def choked_slopes(t):
 a,c,m,k,pa,e,n=t;cv=(1/(1+k))**m
 zz=np.r_[np.linspace(-.2,-1e-4,120),np.geomspace(.0001,1.5,180)]
 def h(p):
  z=p-pa;pu=np.maximum(p,pa);pd=np.maximum(np.minimum(p,pa),.01);rr=np.maximum(pd/pu,(2/2.4)**3.5);ss=np.maximum(rr**(2/1.4)-rr**(2.4/1.4),0)
  return pu*np.sqrt(7*ss)*z/np.sqrt(z*z+e*e)
 return c*cv*(h(pa+zz+1e-5)-h(pa+zz-1e-5))/2e-5

def run():
 records=[]
 for fam in ['series','mixed','choked']:
  if fam=='mixed':base=M;start=np.array(base['t']);start[5]=0.;start[6]=.45;active=[0,1,2,3,4,6]
  else:base=next(r for r in B if r['name']==fam);start=np.array(base['t']);active=[0,1,2,3,4,5];start[5]=.45 if fam=='series' else .05
  lo=np.array([.0001,.0001,.2,.003,.97,.01,.01]);hi=np.array([.005,3,15,3,1.02,.5,.5])
  if fam=='choked':lo[5]=.015;hi[5]=.4
  def physical(t):
   tt=t.copy()
   if fam=='series':tt[5]=t[1]*(1/(1+t[3]))**t[2]/t[5]
   elif fam=='mixed':tt[6]=t[1]/t[6]
   return tt
  def sim(t,d):return simulate(physical(t),d) if fam=='mixed' else rollout(physical(t),d,fam,'saturated')
  def fit(st,data):
   def unpack(x):t=st.copy();t[active]=x;return t
   def residual(x):
    t=unpack(x);res=np.concatenate([sim(t,d)[1:]-d[1:,0] for d in data])
    if fam=='choked':res=np.r_[res,100*np.maximum(choked_slopes(t)-.48,0)]
    return res
   r=least_squares(residual,st[active],bounds=(lo[active],hi[active]),max_nfev=220,x_scale='jac',ftol=1e-9,xtol=1e-9)
   return unpack(r.x),r
  pre,rpre=fit(start,[d[:1000] for d in D.values()]);suffix={s:float(np.sqrt(np.mean((sim(pre,d[1000:])[1:]-d[1001:,0])**2))) for s,d in D.items()}
  full,rfull=fit(pre,list(D.values()));metrics={s:float(np.sqrt(np.mean((sim(full,d)[1:]-d[1:,0])**2))) for s,d in D.items()}
  rec=dict(name=fam,fit_t=full.tolist(),t=physical(full).tolist(),start=start.tolist(),prefix_t=pre.tolist(),active=active,lo=lo.tolist(),hi=hi.tolist(),prefix_nfev=rpre.nfev,full_nfev=rfull.nfev,suffix_metrics=suffix,full_metrics=metrics)
  if fam=='choked':rec['max_slope']=float(max(choked_slopes(full)))
  records.append(rec);json.dump(records,open('stable_fits.json','w'),indent=2);print(rec,flush=True)
if __name__=='__main__':run()
