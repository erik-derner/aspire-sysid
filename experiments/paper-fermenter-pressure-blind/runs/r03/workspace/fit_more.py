exec(open('fit_nonlinear.py').read().split('cases={')[0])
from itertools import product
cases={}
# State transforms with estimated offset, relaxing directly on transformed state.
for kind,g in [('shift_log',sp.log(Y-p[7])),('shift_inverse',1/(Y-p[7])),('shift_sqrt',sp.sqrt(Y-p[7]))]:
 expr=p[0]+p[1]*g+p[2]*u+p[3]*v+p[4]*g*u+p[5]*u**2+p[6]*v**2
 if kind=='shift_inverse': p0=[-.1,.1,0,.007,-.04,0,.001,.5]
 elif kind=='shift_log':p0=[0,-.05,0,.007,.025,0,.001,.5]
 else:p0=[.1,-.1,0,.007,.05,0,.001,.5]
 cases[kind]=(expr,p0,[-5]*7+[-5],[5]*7+[.97])
# Saturating state feedback extrapolates smoothly, with no pole or logarithmic domain.
cases['tanh_state']=(p[0]+p[1]*sp.tanh(p[7]*z)+p[2]*u+p[3]*v+p[4]*u*sp.tanh(p[7]*z)+p[5]*u**2+p[6]*v**2,[0,-.025,.015,.007,.015,0,.001,.7],[-1]*7+[.05],[1]*7+[3])
# Dynamic response of logarithmic state: dy/y = affine-input-dependent relaxation in log(y).
cases['log_coordinate']=(Y*(p[0]+p[1]*sp.log(Y)+p[2]*u+p[3]*v+p[4]*u*sp.log(Y)+p[5]*u**2+p[6]*v**2),[.015,-.1,.005,.005,.07,0,.001],[-1]*7,[1]*7)
# Cubic input-rate and state-input mixed features but no higher powers of y.
cases['input_cubic']=(p[0]+p[1]*z+p[2]*u+p[3]*v+p[4]*z*u+p[5]*u**2+p[6]*v**2+p[7]*z*u**2+p[8]*u**3+p[9]*v**3+p[10]*z*v+p[11]*u*v,[0,-.015,.013,.007,.006,.002,.001,0,0,0,0,0],[-1]*12,[1]*12)
# Multiplicative response uses exp inputs but stays linear in y.
cases['exp_input_bilinear']=(p[0]+p[1]*z+p[2]*sp.exp(p[7]*u)+p[3]*v+p[4]*z*u+p[5]*u**2+p[6]*v**2,[0,-.015,.007,.007,.006,.002,.001,1],[-1]*7+[.05],[1]*7+[3])
results={};np.seterr(over='ignore',invalid='ignore',divide='ignore')
for name,(expr,p0,lo,hi) in cases.items():
 t=time.time();pp=p[:len(p0)];fun,sim=build_expr(expr,pp);X=A[['y','x1','x2']].to_numpy()
 def dr(p):return np.nan_to_num(np.array([fun(*row,p) for row in X])-A.dy.to_numpy(),nan=100,posinf=100,neginf=-100)
 fitd=least_squares(dr,p0,bounds=(lo,hi),max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-9,x_scale='jac')
 cache=[None,None]
 def get(p):
  if cache[0] is None or not np.array_equal(cache[0],p):cache[:]=[p.copy(),sim(p,A,True)]
  return cache[1]
 def sr(p):return np.nan_to_num(get(p)[0][1:]-A.y.to_numpy()[1:],nan=100,posinf=100,neginf=-100)
 def sj(p):return np.nan_to_num(get(p)[1][1:],nan=0,posinf=0,neginf=0)
 fits=least_squares(sr,fitd.x,jac=sj,bounds=(lo,hi),max_nfev=100,ftol=1e-8,xtol=1e-8,gtol=1e-8,x_scale='jac')
 def metrics(p):return {key:float(np.sqrt(np.mean((sim(p,d)[0][1:]-d.y.to_numpy()[1:])**2))) for key,d in [('train',A),('val',B)]}
 results[name]={'expression':str(expr),'initial':p0,'bounds':[lo,hi],'derivative':fitd.x.tolist(),'simulation':fits.x.tolist(),'deriv_metrics':metrics(fitd.x),'sim_metrics':metrics(fits.x),'nfev':[fitd.nfev,fits.nfev]}
 print(name,'D',results[name]['deriv_metrics'],'S',results[name]['sim_metrics'],'p',fits.x.tolist(),'nfev',fits.nfev,'sec',time.time()-t,flush=True)
 json.dump(results,open('more_results.json','w'),indent=2)
# Higher polynomial degree held-out diagnostics.
R=json.load(open('explore_results.json'))
for degree in [4,5]:
 name='polynomial'+str(degree);powers=PolynomialFeatures(degree).fit(np.zeros((1,3))).powers_;terms=[z**int(q[0])*u**int(q[1])*v**int(q[2]) for q in powers];F=[]
 for ti in terms:
  f=sp.lambdify(vars,ti,'numpy');F.append(np.broadcast_to(f(*A[['y','x1','x2']].to_numpy().T),len(A)))
 F=np.stack(F,axis=1);p0=np.linalg.lstsq(F,A.dy.to_numpy(),rcond=None)[0];fun,sim=build(terms)
 print(name,'OLS', {key:float(np.sqrt(np.mean((sim(p0,d)[0][1:]-d.y.to_numpy()[1:])**2))) for key,d in [('train',A),('val',B)]},flush=True)
