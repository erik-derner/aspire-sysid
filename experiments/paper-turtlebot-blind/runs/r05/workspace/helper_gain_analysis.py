import numpy as np
from scipy.optimize import least_squares
from pathlib import Path
z=np.load('kinematics.npz');m=np.load('motion.npz');X=z['X'];G=z['G'];v,u=X[:,3],X[:,4];w=m['w'];q=m['steady'];lines=[]
funs={
 'sqrt_v_gain':(lambda p:(p[0]+p[1]*np.sqrt(v))*np.sign(u)*np.maximum(abs(u)-p[2],0),[.1,.1,.08],([-2,-5,0],[2,5,.5])),
 'quadratic_v_gain':(lambda p:(p[0]+p[1]*v+p[3]*v*v)*np.sign(u)*np.maximum(abs(u)-p[2],0),[.15,.1,.08,0],([-2,-5,0,-20],[2,5,.5,20])),
 'rational_v_gain':(lambda p:p[0]*v/(v+p[1])*np.sign(u)*np.maximum(abs(u)-p[2],0),[.17,.005,.08],([0,1e-7,0],[2,2,.5])),
 'exponential_v_gain':(lambda p:p[0]*(1-np.exp(-v/p[1]))*np.sign(u)*np.maximum(abs(u)-p[2],0),[.17,.01,.08],([0,1e-7,0],[2,2,.5])),
 'rational_floor_gain':(lambda p:(p[0]+p[3]*v/(v+p[1]))*np.sign(u)*np.maximum(abs(u)-p[2],0),[.1,.02,.08,.08],([-2,1e-7,0,-2],[2,2,.5,2]))}
for name,(fun,p0,bounds) in funs.items():
 def fit(mask):return least_squares(lambda p:fun(p)[mask]-w[mask],p0,bounds=bounds,xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=3000).x
 p=fit(q);cv=[];params=[]
 for g in np.unique(G):
  tr=q&(G!=g);te=q&(G==g);pg=fit(tr);params.append(pg.tolist());cv.extend((w[te]-fun(pg)[te]).tolist())
 text=f'{name}: steady training RMSE {np.sqrt(np.mean((fun(p)[q]-w[q])**2))}; LOTO RMSE {np.sqrt(np.mean(np.array(cv)**2))}; parameters {p.tolist()}; LOTO fit parameters {params}'
 print(text);lines.append(text)
Path('helper_gain_results.txt').write_text('\n'.join(lines))
