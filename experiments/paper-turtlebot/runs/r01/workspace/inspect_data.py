import pandas as pd, numpy as np
D=pd.read_csv('data/train.csv')
print(D.head(12).to_string(index=False)); print(D.describe().to_string())
for tid,g in D.groupby('trajectory'):
 print('\nTRAJECTORY',tid,'n',len(g)); print('initial final',g.iloc[[0,-1]].to_string(index=False))
 p=np.unwrap(g.phi.to_numpy()); dx=np.diff(g.x);dy=np.diff(g.y);dp=np.diff(p)
 print('diff stats',np.quantile(dx,[0,.1,.5,.9,1]),np.quantile(dy,[0,.1,.5,.9,1]),np.quantile(dp,[0,.1,.5,.9,1]))
 print('commands by block',g.iloc[::5][['v_f','v_a']].to_numpy())
 print('OLS dp commands',np.linalg.lstsq(np.c_[g.v_a.to_numpy()[:-1]*.2,np.ones(len(dp))*.2],dp,rcond=None)[0])
 print('sum dp',sum(dp),'sum input',sum(g.v_a.to_numpy()[:-1]*.2))
np.savez('data/arrays.npz',**{f't{int(t)}':g[['x','y','phi','v_f','v_a']].to_numpy() for t,g in D.groupby('trajectory')})
