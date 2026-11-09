import numpy as np
from scipy.optimize import least_squares
from pathlib import Path
z=np.load('kinematics.npz');m=np.load('motion.npz');X=z['X'];G=z['G'];v,u=X[:,3],X[:,4];t=X[:,2];s,w=m['s'],m['w'];steady=m['steady'];lines=[]
def out(*a):
 text=' '.join(map(str,a));print(text);lines.append(text)
q=steady&(v>.02);R=np.divide(s,v)
out('speed ratio correlations',[(i,np.corrcoef(R[q],a[q])[0,1]) for i,a in [('theta',t),('cos',np.cos(t)),('sin',np.sin(t)),('cos2',np.cos(2*t)),('sin2',np.sin(2*t)),('y',X[:,0]),('v',v),('absu',abs(u))]])
out('group ratios',[(int(g),R[q&(G==g)].mean(),R[q&(G==g)].std()) for g in np.unique(G)])
base=np.column_stack([np.ones(len(v)),v,u]);extras={
 'none':np.zeros((len(v),0)),
 'position':X[:,:2],
 'heading_harmonic':np.column_stack([v*np.cos(t),v*np.sin(t)]),
 'heading_second_harmonic':np.column_stack([v*np.cos(2*t),v*np.sin(2*t)]),
 'heading_first_second':np.column_stack([v*np.cos(t),v*np.sin(t),v*np.cos(2*t),v*np.sin(2*t)]),
 'speed_position':np.column_stack([v*X[:,0],v*X[:,1]]),
}
for name,E in extras.items():
 A=np.column_stack([base,E]);c=np.linalg.lstsq(A[steady],s[steady],rcond=None)[0];p=A@c;cv=[]
 for g in np.unique(G):
  tr=steady&(G!=g);te=steady&(G==g);cc=np.linalg.lstsq(A[tr],s[tr],rcond=None)[0];cv.extend((s[te]-A[te]@cc).tolist())
 out('speed',name,'steady training RMSE',np.sqrt(np.mean((p[steady]-s[steady])**2)),'LOTO RMSE',np.sqrt(np.mean(np.array(cv)**2)),'coeff',c.tolist())
# Joint fit deadzone plus possible state correction, instead of fixed predictions.
extra_w={'none':np.zeros((len(v),0)),'position':X[:,:2], 'heading':np.column_stack([np.cos(t),np.sin(t)]),'heading_second':np.column_stack([np.cos(2*t),np.sin(2*t)])}
for name,E in extra_w.items():
 def predict(p):return (p[0]+p[1]*v)*np.sign(u)*np.maximum(abs(u)-p[2],0)+E@p[3:]
 p0=[.15,.1,.1]+[0]*E.shape[1]
 def fit(mask):return least_squares(lambda p:predict(p)[mask]-w[mask],p0,bounds=([-2,-5,0]+[-2]*E.shape[1],[2,5,.5]+[2]*E.shape[1]),max_nfev=2000,xtol=1e-12,ftol=1e-12,gtol=1e-12).x
 p=fit(steady);cv=[]
 for g in np.unique(G):
  tr=steady&(G!=g);te=steady&(G==g);pg=fit(tr);cv.extend((w[te]-predict(pg)[te]).tolist())
 out('heading',name,'steady training RMSE',np.sqrt(np.mean((predict(p)[steady]-w[steady])**2)),'LOTO RMSE',np.sqrt(np.mean(np.array(cv)**2)),'coeff',p.tolist())
# Segment-end evaluation removes short transients equally in each experiment.
last=np.array([i%149%5>=3 for i in range(len(v))])
# Compare signed turn response to delay: previous and current inputs alone.
prev=np.r_[0,np.arange(len(v)-1)];valid=np.r_[False,G[1:]==G[:-1]]
A=np.column_stack([u,v*u,u[prev],v[prev]*u[prev]])
c=np.linalg.lstsq(A[valid],w[valid],rcond=None)[0]
out('heading linear current and previous input all valid train RMSE',np.sqrt(np.mean((A[valid]@c-w[valid])**2)),'coeff',c.tolist())
Path('helper_state_results.txt').write_text('\n'.join(lines))
