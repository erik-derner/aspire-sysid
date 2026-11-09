exec(open('fit_explore.py').read().split('results={}')[0])
# Continuous piecewise-linear basis motivated by systematic state-range residuals.
families={
 'hinge_state':[1,z,u,v,z*u,u*u,v*v,sp.Max(Y-1.1,0),sp.Max(Y-1.4,0),sp.Max(Y-1.7,0),u*sp.Max(Y-1.1,0),u*sp.Max(Y-1.4,0),u*sp.Max(Y-1.7,0)],
 'hinge_input':[1,z,u,v,z*u,u*u,v*v,sp.Max(U-70,0)/20,sp.Max(U-85,0)/20,z*sp.Max(U-70,0)/20,z*sp.Max(U-85,0)/20],
}
results={}
for name,terms in families.items():
 t=time.time();F=[]
 # Scalar evaluation avoids lambdify broadcasting for Max.
 for ti in terms:
  f=sp.lambdify(vars,ti,'numpy'); F.append([f(*row) for row in A[['y','x1','x2']].to_numpy()])
 F=np.array(F).T;p0=np.linalg.lstsq(F,A.dy.to_numpy(),rcond=None)[0];fun,sim=build(terms)
 cache=[None,None]
 def get(p):
  if cache[0] is None or not np.array_equal(cache[0],p):cache[:]=[p.copy(),sim(p,A,True)]
  return cache[1]
 def sr(p):return get(p)[0][1:]-A.y.to_numpy()[1:]
 def sj(p):return get(p)[1][1:]
 fit=least_squares(sr,p0,jac=sj,max_nfev=100,ftol=1e-9,xtol=1e-9,gtol=1e-9,x_scale='jac')
 def met(p):return {key:float(np.sqrt(np.mean((sim(p,d)[0][1:]-d.y.to_numpy()[1:])**2))) for key,d in [('train',A),('val',B)]}
 results[name]={'terms':[str(ti) for ti in terms],'ols':p0.tolist(),'simulation':fit.x.tolist(),'ols_metrics':met(p0),'sim_metrics':met(fit.x),'nfev':fit.nfev}
 print(name,'OLS',met(p0),'SIM',met(fit.x),'p',fit.x,flush=True)
 json.dump(results,open('hinge_results.json','w'),indent=2)
