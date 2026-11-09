import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from scipy.signal import lfilter
T=pd.read_csv('data/train.csv').values;V=pd.read_csv('data/val.csv').values
names=['exp_affine','exp_product_interaction','sigmoid_exp','sigmoid_product','threshold_power_exp','exp_input_product','power_product','softplus_exp']
forms=['b0+exp(c0+c1*a+c2*b)','b0+exp(c0+c1*a+c2*b+c3*a*b)','b0+A/(1+exp(-(a-c)/s))*exp(d*(b-1))','b0+A/((1+exp(-(a-c)/s))*(1+exp(-(b-d)/t)))','b0+A*Max(a-c,0)**n*exp(d*(b-1))','b0+exp(c0+c1*a*b)','b0+A*a**n*b**m','b0+A*log(1+exp((a-c)/s))*exp(d*(b-1))']
params=[['k','b0','c0','c1','c2'],['k','b0','c0','c1','c2','c3'],['k','b0','A','c','s','d'],['k','b0','A','c','s','d','t'],['k','b0','A','c','n','d'],['k','b0','c0','c1'],['k','b0','A','n','m'],['k','b0','A','c','s','d']]
starts=[[.03,1,-5,2,2],[.03,1,-5,2,2,.1],[.03,1,1,1,.3,2],[.03,1,3,1,.3,1,.3],[.03,1,1,.2,2,2],[.03,1,-5,4],[.03,1,.3,3,3],[.03,1,.2,1,.3,2]]
lo=[[.0001,.5,-20,-20,-20],[.0001,.5,-20,-20,-20,-20],[.0001,.5,0,-2,.01,-20],[.0001,.5,0,-2,.01,-2,.01],[.0001,.5,0,-1,.1,-20],[.0001,.5,-20,-20],[.0001,.5,0,.01,.01],[.0001,.5,0,-2,.01,-20]]
hi=[[.35,1.5,10,20,20],[.35,1.5,10,20,20,20],[.35,1.5,20,3,3,20],[.35,1.5,20,3,3,3,3],[.35,1.5,20,1.7,8,20],[.35,1.5,10,20],[.35,1.5,20,12,12],[.35,1.5,20,3,3,20]]
def equilibrium(p,d,j):
 a=d[:,1]/60.;b=d[:,2]/20.
 ex=lambda z:np.exp(np.clip(z,-40,40))
 if j==0:return p[1]+ex(p[2]+p[3]*a+p[4]*b)
 if j==1:return p[1]+ex(p[2]+p[3]*a+p[4]*b+p[5]*a*b)
 if j==2:return p[1]+p[2]/(1+ex(-(a-p[3])/p[4]))*ex(p[5]*(b-1))
 if j==3:return p[1]+p[2]/((1+ex(-(a-p[3])/p[4]))*(1+ex(-(b-p[5])/p[6])))
 if j==4:return p[1]+p[2]*np.maximum(a-p[3],0)**p[4]*ex(p[5]*(b-1))
 if j==5:return p[1]+ex(p[2]+p[3]*a*b)
 if j==6:return p[1]+p[2]*np.maximum(a,1e-6)**p[3]*np.maximum(b,1e-6)**p[4]
 return p[1]+p[2]*np.log(1+ex((a-p[3])/p[4]))*ex(p[5]*(b-1))
def deriv(p,d,j):return p[0]*(equilibrium(p,d,j)-d[:,0])-d[:,3]
def rollout(p,d,j):
 q=equilibrium(p,d[:-1],j);h=-5*p[0];r=1+h+h*h/2+h**3/6+h**4/24
 out,_=lfilter([1-r],[1,-r],q,zi=[r*d[0,0]])
 return out-d[1:,0]
rng=np.random.default_rng(23);results=[]
for j,name in enumerate(names):
 best=None
 for trial in range(4):
  p=np.array(starts[j],float)
  if trial:p=np.clip(p+rng.normal(0,.15,len(p)),np.array(lo[j])+1e-6,np.array(hi[j])-1e-6)
  fit=least_squares(lambda p:deriv(p,T,j),p,bounds=(lo[j],hi[j]),max_nfev=1300,ftol=1e-11,xtol=1e-11,gtol=1e-11)
  if best is None or np.sum(fit.fun**2)<np.sum(best.fun**2):best=fit
 p=best.x
 for stage in ['derivative','rollout']:
  if stage=='rollout':p=least_squares(lambda p:rollout(p,T,j),p,bounds=(lo[j],hi[j]),max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-9).x
  r={'family':name,'stage':stage,'parameters':dict(zip(params[j],p.tolist())),'train_derivative_rmse':float(np.sqrt(np.mean(deriv(p,T,j)**2))),'val_derivative_rmse':float(np.sqrt(np.mean(deriv(p,V,j)**2))),'train_rollout_rmse':float(np.sqrt(np.mean(rollout(p,T,j)**2))),'val_rollout_rmse':float(np.sqrt(np.mean(rollout(p,V,j)**2)))}
  results.append(r);print(json.dumps(r),flush=True)
