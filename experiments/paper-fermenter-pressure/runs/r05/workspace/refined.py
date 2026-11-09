import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
from pathlib import Path
from identify import train,val
@njit
def rhs(p,v,q,t,kind):
 a,b,m,s,p0,n,d=t[:7]
 op=max(0.,min(1.,1-v/100.)); z=op**m; c=b*z/(1+s*z); x=(p-p0)/p0
 if kind in (0,3,4): h=x/(x*x+d*d)**((1-n)/2)
 elif kind==1: h=2*x/(d+np.sqrt(d*d+4*abs(x)))
 elif kind==2:
  high=max(p,p0)/p0; low=min(max(p,.01),p0)/p0; r=max(low/high,(2/2.4)**3.5)
  h=np.sign(x)*high*np.sqrt(max(r**(2/1.4)-r**(2.4/1.4),0))*abs(x)/np.sqrt(x*x+d*d)
 elif kind==5: h=x
 if kind==3: return a*q*(1+t[7]*q)-c*h
 elif kind==4: return a*q/(1+t[7]*q)-c*h
 return a*q-c*h
@njit
def sim(arr,t,kind):
 N=len(arr); out=np.empty(N);out[0]=arr[0,0]
 for i in range(N-1):
  p=out[i];v,q=arr[i,1:3];k1=rhs(p,v,q,t,kind);k2=rhs(p+2.5*k1,v,q,t,kind);k3=rhs(p+2.5*k2,v,q,t,kind);k4=rhs(p+5*k3,v,q,t,kind)
  out[i+1]=p+5/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(out[i+1]) or abs(out[i+1])>50:out[i+1:]=50.;return out
 return out
specs={
'power_offset':(0,[.0013,.49,1.45,3.5,.995,.54,.025]),
'resistance_offset':(1,[.0013,.49,1.45,3.5,.995,.5,.14]),
'nozzle_offset':(2,[.0013,1.,1.45,3.5,.995,.5,.05]),
'inlet_quadratic':(3,[.0013,.49,1.45,3.5,.995,.54,.025,.002]),
'inlet_saturating':(4,[.0013,.49,1.45,3.5,.995,.54,.025,.002]),
'linear_series':(5,[.001,.5,2,3,.995,1.,.025])}
lo=[.0001,.0001,.1,0.,.97,.3,.001];hi=[.01,10.,8.,100.,1.02,1.5,.3]

def bounds(kind):
 l=lo.copy();h=hi.copy()
 if kind in (1,2,5):l[5]=.499999;h[5]=.500001
 if kind==1:h[6]=2.
 if kind==5:l[6]=.0249999;h[6]=.0250001
 if kind in (3,4):l+=[0.];h+=[.1]
 return l,h

def run():
 results={}
 for name,(kind,start) in specs.items():
  if kind==5:start[5]=.5
  l,h=bounds(kind)
  # Unused n/d in some families are fixed by near equality for exploration only; final candidates omit them.
  dr=lambda t:np.array([rhs(p,v,q,t,kind) for p,v,q,_ in train])-train[:,3]
  der=least_squares(dr,start,bounds=(l,h),max_nfev=300,x_scale='jac',ftol=1e-10,gtol=1e-10,xtol=1e-10)
  fit=least_squares(lambda t:sim(train,t,kind)[1:]-train[1:,0],der.x,bounds=(l,h),max_nfev=500,x_scale='jac',ftol=1e-10,gtol=1e-10,xtol=1e-10)
  t=fit.x;pt=sim(train,t,kind);pv=sim(val,t,kind)
  result={'kind':kind,'start':start,'lower':l,'upper':h,'derivative_fit':der.x.tolist(),'parameters':t.tolist(),'train_rmse':float(np.sqrt(np.mean((pt[1:]-train[1:,0])**2))),'val_rmse':float(np.sqrt(np.mean((pv[1:]-val[1:,0])**2))),'nfev':fit.nfev}
  results[name]=result;print(name,result,flush=True)
  pd.DataFrame({'train_p':pd.Series(pt),'train_error':pd.Series(pt-train[:,0]),'val_p':pd.Series(pv),'val_error':pd.Series(pv-val[:,0])}).to_csv('diagnostics_'+name+'.csv',index=False)
 Path('refined_results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':run()
