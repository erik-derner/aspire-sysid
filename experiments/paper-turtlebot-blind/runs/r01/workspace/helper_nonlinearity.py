import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); rows=[]
for tr,g in D.groupby('trajectory'):
 a=g.to_numpy(); cols=list(g.columns)
 for k in range(len(g)-1):
  z=g.iloc[k]; n=g.iloc[k+1]; theta=z.x2; dt=np.arctan2(np.sin(n.x2-theta),np.cos(n.x2-theta)); dy=n.y-z.y; dx=n.x1-z.x1
  mid=theta+dt/2
  rows.append(dict(tr=tr,k=k,phase=k%5,u=z.x3,w=z.x4,theta=theta,dtheta=dt,dy=dy,dx=dx,forward=dy*np.cos(theta)+dx*np.sin(theta),lateral=-dy*np.sin(theta)+dx*np.cos(theta),midforward=dy*np.cos(mid)+dx*np.sin(mid),midlateral=-dy*np.sin(mid)+dx*np.cos(mid),speed=np.hypot(dy,dx)))
P=pd.DataFrame(rows); P.to_csv('helper_pairs.csv',index=False)
np.set_printoptions(precision=9,suppress=True)
def reg(label,X,y,mask=None):
 if mask is None:mask=np.ones(len(P),bool)
 b=np.linalg.lstsq(X[mask],y[mask],rcond=None)[0]; e=y-X@b
 print(label,'coef',b,'rmse',np.sqrt(np.mean(e[mask]**2)),'allrmse',np.sqrt(np.mean(e**2)))
 for t in [1,2,3]:
  train=mask&(P.tr.values!=t);test=mask&(P.tr.values==t); bt=np.linalg.lstsq(X[train],y[train],rcond=None)[0]
  print(' hold',t,np.sqrt(np.mean((y[test]-X[test]@bt)**2)),end='')
 print()
 return b,e
u=P.u.values;w=P.w.values;t=P.dtheta.values;s=P.midforward.values
print('phase summaries');print(P.groupby('phase')[['dtheta','midforward','midlateral','lateral']].agg(['mean','std']).to_string())
for interior in [False,True]:
 mask=P.phase.values>=2 if interior else np.ones(len(P),bool)
 print('\nINTERIOR',interior,'n',mask.sum())
 for name,f in [('linear',w),('tan',np.tan(w)),('sin',np.sin(w)),('atan',np.arctan(w)),('tanh',np.tanh(w))]:
  reg('angle '+name,np.array([np.ones(len(P)),f]).T,t,mask)
  reg('angle u*'+name,np.array([np.ones(len(P)),u*f]).T,t,mask)
 reg('angle cubic',np.array([np.ones(len(P)),w,w**3]).T,t,mask)
 reg('angle cubic u',np.array([np.ones(len(P)),w,w**3,u*w,u*w**3]).T,t,mask)
 for name,f in [('linear',u),('square',u*u),('sqrt',np.sqrt(u))]:reg('step '+name,np.array([np.ones(len(P)),f]).T,s,mask)
 reg('step cubic',np.array([np.ones(len(P)),u,u*u,u**3]).T,s,mask)
 reg('step w dep',np.array([np.ones(len(P)),u,u*w*w,u*u]).T,s,mask)
print('\nblock interior means')
B=P[P.phase>=2].groupby(['tr',P.k//5]).agg(u=('u','first'),w=('w','first'),dtheta=('dtheta','mean'),step=('midforward','mean'),dtheta_sd=('dtheta','std'),step_sd=('midforward','std')).reset_index();B.to_csv('helper_blocks.csv',index=False);print(B.to_string(index=False))
