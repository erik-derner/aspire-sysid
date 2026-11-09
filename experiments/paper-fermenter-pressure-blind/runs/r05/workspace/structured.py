import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from rollout import rk4
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
R=json.load(open('poly_results.json')); r=next(z for z in R if z['deg']==3 and z['reg']==0);p=np.array(r['powers']);c=np.array(r['coef'])
for d in [tr,va]:
 pred=np.prod(np.array([(d.y-1).values,d.x1.values/60,d.x2.values/20]).T[:,None,:]**p,axis=2)@c;e=d.dy.values-pred
 print('residual correlations',np.corrcoef(np.c_[e,d[['y','x1','x2']]].T)[0]);print('autocorr',[np.corrcoef(e[:-i],e[i:])[0,1] for i in [1,2,3,5,10]])
 print('input delta residual',[np.corrcoef(e[1:],np.diff(d[k]))[0,1] for k in ['x1','x2']])
 print('time blocks',[round(np.sqrt(np.mean(e[i:i+100]**2)),6) for i in range(0,len(e),100)])
 print('large residuals',d.iloc[np.argsort(abs(e))[-12:]].assign(res=e[np.argsort(abs(e))[-12:]]).to_string())
# separable damping structures: source x1 polynomial and x2 polynomial; state coefficient x1 dependent
families={
 'bilinear':[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(0,2,0),(0,0,2)],
 'damping2':[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,2,0),(0,2,0),(0,3,0),(0,0,2)],
 'damping3':[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,2,0),(1,3,0),(0,2,0),(0,3,0),(0,0,2),(0,0,3)],
 'mixedforcing':[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(0,2,0),(0,0,2),(0,1,1)],
 'quarticforce':[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,2,0),(0,2,0),(0,3,0),(0,4,0),(0,0,2),(0,0,3)],
}
res=[]
for label,powers in families.items():
 p=np.array(powers);Xs=[]
 for d in [tr,va]:Xs.append(np.prod(np.array([d.y.values-1,d.x1.values/60,d.x2.values/20]).T[:,None,:]**p,axis=2))
 c=np.linalg.lstsq(Xs[0],tr.dy,rcond=None)[0]
 def f(y,u,v):return np.prod(np.array([y-1,u/60,v/20])**p,axis=1)@c
 print(label,'der',[np.sqrt(np.mean((X@c-d.dy)**2)) for X,d in zip(Xs,[tr,va])],'roll',[np.sqrt(np.mean((rk4(f,d)[1:]-d.y.values[1:])**2)) for d in [tr,va]])
 res.append(dict(label=label,powers=p.tolist(),coef=c.tolist()))
# variable-projection nonlinear source+damping fits
families2=['expdamp','powerdamp','rationaldamp','sigmoidforcing','logisticdamp','expboth']
def features(theta,d,label):
 y,u,v=d.y.values,d.x1.values/60,d.x2.values/20
 if label=='expdamp': k,q=theta; return np.c_[np.ones(len(y)),u,u*u,v**q,-(y-1)*np.exp(-k*u)]
 if label=='powerdamp': k,q,h=theta; return np.c_[np.ones(len(y)),u,u*u,v**q,-(y-h)*np.maximum(1.7-u,.01)**k]
 if label=='rationaldamp': k,q=theta; return np.c_[np.ones(len(y)),u,u*u,v**q,-(y-1)/(1+k*u)**2]
 if label=='sigmoidforcing': k,h,q=theta; return np.c_[np.ones(len(y)),y-1,(y-1)*u,1/(1+np.exp(-k*(u-h))),v**q]
 if label=='logisticdamp': k,h,q=theta; return np.c_[np.ones(len(y)),u,u*u,v**q,-(y-1)/(1+np.exp(k*(u-h)))]
 if label=='expboth': k,q,h=theta;return np.c_[np.ones(len(y)),np.exp(k*u),v**q,-(y-1)*np.exp(h*u)]
config={'expdamp':([1,2],[-8,.2],[8,5]),'powerdamp':([2,2,1],[-5,.2,.9],[8,5,1.1]),'rationaldamp':([1,2],[0,.2],[20,5]),'sigmoidforcing':([5,1,2],[.1,0,.2],[30,2,5]),'logisticdamp':([5,1,2],[.1,0,.2],[30,2,5]),'expboth':([1,2,-1],[-5,.2,-5],[5,5,5])}
for label in families2:
 start,lo,hi=config[label]
 def residual(theta):
  X=features(theta,tr,label);c=np.linalg.lstsq(X,tr.dy,rcond=None)[0];return X@c-tr.dy.values
 opt=least_squares(residual,start,bounds=(lo,hi),max_nfev=1500,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 theta=opt.x;X=features(theta,tr,label);c=np.linalg.lstsq(X,tr.dy,rcond=None)[0]
 def f(y,u,v):
  d=pd.DataFrame({'y':[y],'x1':[u],'x2':[v]});return (features(theta,d,label)@c)[0]
 scores=[np.sqrt(np.mean((features(theta,d,label)@c-d.dy)**2)) for d in [tr,va]]
 # expensive dataframe function only do val
 roll=[np.sqrt(np.mean((rk4(f,d)[1:]-d.y.values[1:])**2)) for d in [va]]
 print(label,theta,c,'der',scores,'roll',roll)
 res.append(dict(label=label,theta=theta.tolist(),coef=c.tolist(),der=scores,roll=roll))
json.dump(res,open('structured_results.json','w'))
