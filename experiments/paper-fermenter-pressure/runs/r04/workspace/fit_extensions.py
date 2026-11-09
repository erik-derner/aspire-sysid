import os,json
import numpy as np,pandas as pd
from scipy.optimize import least_squares
from numba import njit
D={n:pd.read_csv('data/'+n+'.csv')[['p','valve','flow','dp']].to_numpy() for n in ['train','val']}
# Common positive monotone rational-power valve characteristic b*x**m/(1+c*x**m).
# z = a,b,c,s,n,m,pa,g; g is flow exponent or high-pressure compressibility modifier.
@njit
def rhs(p,v,q,z,fam):
 a,b,c,s,n,m,pa,g=z
 x=max(0.,min(1.,(100.-v)/100.));h=p-pa
 cv=b*x**m/(1.+c*x**m)
 hp=max(h,0.)
 if fam==0: ph=hp*(hp+s)**(n-1.)
 elif fam==1: ph=np.sqrt(hp+s)-np.sqrt(s)
 elif fam==2: ph=hp*(max(p+pa,0.)/(2.*pa))**.5/np.sqrt(hp+s)
 elif fam==3: ph=hp*(hp+s)**(n-1.)
 elif fam==4: ph=hp*(hp+s)**(n-1.)*(1.+g*hp)
 else: ph=hp*(hp+s)**(n-1.)
 inlet=a*max(q,0.)
 if fam==3: inlet=a*20.*(max(q,0.)/20.)**g
 full=b/(1.+c)
 slope=full*s**(n-1.)
 if fam==1:slope=full/(2.*np.sqrt(s))
 if fam==2:slope=full/np.sqrt(s)
 return inlet-cv*ph+slope*max(-h,0.)
@njit
def sim(z,d,fam):
 N=len(d);out=np.empty(N);out[0]=d[0,0]
 for k in range(N-1):
  p=out[k];v=d[k,1];q=d[k,2]
  k1=rhs(p,v,q,z,fam);k2=rhs(p+2.5*k1,v,q,z,fam);k3=rhs(p+2.5*k2,v,q,z,fam);k4=rhs(p+5*k3,v,q,z,fam)
  out[k+1]=p+5.*(k1+2.*k2+2.*k3+k4)/6.
  if not np.isfinite(out[k+1]) or abs(out[k+1])>100:out[k+1:]=100.;break
 return out
@njit
def deriv(z,d,fam):
 out=np.empty(len(d))
 for k in range(len(d)):out[k]=rhs(d[k,0],d[k,1],d[k,2],z,fam)
 return out
lo=np.array([.0001,.01,0.,.0005,.3,.5,.98,0.])
hi=np.array([.004,1.,30.,.5,1.3,3.,1.02,3.])
specs={
 'rational_power':(0,[.0013,.17,1.,.03,.5,1.3,1.,1.],[0,1,2,3,4,5]),
 'reference_power':(0,[.0013,.17,1.,.03,.5,1.3,.992,1.],[0,1,2,3,4,5,6]),
 'mixed_resistance':(1,[.0013,.17,1.,.008,.5,1.3,.992,1.],[0,1,2,3,5,6]),
 'compressible':(2,[.0013,.17,1.,.03,.5,1.3,.992,1.],[0,1,2,3,5,6]),
 'flow_calibration':(3,[.0013,.17,1.,.03,.5,1.3,.992,1.],[0,1,2,3,4,5,6,7]),
 'pressure_correction':(4,[.0013,.17,1.,.03,.5,1.3,.992,.2],[0,1,2,3,4,5,6,7])}
def run(label,fam,start,idx,data_names=['train'],init_given=None):
 start=np.array(start);idx=np.array(idx);L=lo[idx];H=hi[idx]
 def unpack(t):
  z=start.copy();z[idx]=t;return z
 def fd(t):return np.concatenate([(deriv(unpack(t),D[name],fam)[:-1]-D[name][:-1,3])*100 for name in data_names])
 if init_given is None:
  ini=least_squares(fd,start[idx],bounds=(L,H),x_scale='jac',max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-9).x
 else:ini=np.array(init_given)[idx]
 def fs(t):return np.concatenate([sim(unpack(t),D[name],fam)[1:]-D[name][1:,0] for name in data_names])
 fit=least_squares(fs,ini,bounds=(L,H),x_scale='jac',max_nfev=1200,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 z=unpack(fit.x);rec={'fam':fam,'start':start.tolist(),'idx':idx.tolist(),'derivative_init':unpack(ini).tolist(),'params':z.tolist(),'nfev':fit.nfev,'success':bool(fit.success),'data':data_names,'bounds_lower':L.tolist(),'bounds_upper':H.tolist()}
 for name,d in D.items():
  pred=sim(z,d,fam);r=pred-d[:,0];dr=deriv(z,d,fam)-d[:,3]
  rec[name+'_rmse']=float(np.sqrt(np.mean(r[1:]**2)));rec[name+'_derivative_rmse']=float(np.sqrt(np.mean(dr[:-1]**2)))
  np.savez('results/'+label+'_'+name+'.npz',pred=pred,res=r,dres=dr)
 print(label,rec['params'],'RMSE',rec['train_rmse'],rec['val_rmse'],flush=True)
 return rec
if __name__=='__main__':
 results={}
 for label,spec in specs.items():
  results[label]=run(label,*spec);json.dump(results,open('results/extensions.json','w'),indent=2)
