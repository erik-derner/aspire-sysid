import pandas as pd, numpy as np
from sklearn.preprocessing import PolynomialFeatures
D=pd.read_csv('data/train.csv'); print(D.head()); print(D.describe().to_string())
Xs=[]; Ys=[]
for t,g in D.groupby('trajectory',sort=False):
 print('\nTRAJ',t,'first last',g.iloc[[0,-1]].to_string(index=False))
 Xs.append(g[['y','x1','x2','x3','x4']].values[:-1]); Ys.append(g[['y','x1','x2']].values[1:])
X=np.vstack(Xs); Y=np.vstack(Ys); delta=Y-X[:,:3]
np.savez('transitions.npz',X=X,Y=Y)
for degree in [1,2,3]:
 p=PolynomialFeatures(degree); F=p.fit_transform(X); coef=np.linalg.lstsq(F,delta,rcond=None)[0]; res=delta-F@coef
 print('\nDEG',degree,'RMSE',np.sqrt(np.mean(res**2,axis=0)))
 for j in range(3):
  ids=np.argsort(abs(coef[:,j]))[::-1][:20]; print('output',j,[(p.get_feature_names_out(['y','x1','x2','x3','x4'])[i],round(coef[i,j],8)) for i in ids])
print('delta std',delta.std(axis=0)); print('corr',pd.DataFrame(np.hstack([X,delta]),columns=['y','x1','x2','x3','x4','dy','dx1','dx2']).corr().to_string())
