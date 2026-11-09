import numpy as np, pandas as pd, json
from scipy.optimize import least_squares
D={n:pd.read_csv('data/'+n+'.csv') for n in ['train','val']}
results={}
for name,d in D.items():
 p=d.p.to_numpy(); dp=d.dp.to_numpy(); fw=np.diff(p)/5
 results[name]={'forward_difference_rmse':float(np.sqrt(np.mean((dp[:-1]-fw)**2))), 'forward_difference_max_abs':float(np.max(np.abs(dp[:-1]-fw))), 'backward_difference_rmse':float(np.sqrt(np.mean((dp[1:]-fw)**2))), 'ranges':{c:[float(d[c].min()),float(d[c].max())] for c in d},'n':len(d)}
knots=np.arange(0,101,10.)
def arrays(d,lag,mid):
 # derivative interval k -> k+1; shifted input observed at k+lag
 k=np.arange(max(0,-lag),min(len(d)-1,len(d)-lag))
 p=d.p.to_numpy(); return p[k]+mid*(p[k+1]-p[k]),d.valve.to_numpy()[k+lag],d.flow.to_numpy()[k+lag],(p[k+1]-p[k])/5,k

def predict(x,p,v,q):
 a=np.exp(x[0]); n=x[1]; c=np.exp(np.interp(v,knots,x[2:])); h=p-1
 return a*q-c*np.sign(h)*np.abs(h)**n
x0=np.r_[np.log(.001),.8,np.linspace(-2,-8,11)]
fits=[]
for mid in [0,.5,1]:
 for lag in [-2,-1,0,1,2]:
  p,v,q,y,k=arrays(D['train'],lag,mid)
  def fun(x): return np.r_[predict(x,p,v,q)-y,1e-5*np.diff(x[2:],2)]
  f=least_squares(fun,x0,bounds=(np.r_[-12,.2,np.full(11,-15)],np.r_[-4,2,np.full(11,2)]),max_nfev=400,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  rec={'lag_samples':lag,'pressure_fraction':mid,'inlet_gain':float(np.exp(f.x[0])),'pressure_exponent':float(f.x[1]),'train_derivative_rmse':float(np.sqrt(np.mean((predict(f.x,p,v,q)-y)**2))),'parameters':f.x.tolist(),'conductance_knots':np.exp(f.x[2:]).tolist()}
  pp,vv,qq,yy,kk=arrays(D['val'],lag,mid)
  rec['val_derivative_rmse']=float(np.sqrt(np.mean((predict(f.x,pp,vv,qq)-yy)**2)))
  fits.append(rec)
  print('alignment',lag,mid,'train',rec['train_derivative_rmse'],'val',rec['val_derivative_rmse'],'a',rec['inlet_gain'],'n',rec['pressure_exponent'],flush=True)
results['alignment_fits']=fits
best=min(fits,key=lambda r:r['train_derivative_rmse']);x=np.array(best['parameters']);results['best']=best
# exponent profile with best alignment
profiles=[]
p,v,q,y,k=arrays(D['train'],best['lag_samples'],best['pressure_fraction'])
for n in [.5,1,1.5,2]:
 def fun(z):
  xx=np.r_[z[0],n,z[1:]]
  return np.r_[predict(xx,p,v,q)-y,1e-5*np.diff(z[1:],2)]
 f=least_squares(fun,np.r_[x[0],x[2:]],bounds=(np.r_[-12,np.full(11,-15)],np.r_[-4,np.full(11,2)]),max_nfev=400,gtol=1e-10,ftol=1e-10,xtol=1e-10)
 xx=np.r_[f.x[0],n,f.x[1:]]
 pp,vv,qq,yy,kk=arrays(D['val'],best['lag_samples'],best['pressure_fraction'])
 profiles.append({'n':n,'inlet_gain':float(np.exp(xx[0])),'train_derivative_rmse':float(np.sqrt(np.mean((predict(xx,p,v,q)-y)**2))),'val_derivative_rmse':float(np.sqrt(np.mean((predict(xx,pp,vv,qq)-yy)**2))),'conductance_knots':np.exp(xx[2:]).tolist()})
results['exponent_profiles']=profiles
# diagnostic bin residual correlations using best unconstrained structure
for name,d in D.items():
 pp,vv,qq,yy,kk=arrays(d,best['lag_samples'],best['pressure_fraction']);res=yy-predict(x,pp,vv,qq)
 tab=pd.DataFrame({'p':pp,'valve':vv,'flow':qq,'residual':res,'time':kk*5.})
 bins={}
 for col in ['p','valve','flow','time']:
  bins[col]=tab.groupby(pd.qcut(tab[col],5,duplicates='drop'),observed=True).agg({col:['min','max'],'residual':['mean','std','count']}).to_string()
 results[name]['residual_bins']=bins
 results[name]['residual_lag1_corr']=float(np.corrcoef(res[:-1],res[1:])[0,1])
 # near equilibrium within low derivative diagnostic
 sub=tab[np.abs(yy)<.00025].copy();sub['q_over_hpow']=sub.flow/np.maximum(sub.p-1,1e-6)**best['pressure_exponent'];sub['valve_bin']=pd.cut(sub.valve,np.arange(0,101,10))
 results[name]['near_equilibrium_bins']=sub.groupby('valve_bin',observed=True).agg({'p':['mean','count'],'flow':'mean','q_over_hpow':'median'}).to_string()
json.dump(results,open('structure_diagnostics.json','w'),indent=2)
print('BEST',best);print('PROFILES',profiles);print('DERIVATIVE CHECK',[(n,results[n]['forward_difference_rmse'],results[n]['backward_difference_rmse']) for n in D])
