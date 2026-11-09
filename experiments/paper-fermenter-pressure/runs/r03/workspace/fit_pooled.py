import numpy as np,json,time
from scipy.optimize import least_squares
from fit_rollout import D,rollout
from fit_extensions import simulate
B=json.load(open('rollout_fits.json'));E=json.load(open('extension_fits.json'))
def run():
 records=[]
 jobs=[]
 for r in B:
  if r['vl']=='saturated' and r['pl'] in ['linear','sqrt','compress','power','series','choked']:jobs.append(('base',r['pl'],r))
 for fam in ['series_quad','series_capacity','series_calibration','series_area']:
  jobs.append(('extension',fam,next(r for r in E if r['family']==fam)))
 for kind,name,base in jobs:
  t0=np.array(base['t']);active=base['active'];lo=np.array(base['lo']);hi=np.array(base['hi'])
  if name=='series_quad':t0[7]=.004
  simulator=(lambda t,d:rollout(t,d,name,'saturated')) if kind=='base' else (lambda t,d:simulate(t,d,name))
  # two independent prefixes for fitting; two independent suffixes for validation
  def opt(start,data):
   def unpack(x):t=start.copy();t[active]=x;return t
   r=least_squares(lambda x:np.concatenate([simulator(unpack(x),dd)[1:]-dd[1:,0] for dd in data]),start[active],bounds=(lo[active],hi[active]),max_nfev=180,x_scale='jac',ftol=1e-8,xtol=1e-8)
   return unpack(r.x),r
  tprefix,rpre=opt(t0,[d[:1000] for d in D.values()])
  suffix={s:float(np.sqrt(np.mean((simulator(tprefix,d[1000:])[1:]-d[1001:,0])**2))) for s,d in D.items()}
  tfull,r=opt(tprefix,list(D.values()));metrics={s:float(np.sqrt(np.mean((simulator(tfull,d)[1:]-d[1:,0])**2))) for s,d in D.items()}
  rec=dict(kind=kind,name=name,t=tfull.tolist(),start=t0.tolist(),prefix_t=tprefix.tolist(),prefix_nfev=rpre.nfev,full_nfev=r.nfev,active=active,lo=lo.tolist(),hi=hi.tolist(),suffix_metrics=suffix,full_metrics=metrics)
  records.append(rec);json.dump(records,open('pooled_fits.json','w'),indent=2);print(kind,name,'suffix',suffix,'full',metrics,'t',tfull,flush=True)
if __name__=='__main__':run()
