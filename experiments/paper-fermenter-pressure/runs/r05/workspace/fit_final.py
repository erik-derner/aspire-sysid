import json,numpy as np,pandas as pd
from scipy.optimize import least_squares
from numba import njit
from pathlib import Path

P_ATM=1.0
GAMMA=1.4
TS=5.0
@njit
def rhs(p,v,q,t,kind):
 a,cf,m,s,rate=t[:5];o=max(0.,min(1.,1-v/100.));z=o**m;c=cf*(1+s)*z/(1+s*z);x=(p-P_ATM)/P_ATM
 if kind==0:
  n=t[5];d=(cf/(P_ATM*rate))**(1/(1-n));h=x/(x*x+d*d)**((1-n)/2)
 elif kind==1:
  d=cf/(P_ATM*rate);h=2*x/(d+np.sqrt(d*d+4*abs(x)))
 else:
  d=2/GAMMA*(cf/(P_ATM*rate))**2
  high=max(p,P_ATM)/P_ATM;low=min(max(p,.01),P_ATM)/P_ATM;r=max(low/high,(2/(GAMMA+1))**(GAMMA/(GAMMA-1)))
  h=np.sign(x)*high*np.sqrt(max(r**(2/GAMMA)-r**((GAMMA+1)/GAMMA),0))*np.sqrt(abs(x)/(abs(x)+d))
 return a*q-c*h
@njit
def sim(arr,t,kind):
 out=np.empty(len(arr));out[0]=arr[0,0]
 for i in range(len(arr)-1):
  p=out[i];v,q=arr[i,1:3];k1=rhs(p,v,q,t,kind);k2=rhs(p+TS/2*k1,v,q,t,kind);k3=rhs(p+TS/2*k2,v,q,t,kind);k4=rhs(p+TS*k3,v,q,t,kind)
  out[i+1]=p+TS/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(out[i+1]) or abs(out[i+1])>50:out[i+1:]=50.;return out
 return out
SPECS={'power_balance':(0,[.0013,.11,1.45,3.5,.40,.54]),'mixed_resistance':(1,[.0013,.11,1.45,3.5,.40]),'compressible_nozzle':(2,[.0013,.3,1.45,3.5,.40])}
LOW=[.0001,.005,.2,0.,.03];HIGH=[.01,.5,6.,40.,.5]

def run():
 data=[pd.read_csv('data/train.csv').to_numpy(),pd.read_csv('data/val.csv').to_numpy()]
 result={}
 for name,(kind,start) in SPECS.items():
  lo=LOW.copy();hi=HIGH.copy()
  if kind==0:lo+=[.3];hi+=[.85]
  derivative=lambda t:np.array([rhs(p,v,q,t,kind)-dp for p,v,q,dp in data[0]])
  der=least_squares(derivative,start,bounds=(lo,hi),x_scale='jac',max_nfev=600,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  residual=lambda t,ds:np.concatenate([sim(arr,t,kind)[1:]-arr[1:,0] for arr in ds])
  tr=least_squares(residual,der.x,args=([data[0]],),bounds=(lo,hi),x_scale='jac',max_nfev=600,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  fit=least_squares(residual,tr.x,args=(data,),bounds=(lo,hi),x_scale='jac',max_nfev=600,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  t=fit.x
  rmse=lambda y:float(np.sqrt(np.mean(y*y)))
  r={'kind':kind,'start':start,'bounds':[lo,hi],'derivative_fit':der.x.tolist(),'training_fit':tr.x.tolist(),'parameters':t.tolist(),'training_only_train_rmse':rmse(residual(tr.x,[data[0]])),'training_only_val_rmse':rmse(residual(tr.x,[data[1]])),'final_train_rmse':rmse(residual(t,[data[0]])),'final_val_rmse':rmse(residual(t,[data[1]])),'final_combined_rmse':rmse(residual(t,data)),'status':int(fit.status),'nfev':fit.nfev}
  cf,rate=t[1],t[4]
  r['smoothing']=float((cf/(P_ATM*rate))**(1/(1-t[5])) if kind==0 else cf/(P_ATM*rate) if kind==1 else 2/GAMMA*(cf/(P_ATM*rate))**2)
  result[name]=r;print(name,r,flush=True)
  for lab,arr in zip(['train','val'],data):
   ps=sim(arr,t,kind); de=np.array([rhs(p,v,q,t,kind)-dp for p,v,q,dp in arr]);pd.DataFrame({'p_observed':arr[:,0],'p_simulated':ps,'pressure_residual':ps-arr[:,0],'derivative_residual':de}).to_csv('final_'+name+'_'+lab+'.csv',index=False)
 Path('final_results.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':run()
