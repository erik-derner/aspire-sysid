import pandas as pd, numpy as np
D=pd.read_csv('data/train.csv')
print(D.head(12).to_string(index=False));print(D.describe().to_string())
for k,g in D.groupby('trajectory'):
 p=np.unwrap(g.phi.to_numpy());dx=np.diff(g.x);dy=np.diff(g.y);dp=np.diff(p);vf=g.v_f.to_numpy()[:-1];va=g.v_a.to_numpy()[:-1];ph=p[:-1]
 print('\nTRAJ',k,'first',g.iloc[0].to_dict(),'last',g.iloc[-1].to_dict())
 print('vf unique',g.v_f.unique(),'va unique',g.v_a.unique())
 for name,v in [('dx',dx),('dy',dy),('dp',dp),('df',dx*np.cos(ph)+dy*np.sin(ph)),('dl',-dx*np.sin(ph)+dy*np.cos(ph))]:
  print(name,'mean/std',np.mean(v),np.std(v),'lag1',np.corrcoef(v[:-1],v[1:])[0,1])
 print('phi gain',np.linalg.lstsq(np.c_[.2*va,np.ones(len(va))],dp,rcond=None)[0])
print('missing',D.isna().sum().to_dict())
