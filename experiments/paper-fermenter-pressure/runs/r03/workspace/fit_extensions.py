import numpy as np,pandas as pd,math,json,time
from scipy.optimize import least_squares
from fit_rollout import D
BASE=json.load(open('rollout_fits.json'))

def simulate(t,data,family):
 # family series_quad, power_quad, series_calibration, compress_calibration, series_area, series_inletpressure
 a,c,m,k,pa,e,n,b,*g=t
 p=data[0,0];out=np.empty(len(data));out[0]=p
 def rhs(pp,cv,q):
  z=pp-pa
  if family.startswith('power'):h=z*(z*z+e*e)**((n-1)/2)
  elif family.startswith('compress'):h=z*math.sqrt(max(pp+pa,.01))/(z*z+e*e)**.25
  else:h=2*z/(e+math.sqrt(e*e+4*abs(z)))
  infl=a*q*(1+b*q) if family.endswith('quad') else a*q
  if family.endswith('inletpressure'):infl*=max(pp,.1)**b
  if family.endswith('capacity'):return (infl-c*cv*h)/(1+b*q)
  return infl-c*cv*h
 try:
  for i in range(len(data)-1):
   x=max(0.,min(1.,1-data[i,1]/100));q=data[i,2]
   if 'calibration' in family:
    knots=[0,.1,.2,.3,.45,.65,1.];gg=np.cumsum([0]+g).tolist();cv=float(np.interp(x,knots,gg))
   elif family.endswith('area'):
    cv=x**m/(x**m+k**m)
   else:cv=(x/(x+k))**m
   k1=rhs(p,cv,q);k2=rhs(p+2.5*k1,cv,q);k3=rhs(p+2.5*k2,cv,q);k4=rhs(p+5*k3,cv,q);p+=5*(k1+2*k2+2*k3+k4)/6
   if not math.isfinite(p) or abs(p)>20:out[i+1:]=20;return out
   out[i+1]=p
 except (OverflowError,ValueError,ZeroDivisionError):out[i+1:]=20
 return out

def run():
 results=[]
 for fam in ['series_quad','power_quad','series_area','series_inletpressure','series_capacity','series_calibration','compress_calibration']:
  pl='power' if fam.startswith('power') else ('compress' if fam.startswith('compress') else 'series')
  base=next(r for r in BASE if r['pl']==pl and r['vl']=='saturated');t0=base['t']+[0.]
  active=[0,1,2,3,4,5]+([6] if pl=='power' else [])+([7] if fam.endswith(('quad','inletpressure','capacity')) else [])
  lo=[.0001,.0001,.2,.003,.97,.003,.3,0.];hi=[.005,3,15,3,1.02,.6,1.3,.08]
  if fam.endswith('inletpressure'):hi[7]=2
  if fam.endswith('capacity'):lo[7]=-.025;hi[7]=.04
  if 'calibration' in fam:
   a,c,m,k,pa,e,n,b=t0;knots=np.array([0,.1,.2,.3,.45,.65,1.]);cv=(knots/(knots+k))**m;g=np.diff(cv)
   t0+=g.tolist();lo+=[.000001]*6;hi+=[1]*6
   active=[0,4,5]+list(range(8,14)) # absorb c into g, fix c from base
  t0=np.array(t0);lo=np.array(lo);hi=np.array(hi)
  def unpack(x):t=t0.copy();t[active]=x;return t
  ts=time.time();r=least_squares(lambda x:simulate(unpack(x),D['train'],fam)[1:]-D['train'][1:,0],t0[active],bounds=(lo[active],hi[active]),max_nfev=260,x_scale='jac',diff_step=1e-4,ftol=1e-8,xtol=1e-8)
  t=unpack(r.x);metrics={s:float(np.sqrt(np.mean((simulate(t,data,fam)[1:]-data[1:,0])**2))) for s,data in D.items()}
  out=dict(family=fam,t=t.tolist(),start=t0.tolist(),active=active,lo=lo.tolist(),hi=hi.tolist(),metrics=metrics,nfev=r.nfev,message=r.message)
  results.append(out);json.dump(results,open('extension_fits.json','w'),indent=2);print(fam,metrics,'t',t,'nfev',r.nfev,'sec',time.time()-ts,flush=True)
if __name__=='__main__':run()