json.dump(results,open('helper_results.json','w'),indent=2)
with open('helper_report.txt','w') as f:
 f.write('NONLINEAR RELAXATION EXPLORATION\nOnly data/train.csv and data/val.csv were read. No final model JSON written. Physical interpretation is assumed, not supplied: stable first-order relaxation to a nonlinear input equilibrium. Every expression is `dy=k*(q-y)`, where `q` is an equilibrium in unspecified y units and `k` is in s**(-1). Fixed normalizers are `a=x1/60` and `b=x2/20`; divisors carry respective unknown input units and only improve numerical conditioning. All other equilibrium parameters are dimensionless except `b0` and `A`, which carry y units.\n')
 f.write('Fit data: all 1452 train rows for derivative; 1451 post-initial train states for rollout. Validation: all 1454 derivative rows and 1453 post-initial states. Derivative RMSE = sqrt(mean((predicted dy - logged dy)**2)), unspecified y units/s. Rollout RMSE = sqrt(mean((simulated y - logged y)**2)), unspecified y units. Validation was never used for parameter estimation.\n')
 f.write('Method: scipy.optimize.least_squares bounded trust-region reflective nonlinear least squares; four derivative starts per family: listed base start followed by three independent normal perturbations with SD 0.15 in each parameter numerical unit, clipped inside bounds by 1e-6 numerical units; numpy random seed 23. Minimize unweighted derivative SSE, max_nfev=1300, ftol=xtol=gtol=1e-11. Best derivative solution initializes joint train rollout SSE optimization, max_nfev=500, tolerances 1e-9. All parameters estimated jointly at each stage. Bounds encourage positive stable rate and positive excess equilibrium; broad bounds are heuristic, not physically known.\n')
 f.write('Simulation: 5 s sampling, input held constant; exact algebraic implementation of classical RK4 for affine state dynamics using multiplier `r=1+h+h**2/2+h**3/6+h**4/24`, `h=-5*k`. Recurrence `y_next=r*y+(1-r)*q` implemented with scipy.signal.lfilter; initial logged state only, never reset. Exponent arguments clipped to [-40,40] for numerical safety during optimization; this is not intended as part of any submitted equation. Powers clip normalized nonpositive inputs to 1e-6 in the power family.\n')
 for j,name in enumerate(names):
  f.write('\nFamily '+name+'; equilibrium `q='+forms[j]+'`. Parameter order '+str(params[j])+'.\n')
  f.write('Base starts '+str(starts[j])+', lower bounds '+str(lo[j])+', upper bounds '+str(hi[j])+'; units as defined above.\n')
  for r in [r for r in results if r['family']==name]:
   f.write(r['stage']+' fit params: '+', '.join('`'+n+'='+repr(v)+'`'+(' s**(-1)' if n=='k' else ' unspecified y units' if n in ['b0','A'] else '') for n,v in r['parameters'].items())+'\n')
   for key in ['train_derivative_rmse','val_derivative_rmse','train_rollout_rmse','val_rollout_rmse']:f.write(key+' = '+str(r[key])+(' unspecified y units/s' if 'derivative' in key else ' unspecified y units')+'\n')
 best=min(results,key=lambda r:r['val_rollout_rmse']);f.write('\nBest observed validation rollout: '+json.dumps(best)+'\n')
 f.write('Limitations: no supplied physical description, units, or input constraints; equilibrium structures have mathematical plausibility only. Exponential extrapolation may be unsafe; sigmoid saturation and power laws are not identified outside sampled inputs. Derivative and RK4 rollout fits can differ because logged derivative need not correspond to RK4. Methods reference from memory, not externally checked: J. C. Butcher, Numerical Methods for Ordinary Differential Equations, Wiley; first-order relaxation is the standard first-order nonlinear Hammerstein model family.\n')
