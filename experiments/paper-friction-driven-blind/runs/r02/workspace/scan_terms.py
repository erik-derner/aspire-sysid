import numpy as np,pandas as pd
from sklearn.linear_model import ARDRegression
for file in ['train','val']:
 d=pd.read_csv('data/'+file+'.csv');y=d.y.values;v=d.x1.values;u=d.x2.values
 feats={'1':np.ones(len(d)),'sin(y)':np.sin(y),'x1':v,'x2':u,'sign(x1)':np.sign(v),'y':y,'y**3':y**3,'cos(y)-1':np.cos(y)-1,'sin(2*y)':np.sin(2*y),'y**2*x1':y*y*v,'y*x1':y*v,'cos(y)*sign(x1)':np.cos(y)*np.sign(v),'sin(y)*sign(x1)':np.sin(y)*np.sign(v),'Abs(x1)':np.abs(v),'x1*Abs(x1)':v*np.abs(v),'x2*Abs(x2)':u*np.abs(u),'y*x2':y*u,'cos(y)*x2':np.cos(y)*u,'sin(y)*x1**2':np.sin(y)*v*v}
 mask=np.abs(v)>.5
 base=['1','sin(y)','x1','x2','sign(x1)']
 X=np.column_stack([feats[n][mask] for n in base]);b=np.linalg.lstsq(X,d.dx1.values[mask],rcond=None)[0];err=d.dx1.values[mask]-X@b
 print(file,'base',b,'rmse',np.sqrt(np.mean(err*err)))
 for n in feats:
  if n in base:continue
  XX=np.column_stack([X,feats[n][mask]]);bb=np.linalg.lstsq(XX,d.dx1.values[mask],rcond=None)[0];e=d.dx1.values[mask]-XX@bb
  print(n,'coef',bb[-1],'rmse',np.sqrt(np.mean(e*e)))
 names=list(feats);A=np.column_stack([feats[n][mask] for n in names]);s=np.std(A,axis=0);s[0]=1
 ar=ARDRegression(fit_intercept=False).fit(A/s,d.dx1.values[mask]);print('ARD',list(zip(names,ar.coef_/s)))
