import numpy as np, pandas as pd
for f in ['train','val']:
 d=pd.read_csv('data/'+f+'.csv'); print('\n',f,d.shape,d.describe().to_string()); print(d.head(15).to_string(index=False));
 for col in ['valve','flow']:
  print(col,'unique',d[col].nunique(),'quantiles',np.quantile(d[col],[0,.01,.1,.25,.5,.75,.9,.99,1])); print(d[col].value_counts().head(25).to_string())
 print('dp correlation forward difference',np.corrcoef(d.dp[:-1],np.diff(d.p)/5)[0,1]);print('dp corr backward difference',np.corrcoef(d.dp[1:],np.diff(d.p)/5)[0,1]);
 print('Input changed rows:',np.where((np.abs(np.diff(d.valve))>1)|(np.abs(np.diff(d.flow))>1))[0][:100]);
 print('mean p by valve bins',d.groupby(pd.cut(d.valve,10),observed=True).p.agg(['min','mean','max','count']).to_string())
