import pandas as pd, numpy as np
for f in ['train','val']:
 d=pd.read_csv('data/'+f+'.csv'); print(f,d.columns, d.describe().to_string())
 for k,g in d.groupby('trajectory',sort=False):
  print(k,len(g),'initial',g.iloc[0].to_dict(),'ranges',[(v,round(g[v].min(),4),round(g[v].max(),4)) for v in ['theta','omega','u','domega']], 'zero',sum(g.omega==0),'last',g.iloc[-1].to_dict())
