import numpy as np,pandas as pd
from scipy.optimize import least_squares
from scipy.special import expit
D={s:pd.read_csv('data/'+s+'.csv') for s in ['train','val']}
d=D['train'];p=d.p.to_numpy();v=d.valve.to_numpy();q=d.flow.to_numpy();y=d.dp.to_numpy(); x=1-v/100
print('dp forward discrepancy',np.max(np.abs(y[:-1]-np.diff(p)/5)))
# a,c,m,k,pa,e pressure laws / valve laws
results=[]
for pl in ['linear','sqrt','compress','power']:
 for vl in ['power','exponential','saturated','logistic']:
  def pred(t,data):
   a,c,m,k,pa,e,n=t; pp=data.p.to_numpy();xx=1-data.valve.to_numpy()/100;z=pp-pa
   if vl=='power':cv=xx**m
   elif vl=='exponential':cv=np.expm1(k*xx)/np.expm1(k)
   elif vl=='saturated':cv=(xx/(xx+k))**m
   else:cv=(expit(k*(xx-m))-expit(-k*m))/(expit(k*(1-m))-expit(-k*m))
   if pl=='linear':h=z
   elif pl=='sqrt':h=z/(z*z+e*e)**.25
   elif pl=='compress':h=z*np.sqrt(np.maximum(pp+pa,.01))/(z*z+e*e)**.25
   else:h=z*(z*z+e*e)**((n-1)/2)
   return a*data.flow.to_numpy()-c*cv*h
  t0=[.001,.1,2,3,1,.02,.6];lo=[.00001,.00001,.05,.01,.97,.002,.2];hi=[.01,10,10,30,1.03,.2,1.5]
  if vl=='saturated':t0[3]=.2;hi[3]=3
  if vl=='logistic':t0[2]=.25;t0[3]=10;hi[2]=1
  r=least_squares(lambda t:pred(t,d)-y,t0,bounds=(lo,hi),max_nfev=500,x_scale='jac',ftol=1e-10)
  tr=np.sqrt(np.mean((pred(r.x,d)-y)**2));va=np.sqrt(np.mean((pred(r.x,D['val'])-D['val'].dp)**2))
  results.append(dict(pl=pl,vl=vl,t=r.x.tolist(),train=tr,val=va));print(pl,vl,tr,va,r.x)
import json
json.dump(results,open('derivative_fits.json','w'),indent=2)
