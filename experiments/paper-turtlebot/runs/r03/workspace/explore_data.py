import pandas as pd,numpy as np
from scipy.stats import pearsonr
D=pd.read_csv('data/train.csv'); print(D.head(12).to_string(index=False));print(D.groupby('trajectory').agg(['min','max','mean','std']).to_string())
for tr,d in D.groupby('trajectory'):
 p=np.unwrap(d.phi.to_numpy()); u=d[['v_f','v_a']].to_numpy(); dx=np.diff(d.x);dy=np.diff(d.y);dp=np.diff(p)
 print('\nTR',tr,'start',d.iloc[0].to_dict(),'end',d.iloc[-1].to_dict())
 print('input first 20',u[:20]); print('dp stats',np.quantile(dp,[0,.1,.5,.9,1]),'noise vs u',np.std(dp-.2*u[:-1,1]));print('trans residual', np.std(dx-.2*u[:-1,0]*np.cos(p[:-1])),np.std(dy-.2*u[:-1,0]*np.sin(p[:-1])))
 print('ang command LS',np.linalg.lstsq(np.c_[u[:-1,1],np.ones(149)],dp,rcond=None)[0]);print('head first 20',p[:20])
np.savez('inspect_data.npz',dummy=0)
