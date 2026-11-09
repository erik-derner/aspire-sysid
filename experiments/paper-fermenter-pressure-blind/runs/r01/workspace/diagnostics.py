import numpy as np,pandas as pd,json
from sklearn.preprocessing import PolynomialFeatures
for label in ['train','val']:
 d=pd.read_csv('data/'+label+'.csv');r=json.load(open('poly_results.json'))[4];c=np.array(r['c']);p=PolynomialFeatures(3);X=p.fit_transform(np.c_[d.y,d.x1/100,d.x2/30]);e=d.dy-X@c
 print(label,'residual mean/std',e.mean(),e.std(),'quantiles',np.quantile(e,[0,.01,.1,.5,.9,.99,1]))
 for col in ['y','x1','x2','dy']:
  for lag in [-2,-1,0,1,2]:
   v=d[col].shift(lag);print(col,lag,round(e.corr(v),4))
 for col in ['x1','x2']:
  print('res corr diff',col,e.corr(d[col].diff()),e.corr(d[col].diff().shift(-1)))
 print('largest',d.assign(res=e).iloc[np.argsort(np.abs(e))[-20:]].to_string())
 print('bins',pd.DataFrame({'e':e,'x':pd.qcut(d.x1,10)}).groupby('x',observed=True).e.agg(['mean','std']).to_string())
