import pandas as pd, numpy as np
from scipy.signal import savgol_filter
for file in ['train','val']:
 d=pd.read_csv('data/'+file+'.csv'); print(file,d.shape,d.head().to_string(),d.describe().to_string())
 for k,g in d.groupby('trajectory',sort=False):
  print(k,len(g),{c:(round(g[c].min(),5),round(g[c].max(),5)) for c in ['y','x1','x2','dx1']})
  dy=np.gradient(g.y,.01); dx=np.gradient(g.x1,.01)
  print('derivatives: dy-x1 rmse',np.sqrt(np.mean((dy-g.x1)**2)), 'dx-dx1 rmse',np.sqrt(np.mean((dx-g.dx1)**2)))
