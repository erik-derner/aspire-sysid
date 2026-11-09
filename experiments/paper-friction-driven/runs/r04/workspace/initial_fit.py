import numpy as np, pandas as pd
from scipy.optimize import lsq_linear
D=pd.read_csv('data/train.csv');v=pd.read_csv('data/val.csv')
for maskname,mask in [('all',np.ones(len(D),bool)),('moving',abs(D.omega)>.8),('fast',abs(D.omega)>2)]:
 d=D[mask];t=d.theta.to_numpy();w=d.omega.to_numpy();u=d.u.to_numpy();y=d.domega.to_numpy()
 for grav in ['sin','linear','harmonic']:
  X=np.column_stack([u,-w,-np.sin(t) if grav!='linear' else -t,-np.sign(w)])
  if grav=='harmonic': X=np.column_stack([X,-np.sin(2*t)])
  p=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@p
  print(maskname,grav,p,'RMSE',np.sqrt(np.mean(r*r)))
  if maskname=='moving' and grav=='sin':
   print('Residual correlations',[(k,np.corrcoef(r,z)[0,1]) for k,z in [('u',u),('u3',u**3),('w2',w*abs(w)),('sin2',np.sin(2*t)),('theta',t),('absw',abs(w))]])
   for key,z,bins in [('w',w,[-25,-10,-5,-2,-.8,.8,2,5,10,25]),('u',u,[-5,-3,-2,-1,0,1,2,3,5]),('theta',t,[-3,-2,-1,-.5,0,.5,1,2,3])]:
    print('Bins',key,[(lo,hi,int(sum((z>=lo)&(z<hi))),round(float(np.mean(r[(z>=lo)&(z<hi)])),2)) for lo,hi in zip(bins[:-1],bins[1:]) if sum((z>=lo)&(z<hi))])
