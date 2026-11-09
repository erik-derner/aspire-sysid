import pandas as pd, numpy as np
for name in ['train','val']:
 d=pd.read_csv('data/'+name+'.csv'); print(name,d.shape); print(d.describe().to_string()); print(d.head(12).to_string()); print('corr',d.corr().to_string());
 for c in d: print(c,'unique',d[c].nunique())
 print('finite differences vs dy',np.corrcoef(np.diff(d.y)/5,d.dy[:-1])[0,1], np.sqrt(np.mean((np.diff(d.y)/5-d.dy[:-1])**2)))
