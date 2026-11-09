import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
import explore as e
H=json.load(open('helper_diagnostics.json'));R=json.load(open('explore_results.json'))
out={}
for s,d in e.D.items():
 fd=np.diff(d[:,0])/5;dp=d[:,3]
 out[s]={'diff_tests':{},'jump_counts':{}}
 for name,y,target in [('backward',fd,dp[1:]),('forward',fd,dp[:-1]),('central',(d[2:,0]-d[:-2,0])/10,dp[1:-1])]:out[s]['diff_tests'][name]={'rmse':float(np.sqrt(np.mean((target-y)**2))),'corr':float(np.corrcoef(target,y)[0,1])}
 for j,c,thr in [(1,'valve',3),(2,'flow',2)]:
  jumps=np.where(np.abs(np.diff(d[:,j]))>thr)[0]+1;otherj=3-j;oththr=2 if j==1 else 3;other=np.where(np.abs(np.diff(d[:,otherj]))>oththr)[0]+1
  isolated=np.array([k for k in jumps if k>5 and k<len(d)-8 and np.all(np.abs(other-k)>3)],dtype=int)
  t=np.array(H['best']['params']);from helper_diagnostics import step_errors
  err=step_errors(d,t,H['best']['kind'],H['best']['drive'])
  out[s]['jump_counts'][c]={'threshold':thr,'total':len(jumps),'isolated':len(isolated),'signed_one_step_residual_bar_s':[[lag,float(np.mean(err[isolated+lag]*np.sign(d[isolated,j]-d[isolated-1,j])))] for lag in range(-3,5)] if len(isolated) else []}
print(out,flush=True)
@njit
def rhs(p,v,f,t,kind,drive):
 a,c,atm,eps,b=t;x=max(0.,1-v/100.);z=p-atm
 if kind==0:C=c*(x/.3)**b
 elif kind==1:C=c*(x/(b+x))/(.3/(b+.3))
 elif kind==2:C=c*np.tanh(x/b)/np.tanh(.3/b)
 else:C=c*(1-np.exp(-x/b))/(1-np.exp(-.3/b))
 if drive==0:h=z/np.sqrt(eps+abs(z))
 elif drive==1:h=2*z/(np.sqrt(eps)+np.sqrt(eps+4*abs(z)))
 elif drive==2:h=z
 else:h=z/(z*z+eps*eps)**.25
 return a*f-C*h
@njit
def sim(d,t,kind,drive):
 y=np.empty(len(d));y[0]=d[0,0]
 for k in range(len(d)-1):
  p=y[k];v=d[k,1];f=d[k,2];k1=rhs(p,v,f,t,kind,drive);k2=rhs(p+2.5*k1,v,f,t,kind,drive);k3=rhs(p+2.5*k2,v,f,t,kind,drive);k4=rhs(p+5*k3,v,f,t,kind,drive);y[k+1]=p+5*(k1+2*k2+2*k3+k4)/6
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:y[k+1:]=100;break
 return y
out['alternatives']=[]
for kind in [0,1,2,3]:
 for drive in [0,1,2,3]:
  start=np.array([.00125,.05,.99,.02,1 if kind==0 else .2]);lo=[.0002,.001,.97,.00001,.03];hi=[.003,.3,1.02,2,8 if kind==0 else 3]
  fit=least_squares(lambda t:sim(e.D['train'],t,kind,drive)[1:]-e.D['train'][1:,0],start,bounds=(lo,hi),x_scale='jac',max_nfev=120)
  t=fit.x;metrics={s:float(np.sqrt(np.mean((sim(d,t,kind,drive)[1:]-d[1:,0])**2))) for s,d in e.D.items()};out['alternatives'].append({'kind':kind,'drive':drive,'params':t.tolist(),'rmse_bar':metrics});print(kind,drive,metrics,t,flush=True)
json.dump(out,open('helper_more.json','w'),indent=2)
