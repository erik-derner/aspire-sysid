import numpy as np,pandas as pd
from scipy.signal import savgol_filter
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
print(tr.head().to_string());print(tr.describe().to_string()); print('validation',va.describe().to_string())
for k,g in tr.groupby('trajectory',sort=False):
 print('trajectory',k,'n',len(g),'first',g.iloc[0].to_dict(),'range',[(c,round(g[c].min(),4),round(g[c].max(),4)) for c in ['y','x1','x2','dx1']])
print('correlation');print(tr.corr().to_string())
for name,d in [('train',tr),('val',va)]:
 yy=[]; xx=[]
 for k,g in d.groupby('trajectory',sort=False):
  a=g[['y','x1','x2']].values
  dy=np.gradient(a[:,0],.01); xx.append(a[2:-2]);yy.append(dy[2:-2])
 X=np.concatenate(xx);Y=np.concatenate(yy)
 for cols in [[0],[1],[0,1],[0,1,2]]:
  A=np.column_stack([np.ones(len(X)),X[:,cols]]);b=np.linalg.lstsq(A,Y,rcond=None)[0]
  print(name,'dy linear',cols,b,'rmse',np.sqrt(np.mean((A@b-Y)**2)))
 A=np.column_stack([np.ones(len(d)),d[['y','x1','x2']].values]);b=np.linalg.lstsq(A,d.dx1,rcond=None)[0]
 print(name,'dx1 linear',b,'rmse',np.sqrt(np.mean((A@b-d.dx1)**2)))
