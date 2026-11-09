import numpy as np,pandas as pd
from sklearn.preprocessing import PolynomialFeatures
D=pd.read_csv('data/train.csv'); print(D.head()); print(D.describe().to_string())
S=['y','x1','x2']; V=S+['x3','x4']
X=[];Y=[];G=[]
for g,d in D.groupby('trajectory',sort=False):
 a=d[V].values;X.extend(a[:-1]);Y.extend(a[1:,:3]-a[:-1,:3]);G.extend([g]*(len(a)-1))
X=np.array(X);Y=np.array(Y);G=np.array(G);np.savez('transitions.npz',X=X,Y=Y,G=G)
for degree in [1,2,3]:
 p=PolynomialFeatures(degree); A=p.fit_transform(X); c=np.linalg.lstsq(A,Y,rcond=None)[0]; e=Y-A@c
 print('\nDEGREE',degree,'rmse',np.sqrt(np.mean(e**2,axis=0)))
 names=p.get_feature_names_out(V)
 for j in range(3):
  inds=np.argsort(abs(c[:,j]))[::-1][:20];print(S[j],[(names[i],round(c[i,j],7)) for i in inds])
print('increments stats',pd.DataFrame(Y,columns=S).describe().to_string())
