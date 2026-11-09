"""Empirical motion-family investigation; creates no candidate model files."""
import numpy as np
from scipy.optimize import least_squares
from pathlib import Path
z=np.load('kinematics.npz'); m=np.load('motion.npz')
X,Y,G=z['X'],z['Y'],z['G']; v,u=X[:,3],X[:,4]; w=m['w']; s=m['s']; lat=m['lat']; steady=m['steady']
# Samples retaining same input over current and preceding two transitions are
# less confounded by unlogged actuator dynamics; all data retained separately.
features={
 'linear':lambda v,u:np.column_stack([np.ones_like(v),v,u]),
 'odd_heading':lambda v,u:np.column_stack([u,v*u]),
 'tan_heading':lambda v,u:np.column_stack([np.tan(u),v*np.tan(u)]),
 'odd_cubic_heading':lambda v,u:np.column_stack([u,u**3,v*u,v*u**3]),
 'abs_heading':lambda v,u:np.column_stack([u,u*abs(u),v*u,v*u*abs(u)]),
 'quadratic':lambda v,u:np.column_stack([np.ones_like(v),v,u,v*v,v*u,u*u]),
 'symmetric_speed':lambda v,u:np.column_stack([np.ones_like(v),v,abs(u),v*abs(u),v*v]),
 'symmetric_speed_quadratic':lambda v,u:np.column_stack([np.ones_like(v),v,u*u,v*u*u,v*v]),
}
rmse=lambda a,b:np.sqrt(np.mean((a-b)**2))
lines=[]
def out(*a):
 text=' '.join(map(str,a));print(text);lines.append(text)
for mask,label in [(np.ones(len(v),bool),'all'),(steady,'steady')]:
 out('\nDATA',label,'n',mask.sum())
 for target,name in [(w,'heading'),(s,'forward')]:
  for fam,fun in features.items():
   A=fun(v,u);c=np.linalg.lstsq(A[mask],target[mask],rcond=None)[0]; pred=A@c
   cv=[]
   for g in np.unique(G):
    tr=mask&(G!=g);te=mask&(G==g);cc=np.linalg.lstsq(A[tr],target[tr],rcond=None)[0];cv.extend((target[te]-A[te]@cc).tolist())
   out(name,fam,'train RMSE',rmse(pred[mask],target[mask]),'LOTO RMSE',np.sqrt(np.mean(np.array(cv)**2)),'coeff',c.tolist())

# Odd dead zone captures lack of turn for small steering command.
def heading(p,v,u):
 a,b,d=p;return (a+b*v)*np.sign(u)*np.maximum(abs(u)-d,0)
def heading_tanh(p,v,u):
 a,b,d,k=p;q=np.sign(u)*np.maximum(abs(u)-d,0);return (a+b*v)*np.tanh(k*q)/k
for fun,p0,bounds,name in [(heading,[.15,.1,.1],([-2,-5,0],[2,5,.5]),'deadzone'),(heading_tanh,[.15,.1,.1,1],([-2,-5,0,.01],[2,5,.5,10]),'deadzone_tanh')]:
 for mask,label in [(np.ones(len(v),bool),'all'),(steady,'steady')]:
  fit=lambda mm:least_squares(lambda p:fun(p,v[mm],u[mm])-w[mm],p0,bounds=bounds,xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=3000).x
  p=fit(mask);pred=fun(p,v,u);cv=[]
  for g in np.unique(G):
   tr=mask&(G!=g);te=mask&(G==g);pg=fit(tr);cv.extend((w[te]-fun(pg,v[te],u[te])).tolist())
  out(name,label,'train RMSE',rmse(pred[mask],w[mask]),'LOTO RMSE',np.sqrt(np.mean(np.array(cv)**2)),'parameters',p.tolist())
  if name=='deadzone' and label=='steady':wpred=pred; hp=p
# Residual state dependence and input transitions: no prior input allowed in model.
A=features['symmetric_speed'](v,u);c=np.linalg.lstsq(A[steady],s[steady],rcond=None)[0];spred=A@c
change=np.r_[True,np.any(np.diff(X[:,3:],axis=0)!=0,axis=1)|(np.diff(G)!=0)]
for pred,target,name in [(wpred,w,'heading_deadzone'),(spred,s,'forward_sym')]:
 residual=target-pred
 out('\nResidual',name,'fit steady')
 for mask,label in [(steady,'steady'),(change,'input_change'),(~steady&~change,'one_after_change')]:out(label,'n',mask.sum(),'RMSE',rmse(pred[mask],target[mask]),'mean',residual[mask].mean())
 for idx in range(3):out('state correlation',idx,np.corrcoef(residual[steady],X[steady,idx])[0,1])
 out('lag 1 within trajectories correlation',np.corrcoef(residual[1:][G[1:]==G[:-1]],residual[:-1][G[1:]==G[:-1]])[0,1])
 # Fit state terms added to a frozen nonlinear input prediction, then group CV.
 B=np.column_stack([np.ones(len(v)),X[:,:3],np.sin(X[:,2]),np.cos(X[:,2])]);bc=np.linalg.lstsq(B[steady],residual[steady],rcond=None)[0]
 out('state residual correction training RMSE',rmse(target[steady],(pred+B@bc)[steady]),'coeff',bc.tolist())
# Body displacement midpoint relation to observed wrapped heading increment.
out('\nLateral: lat versus half-heading times forward')
for mask,label in [(np.ones(len(v),bool),'all'),(steady,'steady')]:
 out(label,'lat RMSE vs zero',rmse(lat[mask],np.zeros(mask.sum())),'lat RMSE vs s*tan(w/2)',rmse(lat[mask],(s*np.tan(w/2))[mask]))
# Heading quantization identified from wrapped increments.
out('max quantization residual angular grid pi/18000',np.max(abs(w/(np.pi/18000)-np.round(w/(np.pi/18000)))))
Path('helper_analysis_results.txt').write_text('\n'.join(lines))
