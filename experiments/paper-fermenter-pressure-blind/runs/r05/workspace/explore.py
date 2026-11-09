import numpy as np,pandas as pd,json
from sklearn.preprocessing import PolynomialFeatures
from scipy.stats import pearsonr
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
# fit normalized polynomial up to degree 6, ridge stabilizes for high degree
S=np.array([1,60,20]); C=np.array([1,0,0])
A=(tr[['y','x1','x2']].values-C)/S; B=(va[['y','x1','x2']].values-C)/S
out=[]
for deg in range(1,7):
 p=PolynomialFeatures(deg);X=p.fit_transform(A);V=p.transform(B)
 for reg in [0,1e-6,1e-3,.1,10]:
  sd=np.sqrt(np.mean(X**2,axis=0));Z=X/sd
  c=np.linalg.lstsq(np.vstack([Z,np.sqrt(reg)*np.eye(Z.shape[1])]),np.r_[tr.dy,np.zeros(Z.shape[1])],rcond=None)[0]/sd
  train=np.sqrt(np.mean((X@c-tr.dy)**2));val=np.sqrt(np.mean((V@c-va.dy)**2))
  print('poly',deg,reg,train,val)
  out.append(dict(deg=deg,reg=reg,train=train,val=val,powers=p.powers_.tolist(),coef=c.tolist()))
# transformed feedback guesses
for state in [lambda y:y,lambda y:y**2,lambda y:np.sqrt(np.maximum(y-0.99,1e-6)),lambda y:np.log(np.maximum(y-0.99,1e-6)),lambda y:np.log(np.maximum(y-1,1e-6)),lambda y:(np.maximum(y-.99,1e-6))**.2]:
 for deg in [1,2,3,4,5]:
  p=PolynomialFeatures(deg);U=p.fit_transform(tr[['x1','x2']].values/[60,20]);W=p.transform(va[['x1','x2']].values/[60,20])
  X=np.c_[U,state(tr.y.values)];V=np.c_[W,state(va.y.values)]
  c=np.linalg.lstsq(X,tr.dy,rcond=None)[0]
  print('state transformed',state(np.array([1.1,1.5])),deg,np.sqrt(np.mean((X@c-tr.dy)**2)),np.sqrt(np.mean((V@c-va.dy)**2)))
json.dump(out,open('poly_results.json','w'))
# temporal discrepancy samples
for d in [tr,va]:
 delta=np.diff(d.y)/5-d.dy.values[:-1];idx=np.argsort(abs(delta))[-15:]
 print('delta outliers',list(zip(idx.tolist(),delta[idx].tolist())))
 print('unique near min', d.nsmallest(20,'y').to_string(index=False))
