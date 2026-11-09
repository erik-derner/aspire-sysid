import numpy as np, pandas as pd
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv');print('\n',fn,d.shape,d.columns.tolist());print(d.describe().to_string());
 for k,g in d.groupby('trajectory',sort=False):
  print(k,len(g),'start',g.iloc[0].to_dict(),'endtheta',g.theta.iloc[-1], 'urange',g.u.min(),g.u.max(),'theta',g.theta.min(),g.theta.max(),'omega',g.omega.min(),g.omega.max(),'zeros',sum(abs(g.omega)<.01))
 d.to_pickle(fn+'.pkl')
print(pd.read_csv('data/train.csv').head(20).to_string(index=False))
