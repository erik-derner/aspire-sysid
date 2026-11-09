import pandas as pd,numpy as np
for f in ['train','val']:
 a=pd.read_csv('data/'+f+'.csv')
 print(f,a.describe().to_string());print(a.head(20).to_string(index=False))
 print('CORRELATIONS',a.corr().to_string())
 d=np.diff(a.y)/5
 print('diff comparison',np.corrcoef(d,a.dy[:-1])[0,1],np.sqrt(np.mean((d-a.dy[:-1])**2)))
 print('input unique',a.x1.nunique(),a.x2.nunique())
 print('input step summaries',np.quantile(np.diff(a.x1),[0,.1,.5,.9,1]),np.quantile(np.diff(a.x2),[0,.1,.5,.9,1]))
