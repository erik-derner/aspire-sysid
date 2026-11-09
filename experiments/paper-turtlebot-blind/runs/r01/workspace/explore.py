import numpy as np,pandas as pd
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
D=pd.read_csv('data/train.csv');print(D.describe().to_string()); print(D.head(12).to_string())
cols=['y','x1','x2','x3','x4'];X=[];Y=[];G=[]
for g,d in D.groupby('trajectory',sort=False):
 x=d[cols].to_numpy();X.append(x[:-1]);Y.append(x[1:,:3]);G.extend([g]*(len(x)-1))
X=np.vstack(X);Y=np.vstack(Y);G=np.array(G);np.savez('pairs.npz',X=X,Y=Y,G=G)
for j in range(3):
 print('output',cols[j], 'increment',np.quantile(Y[:,j]-X[:,j],[0,.01,.5,.99,1]))
for deg in [1,2,3]:
 p=PolynomialFeatures(deg);F=p.fit_transform(X); coef=np.linalg.lstsq(F,Y-X[:,:3],rcond=None)[0];err=F@coef-(Y-X[:,:3]);print('degree',deg,'rmse',np.sqrt(np.mean(err**2,axis=0)),'cond',np.linalg.cond(F))
 names=p.get_feature_names_out(cols)
 for j in range(3):
  ids=np.argsort(abs(coef[:,j]))[-15:][::-1];print(cols[j],[(names[i],round(coef[i,j],8)) for i in ids])
 print('loo',end=' ')
 for g in np.unique(G):
  c=np.linalg.lstsq(F[G!=g],(Y-X[:,:3])[G!=g],rcond=None)[0];print(g,np.sqrt(np.mean((F[G==g]@c-(Y-X[:,:3])[G==g])**2,axis=0)),end='; ')
 print()
