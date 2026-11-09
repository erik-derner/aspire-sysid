import pandas as pd, numpy as np
from scipy.signal import savgol_filter
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv'); print(fn,d.shape,d.columns.tolist()); print(d.describe().to_string());
 for k,g in d.groupby('trajectory',sort=False):
  a=g[['y','x1','x2','dx1']].values
  dy=np.gradient(a[:,0],.01)
  print(k,len(g),'first',a[0],'last',a[-1], 'ranges',np.ptp(a,axis=0),'dy range',dy.min(),dy.max(), 'dy-x1 rmse',np.sqrt(np.mean((dy-a[:,1])**2)))
 print(d.head(10).to_string(index=False))
