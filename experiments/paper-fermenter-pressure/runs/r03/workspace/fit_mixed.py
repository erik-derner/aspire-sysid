import numpy as np,math,json
from scipy.optimize import least_squares
from fit_rollout import D

def simulate(t,data,gas=False):
 a,c,m,k,pa,elin,eclosed=t;p=data[0,0];out=np.empty(len(data));out[0]=p
 def f(pp,xx,q):
  z=pp-pa
  if gas:z=(pp-pa)*max(pp+pa,.01)
  r=elin*xx+eclosed;s=xx*xx+k**(2*m)
  return a*q-c*2*xx*z/(r+math.sqrt(r*r+4*s*abs(z)))
 try:
  for i in range(len(data)-1):
   xx=max(0,min(1,1-data[i,1]/100))**m;q=data[i,2]
   k1=f(p,xx,q);k2=f(p+2.5*k1,xx,q);k3=f(p+2.5*k2,xx,q);k4=f(p+5*k3,xx,q);p+=5*(k1+2*k2+2*k3+k4)/6
   if abs(p)>20 or not math.isfinite(p):out[i+1:]=20;return out
   out[i+1]=p
 except (ValueError,OverflowError,ZeroDivisionError):out[i+1:]=20
 return out

def run():
 records=[]
 for gas in [False,True]:
  starts=[[.00125,.13,1.4,.5,.992,.1,.015],[.0012,.12,1.5,.4,.992,.02,.03]]
  lo=[.0001,.001,.3,.01,.97,.0001,.0001];hi=[.005,1,5,2,1.02,3,3]
  def fit(t0,data):
   return least_squares(lambda t:np.concatenate([simulate(t,d,gas)[1:]-d[1:,0] for d in data]),t0,bounds=(lo,hi),max_nfev=240,x_scale='jac',ftol=1e-9,xtol=1e-9)
  prefix_fits=[fit(st,[d[:1000] for d in D.values()]) for st in starts];pre=min(prefix_fits,key=lambda r:r.cost)
  suffix={s:float(np.sqrt(np.mean((simulate(pre.x,d[1000:],gas)[1:]-d[1001:,0])**2))) for s,d in D.items()}
  full=fit(pre.x,list(D.values()));metrics={s:float(np.sqrt(np.mean((simulate(full.x,d,gas)[1:]-d[1:,0])**2))) for s,d in D.items()}
  rec=dict(name='mixed_gas' if gas else 'mixed_resistance',gas=gas,t=full.x.tolist(),starts=starts,lo=lo,hi=hi,prefix_t=pre.x.tolist(),prefix_costs=[r.cost for r in prefix_fits],suffix_metrics=suffix,full_metrics=metrics,full_nfev=full.nfev)
  records.append(rec);json.dump(records,open('mixed_fits.json','w'),indent=2);print(rec,flush=True)
if __name__=='__main__':run()
