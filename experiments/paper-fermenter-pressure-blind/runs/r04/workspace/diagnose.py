import pandas as pd,numpy as np,json
from sklearn.ensemble import HistGradientBoostingRegressor,ExtraTreesRegressor
A=pd.read_csv('data/train.csv');V=pd.read_csv('data/val.csv')
for depth in [3,5,8,None]:
 m=HistGradientBoostingRegressor(max_iter=350,max_depth=depth,l2_regularization=.01,min_samples_leaf=20).fit(A[['y','x1','x2']],A.dy)
 r=V.dy.values-m.predict(V[['y','x1','x2']]);print(depth,np.sqrt(np.mean(r*r)), 'acf',np.corrcoef(r[:-1],r[1:])[0,1],flush=True)
q=next(q for q in json.load(open('poly_results.json')) if q['kind']=='raw' and q['degree']==3)
def pred(d):
 z=(d.y.values-1.3)/.3;u=d.x1.values/70;w=d.x2.values/20
 return sum(c*z**i*u**j*w**k for c,(i,j,k) in zip(q['coefficients'],q['powers']))
for d in [A,V]:
 r=d.dy.values-pred(d);print('polynomial residual rmse',np.sqrt(np.mean(r*r)),'acf',[np.corrcoef(r[:-lag],r[lag:])[0,1] for lag in [1,2,3,5,10]])
 for col in ['x1','x2']:
  print(col,'corr du',np.corrcoef(r[1:],np.diff(d[col]))[0,1], 'corr next du',np.corrcoef(r[:-1],np.diff(d[col]))[0,1])
 print('worst',d.iloc[np.argsort(abs(r))[-10:]].assign(res=r[np.argsort(abs(r))[-10:]]).to_string())
