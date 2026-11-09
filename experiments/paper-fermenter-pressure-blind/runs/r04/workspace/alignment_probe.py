import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import numpy as np,pandas as pd
from sklearn.preprocessing import PolynomialFeatures
for file in ['train','val']:
 d=pd.read_csv('data/'+file+'.csv');y=d.y.to_numpy();u=d.x1.to_numpy()/70;w=d.x2.to_numpy()/20;dy=d.dy.to_numpy();mask=np.arange(len(y)-1);mask=mask[np.abs(np.diff(y)/5-dy[:-1])<.001]
 for kind in ['raw','sqrt']:
  z=(y-1.3)/.3 if kind=='raw' else np.sqrt(np.maximum(y-.99,0))
  for shift in [0,1]:
   for degree in [1,2,3]:
    p=PolynomialFeatures(degree);F=p.fit_transform(np.array([z[mask],u[mask],w[mask+shift]]).T);c=np.linalg.lstsq(F,dy[mask],rcond=None)[0];print(file,kind,shift,degree,np.sqrt(np.mean((F@c-dy[mask])**2)))
    if shift==1 and degree==2:print(list(zip(p.powers_.tolist(),c.tolist())))
