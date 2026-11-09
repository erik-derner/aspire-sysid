import pandas as pd, numpy as np
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv');print(fn,d.head(),d.describe(),sep='\n')
 for k,g in d.groupby('trajectory',sort=False):
  a=g[['y','x1','x2','dx1']].to_numpy();dy=np.diff(a[:,0])/.01
  print(k,len(g),'start',a[0],'range',a.min(0),a.max(0),'dy',dy.min(),dy.max(),'corr dy x1',np.corrcoef(dy,a[:-1,1])[0,1])
