import numpy as np,pandas as pd,json,time
import sympy as sp
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv')
Y,U,V=sp.symbols('y x1 x2');vars=(Y,U,V)
# Fixed numeric centering/scaling are design choices, not fitted response coefficients.
z=(Y-1.3)/.3;u=(U-60)/20;v=(V-18)/7
families={
 'affine':[1,z,u,v],
 'bilinear':[1,z,u,v,z*u],
 'restricted':[1,z,u,v,z*u,u*u,v*v],
 'quadratic':list(PolynomialFeatures(2).fit(np.zeros((1,3))).powers_),
 'cubic':list(PolynomialFeatures(3).fit(np.zeros((1,3))).powers_),
 'state_log':[1,sp.log(Y),u,v,sp.log(Y)*u,u*u,v*v],
 'state_inverse':[1,1/Y,u,v,u/Y,u*u,v*v],
 'state_sqrt':[1,sp.sqrt(Y),u,v,u*sp.sqrt(Y),u*u,v*v],
 'product':[1,z,u,v,z*u,z*v,u*v,u*u,v*v],
 'nonlinear_loss':[1,z,u,v,z*u,u*u,z*z,z*z*u,v*v],
}
for name in ['quadratic','cubic']:
 families[name]=[z**int(p[0])*u**int(p[1])*v**int(p[2]) for p in families[name]]

def build(terms):
 p=sp.symbols('p0:'+str(len(terms))); expr=sum(pi*ti for pi,ti in zip(p,terms));fun=sp.lambdify((Y,U,V,*p),expr,'numpy',cse=True)
 df=sp.lambdify((Y,U,V,*p),[sp.diff(expr,Y)]+[sp.diff(expr,pi) for pi in p],'numpy',cse=True)
 def evalf(y,u,v,p):return float(fun(y,u,v,*p))
 def partial(y,u,v,p):
  a=df(y,u,v,*p);return float(a[0]),np.asarray(a[1:],float)
 def sim(p,d,jac=False):
  out=np.empty(len(d));out[0]=d.y.iloc[0];S=np.zeros((len(d),len(p)));xx=d[['x1','x2']].to_numpy()
  for k,(a,b) in enumerate(xx[:-1]):
   yy=out[k];ss=S[k];k1=evalf(yy,a,b,p);t2=yy+2.5*k1;k2=evalf(t2,a,b,p);t3=yy+2.5*k2;k3=evalf(t3,a,b,p);t4=yy+5*k3;k4=evalf(t4,a,b,p)
   out[k+1]=yy+5/6*(k1+2*k2+2*k3+k4)
   if not np.isfinite(out[k+1]) or abs(out[k+1])>100:return (np.full(len(d),100.),np.zeros_like(S))
   if jac:
    ay,ap=partial(yy,a,b,p);s1=ay*ss+ap
    ay,ap=partial(t2,a,b,p);s2=ay*(ss+2.5*s1)+ap
    ay,ap=partial(t3,a,b,p);s3=ay*(ss+2.5*s2)+ap
    ay,ap=partial(t4,a,b,p);s4=ay*(ss+5*s3)+ap
    S[k+1]=ss+5/6*(s1+2*s2+2*s3+s4)
  return out,S
 return evalf,sim
results={}
for name,terms in families.items():
 t=time.time();cols=[]
 for ti in terms:
  f=sp.lambdify(vars,ti,'numpy'); cols.append(np.broadcast_to(f(*A[['y','x1','x2']].to_numpy().T),len(A)))
 F=np.stack(cols,axis=1);p0=np.linalg.lstsq(F,A.dy.to_numpy(),rcond=None)[0]
 fun,sim=build(terms)
 pred=np.array([fun(*row,p0) for row in B[['y','x1','x2']].to_numpy()]);errd=float(np.sqrt(np.mean((pred-B.dy)**2)))
 def metrics(p):
  out={}
  for key,d in [('train',A),('val',B)]:
   sy,_=sim(p,d);out[key]=float(np.sqrt(np.mean((sy[1:]-d.y.to_numpy()[1:])**2)))
  return out
 m0=metrics(p0)
 cache=[None,None]
 def get(p):
  if cache[0] is None or not np.array_equal(p,cache[0]):cache[:]=[p.copy(),sim(p,A,True)]
  return cache[1]
 def resid(p):return get(p)[0][1:]-A.y.to_numpy()[1:]
 def jac(p):return get(p)[1][1:]
 fit=least_squares(resid,p0,jac=jac,max_nfev=100,xtol=1e-9,ftol=1e-9,gtol=1e-9,x_scale='jac')
 mf=metrics(fit.x)
 results[name]={'terms':[str(ti) for ti in terms],'ols':p0.tolist(),'simulation':fit.x.tolist(),'ols_metrics':m0,'sim_metrics':mf,'val_derivative_ols':errd,'nfev':fit.nfev,'success':bool(fit.success)}
 print(name,'OLS',m0,'SIM',mf,'dval',errd,'nfev',fit.nfev,'seconds',time.time()-t,flush=True)
 json.dump(results,open('explore_results.json','w'),indent=2)
