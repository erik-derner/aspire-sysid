import pandas as pd, numpy as np
for path in ['data/train.csv','data/val.csv']:
 d=pd.read_csv(path);print('\n',path,d.shape,d.columns.tolist());print(d.describe().to_string())
 for k,g in d.groupby('trajectory',sort=False):
  print(k,len(g),'initial',g.iloc[0].to_dict(),'end',g.iloc[-1].to_dict(),'range',g[['theta','omega','u','domega']].agg(['min','max']).to_dict(),'rest',sum(abs(g.omega)<.05))
 print(d.head(15).to_string(index=False))
