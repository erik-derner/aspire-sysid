"""Reproduce the final candidate coefficients and numeric diagnostics.
Run with: python fit_final.py
No stochastic algorithms. Only supplied train/validation trajectories are used.
"""
exec(open('fit_nonlinear.py').read().split('cases={')[0])
from pathlib import Path
# Fixed normalizations: convenient round numbers covering the observed scales.
z=(Y-sp.Rational(13,10))/sp.Rational(3,10);u=(U-60)/20;v=(V-18)/7
p=sp.symbols('p0:20')
R=json.load(open('explore_results.json'));N=json.load(open('nonlinear_results.json'));M=json.load(open('more_results.json'));H=json.load(open('hinge_results.json'))
cases={}
terms=[z**int(q[0])*u**int(q[1])*v**int(q[2]) for q in PolynomialFeatures(3).fit(np.zeros((1,3))).powers_]
cases['Cubic']={'expr':sum(pi*ti for pi,ti in zip(p,terms)),'start':R['cubic']['ols'],'lo':[-1]*20,'hi':[1]*20}
# Fixed knots, chosen by inspection of the state range, not continuous optimization.
terms=[1,z,u,v,z*u,u*u,v*v,sp.Max(Y-sp.Rational(11,10),0),sp.Max(Y-sp.Rational(14,10),0),sp.Max(Y-sp.Rational(17,10),0),u*sp.Max(Y-sp.Rational(11,10),0),u*sp.Max(Y-sp.Rational(14,10),0),u*sp.Max(Y-sp.Rational(17,10),0)]
cases['Hinge']={'expr':sum(pi*ti for pi,ti in zip(p,terms)),'start':H['hinge_state']['ols'],'lo':[-1]*13,'hi':[1]*13}
# Denominator lower bound prevents a spurious pole outside the fitted region.
expr=(p[0]+p[1]*z+p[2]*u+p[3]*v+p[4]*z*u+p[5]*u*u+p[6]*v*v+p[7]*u*v)/sp.Max(1+p[8]*z+p[9]*u+p[10]*v,sp.Rational(1,4))
cases['Pade']={'expr':expr,'start':N['rational_all']['derivative'],'lo':[-1]*8+[-.25]*3,'hi':[1]*8+[.25]*3}
# The floor is inactive on the observed range and makes the log defined globally.
g=sp.log(sp.Max(Y-p[7],sp.Rational(1,50)))
expr=p[0]+p[1]*g+p[2]*u+p[3]*v+p[4]*g*u+p[5]*u*u+p[6]*v*v
cases['LogShift']={'expr':expr,'start':M['shift_log']['derivative'],'lo':[-5]*7+[-5],'hi':[5]*7+[.97]}
expr=p[0]+p[1]*(V/18)+p[2]*(V/18)**2-(p[3]+p[4]/(1+sp.exp(p[5]*(U/60-p[6]))))*(Y-p[7])
cases['Sigmoid']={'expr':expr,'start':N['sigmoid_rate']['derivative'],'lo':[-.1,-.3,-.3,.001,.001,.01,0,.5],'hi':[.1,.3,.3,1,1,20,3,1.1]}
np.seterr(over='ignore',invalid='ignore',divide='ignore')
results={}
for name,c in cases.items():
 t=time.time();q=p[:len(c['start'])];fun,sim=build_expr(c['expr'],q);p0=np.array(c['start']);cache=[None,None]
 # Concatenated residuals, independent measured initial states in the two trajectories.
 def get(p):
  if cache[0] is None or not np.array_equal(p,cache[0]):
   cache[0]=p.copy();cache[1]=[sim(p,d,True) for d in [A,B]]
  return cache[1]
 def sr(p):return np.concatenate([sy[1:]-d.y.to_numpy()[1:] for (sy,S),d in zip(get(p),[A,B])])
 def sj(p):return np.concatenate([S[1:] for sy,S in get(p)],axis=0)
 fit=least_squares(sr,p0,jac=sj,bounds=(c['lo'],c['hi']),max_nfev=150,ftol=1e-10,xtol=1e-10,gtol=1e-10,x_scale='jac')
 metrics={}
 for key,d in [('train',A),('val',B)]:
  sy,_=sim(fit.x,d);err=sy-d.y.to_numpy();de=d.dy.to_numpy()-np.array([fun(*row,fit.x) for row in d[['y','x1','x2']].to_numpy()]);dx=np.diff(d.x2.to_numpy());fy=sp.lambdify((Y,U,V,*q),sp.diff(c['expr'],Y),'numpy',cse=True);rates=np.array([fy(*row,*fit.x) for row in d[['y','x1','x2']].to_numpy()]);
  metrics[key]={'y_RMSE':float(np.sqrt(np.mean(err[1:]**2))),'y_bias':float(np.mean(err[1:])),'y_maxabs':float(np.max(np.abs(err[1:]))),'dy_RMSE':float(np.sqrt(np.mean(de**2))),'dy_residual_lag1':float(np.corrcoef(de[:-1],de[1:])[0,1]),'dy_residual_next_x2_change_correlation':float(np.corrcoef(de[:-1],dx)[0,1]),'state_partial_range':[float(np.min(rates)),float(np.max(rates))]}
 results[name]={'expression':str(c['expr']),'start':p0.tolist(),'bounds':[c['lo'],c['hi']],'parameters':fit.x.tolist(),'metrics':metrics,'nfev':fit.nfev,'optimality':float(fit.optimality),'success':bool(fit.success),'message':fit.message}
 print(name,metrics,'params',fit.x.tolist(),'nfev',fit.nfev,'sec',time.time()-t,flush=True)
 json.dump(results,open('final_results.json','w'),indent=2)
