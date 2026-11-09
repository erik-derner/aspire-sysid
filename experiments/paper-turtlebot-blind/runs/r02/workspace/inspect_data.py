import pandas as pd,numpy as np
D=pd.read_csv('data/train.csv');print(D.head(12).to_string(index=False));print(D.groupby('trajectory').agg(['min','max','mean','std']).to_string())
for t,g in D.groupby('trajectory'):
 s=g[['y','x1','x2']].values; ds=np.diff(s,axis=0);print('trajectory',t,'increment stats',np.min(ds,axis=0),np.max(ds,axis=0),np.std(ds,axis=0));print('head states',s[:5]);print('tail states',s[-5:])
X=np.vstack([g[['y','x1','x2','x3','x4']].values[:-1] for _,g in D.groupby('trajectory')]);Y=np.vstack([g[['y','x1','x2']].values[1:] for _,g in D.groupby('trajectory')]);A=np.column_stack([np.ones(len(X)),X]);C=np.linalg.lstsq(A,Y-X[:,:3],rcond=None)[0];print('affine increment C',C);print('rms residual',np.sqrt(np.mean((Y-X[:,:3]-A@C)**2,axis=0)));print('correlation',D.corr().to_string())
