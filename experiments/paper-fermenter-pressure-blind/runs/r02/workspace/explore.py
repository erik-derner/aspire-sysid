import numpy as np,pandas as pd
from scipy import signal
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv');print(fn,d.shape);print(d.describe().to_string());print('corr',d.corr().to_string());print(d.head(15).to_string(index=False))
 print('diff dy RMSE',np.sqrt(np.mean((np.diff(d.y)/5-d.dy.values[:-1])**2)))
 print('unique inputs',d.x1.nunique(),d.x2.nunique());print('dy quantiles',d.dy.quantile([0,.01,.1,.5,.9,.99,1]).to_dict())
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(4,1,figsize=(12,10))
for f in ['train','val']:
 d=pd.read_csv('data/'+f+'.csv')
 for a,c in zip(ax,d.columns):a.plot(d[c],label=f);a.set_ylabel(c);a.legend()
fig.tight_layout();fig.savefig('explore.png')
