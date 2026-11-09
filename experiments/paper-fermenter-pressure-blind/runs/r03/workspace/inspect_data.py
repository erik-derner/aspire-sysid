import numpy as np, pandas as pd
from pathlib import Path
for f in ['train','val']:
 d=pd.read_csv('data/'+f+'.csv'); print(f,d.shape);print(d.describe().to_string());print(d.head(12).to_string());print('corr', d.corr().to_string())
 y=d.y.to_numpy();dy=d.dy.to_numpy(); step=np.diff(y)/5
 print('finite difference vs dy: rmse forward',np.sqrt(np.mean((step-dy[:-1])**2)),'back',np.sqrt(np.mean((step-dy[1:])**2)))
 print('input changes',[(x,len(np.unique(d[x])), np.sum(np.diff(d[x])!=0)) for x in ['x1','x2']])
 print('last',d.tail().to_string())
