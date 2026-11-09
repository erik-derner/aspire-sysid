exec(open('fit_explore.py').read().split('results={}')[0])
# General nonlinear symbolic dynamics, analytical RK4 sensitivities.
def build_expr(expr,p):
 fun=sp.lambdify((Y,U,V,*p),expr,'numpy',cse=True)
 df=sp.lambdify((Y,U,V,*p),[sp.diff(expr,Y)]+[sp.diff(expr,pi) for pi in p],'numpy',cse=True)
 def evalf(y,u,v,p):return float(fun(y,u,v,*p))
 def partial(y,u,v,p):
  a=df(y,u,v,*p);return float(a[0]),np.asarray(a[1:],float)
 # borrow identical integrator by replacing build's callbacks
 source=open('fit_explore.py').read();body=source[source.index(' def sim(p,d,jac=False):'):source.index(' return evalf,sim')]
 scope={'np':np,'evalf':evalf,'partial':partial};exec('if True:\n'+body,scope)
 return evalf,scope['sim']
p=sp.symbols('p0:15');rawu=U/60;rawv=V/18
cases={
 'rational_rate':(p[0]+p[1]*rawv+p[2]*rawv**2-(p[3]+p[4]*rawu+p[5]*rawu**2)*(Y-p[6])/(1+p[7]*(Y-p[6])),[0,.008,.008,.25,-.2,.04,1,.3],[-.1,-.3,-.3,.001,-1,-1,.5,-.2],[.1,.3,.3,1,1,1,1.05,10]),
 'rational_all':((p[0]+p[1]*z+p[2]*u+p[3]*v+p[4]*z*u+p[5]*u**2+p[6]*v**2+p[7]*u*v)/(1+p[8]*z+p[9]*u+p[10]*v),[0,-.015,.012,.008,.006,.002,.001,0,.1,0,0],[-1]*8+[-.25,-.25,-.25],[1]*8+[.25,.25,.25]),
 'positive_rate':(p[0]+p[1]*rawv+p[2]*rawv**2-(p[3]**2+p[4]**2*(rawu-p[5])**2)*(Y-p[6]),[0,.006,.008,.04,.2,1.6,1],[-.1,-.3,-.3,.001,0,1,.5],[.1,.3,.3,1,1,3,1.1]),
 'sigmoid_rate':(p[0]+p[1]*rawv+p[2]*rawv**2-(p[3]+p[4]/(1+sp.exp(p[5]*(rawu-p[6]))))*(Y-p[7]),[0,.006,.008,.01,.3,3,1,1],[-.1,-.3,-.3,.001,.001,.01,0,.5],[.1,.3,.3,1,1,20,3,1.1]),
 'exp_rate':(p[0]+p[1]*rawv+p[2]*rawv**2-(p[3]+p[4]*sp.exp(-p[5]*rawu))*(Y-p[6]),[0,.006,.008,-.04,.25,1,1],[-.1,-.3,-.3,-1,.001,.01,.5],[.1,.3,.3,1,2,10,1.1]),
 'power_balance':(p[0]+p[1]*rawv**p[2]-(p[3]+p[4]*rawu+p[5]*rawu**2)*(Y-p[6])*(Y/p[6])**p[7],[0,.015,1.3,.2,-.15,.03,1,-1],[-.1,0,.3,.001,-1,-1,.5,-4],[.1,.2,4,1,1,1,1.05,4]),
 'rational_equilibrium':((p[0]+p[1]*rawu+p[2]*rawu**2)*(p[3]+p[4]*rawv**p[5]/(p[6]-rawu)-Y),[.2,-.2,.055,1,.12,1,1.7],[.001,-1,-1,.5,0,.3,1.60],[1,1,1,1.1,2,4,5]),
 'exp_equilibrium':((p[0]+p[1]*rawu+p[2]*rawu**2)*(p[3]+p[4]*sp.exp(p[5]*rawu)*rawv**p[6]-Y),[.2,-.2,.06,1,.002,3,1],[.001,-1,-1,.5,0,.1,.3],[1,1,1,1.1,2,10,4]),
 'rational_state':(p[0]+p[1]*rawv+p[2]*rawv**2-(p[3]+p[4]*rawu+p[5]*rawu**2)*(Y-p[6])/(Y**p[7]),[0,.008,.008,.25,-.2,.04,1,1],[-.1,-.3,-.3,.001,-1,-1,.5,-4],[.1,.3,.3,1,1,1,1.05,4]),
}
results={}
np.seterr(over='ignore',invalid='ignore',divide='ignore')
for name,(expr,p0,lo,hi) in cases.items():
 t=time.time();pp=p[:len(p0)];fun,sim=build_expr(expr,pp);X=A[['y','x1','x2']].to_numpy()
 def dr(p):
  pred=np.array([fun(*row,p) for row in X]);return np.nan_to_num(pred-A.dy.to_numpy(),nan=100,posinf=100,neginf=-100)
 fitd=least_squares(dr,p0,bounds=(lo,hi),max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-9,x_scale='jac')
 cache=[None,None]
 def get(p):
  if cache[0] is None or not np.array_equal(cache[0],p):cache[:]=[p.copy(),sim(p,A,True)]
  return cache[1]
 def sr(p):return np.nan_to_num(get(p)[0][1:]-A.y.to_numpy()[1:],nan=100,posinf=100,neginf=-100)
 def sj(p):return np.nan_to_num(get(p)[1][1:],nan=0,posinf=0,neginf=0)
 fits=least_squares(sr,fitd.x,jac=sj,bounds=(lo,hi),max_nfev=150,ftol=1e-8,xtol=1e-8,gtol=1e-8,x_scale='jac')
 def metrics(p):return {key:float(np.sqrt(np.mean((sim(p,d)[0][1:]-d.y.to_numpy()[1:])**2))) for key,d in [('train',A),('val',B)]}
 results[name]={'expression':str(expr),'initial':p0,'bounds':[lo,hi],'derivative':fitd.x.tolist(),'simulation':fits.x.tolist(),'deriv_metrics':metrics(fitd.x),'sim_metrics':metrics(fits.x),'nfev':[fitd.nfev,fits.nfev]}
 print(name,'D',results[name]['deriv_metrics'],'S',results[name]['sim_metrics'],'p',fits.x.tolist(),'nfev',fits.nfev,'sec',time.time()-t,flush=True)
 json.dump(results,open('nonlinear_results.json','w'),indent=2)
