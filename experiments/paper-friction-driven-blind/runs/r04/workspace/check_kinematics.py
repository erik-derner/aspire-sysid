import pandas as pd,numpy as np
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv');r=[]
 for k,g in d.groupby('trajectory'):
  y,v,u=g[['y','x1','x2']].to_numpy().T
  er=(y[2:]-y[:-2])/.02-v[1:-1]
  print(fn,k,'central velocity rms',np.sqrt(np.mean(er**2)),'max',max(abs(er)))
  r.extend(er)
 print('all',np.sqrt(np.mean(np.array(r)**2)))
