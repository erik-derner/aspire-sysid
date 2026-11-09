import pandas as pd,numpy as np
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv'); print(fn,d.shape); print(d.describe().to_string()); print(d.head(12).to_string(index=False)); print('valve unique',np.sort(d.valve.unique())); print('flow unique',np.sort(d.flow.unique())[:80]); print('correlations',d.corr().to_string());
 d.to_pickle(fn+'.pkl')
