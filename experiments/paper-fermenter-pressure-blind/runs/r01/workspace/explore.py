import numpy as np,pandas as pd
from sklearn.preprocessing import PolynomialFeatures
for file in ['train','val']:
 d=pd.read_csv('data/'+file+'.csv');print(file,d.describe().to_string());print(d.head(12).to_string());print('corr',d.corr().to_string())
 z=d.y.to_numpy();dy=d.dy.to_numpy();print('increment derivative',np.sqrt(np.mean(((z[1:]-z[:-1])/5-dy[:-1])**2)), np.corrcoef((z[1:]-z[:-1])/5,dy[:-1])[0,1])
a=pd.read_csv('data/train.csv');b=pd.read_csv('data/val.csv')
for deg in [1,2,3,4,5]:
 p=PolynomialFeatures(deg);X=p.fit_transform(a[['y','x1','x2']]);V=p.transform(b[['y','x1','x2']]);c=np.linalg.lstsq(X,a.dy,rcond=None)[0];print('degree',deg,'train',np.sqrt(np.mean((X@c-a.dy)**2)),'val',np.sqrt(np.mean((V@c-b.dy)**2)))
 if deg<=2: print(list(zip(p.get_feature_names_out(),c)))
