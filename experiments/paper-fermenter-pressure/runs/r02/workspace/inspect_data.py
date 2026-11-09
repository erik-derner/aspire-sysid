import pandas as pd, numpy as np
for name in ['train','val']:
 d=pd.read_csv('data/'+name+'.csv'); print('\n',name,d.shape); print(d.describe().to_string()); print('head\n',d.head(15).to_string());print('tail\n',d.tail().to_string())
 for c in ['valve','flow']:
  print(c,'unique',d[c].nunique(),'levels',np.unique(np.round(d[c],3))[:150]);print('changes',np.sum(np.abs(np.diff(d[c]))>.1))
 print('corr\n',d.corr().to_string());print('pressure delta RMSE dp',np.sqrt(np.mean((np.diff(d.p)/5-d.dp[:-1])**2)))
 # output means by valve rounded levels
 d['vbin']=pd.cut(d.valve,[-1,10,20,30,40,50,60,70,80,90,100.01]); print(d.groupby('vbin',observed=True)[['p','flow','dp']].agg(['mean','min','max','count']).to_string())
