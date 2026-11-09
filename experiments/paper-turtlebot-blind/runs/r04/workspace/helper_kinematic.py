import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');S=[]
for tid,g in D.groupby('trajectory'):
 a=g[['y','x1','x2','x3','x4']].values;dp=np.diff(a[:,:2],axis=0);dt=np.angle(np.exp(1j*np.diff(a[:,2])));z=dp[:,0]+1j*dp[:,1]; local=z*np.exp(-1j*a[:-1,2]);print('\ntraj',tid,'first40: k,u,w,local_real,local_imag,dtheta')
 for k in range(35):print(k,*np.round([a[k,3],a[k,4],local[k].real,local[k].imag,dt[k]],7))
 old=np.r_[a[0,3:5][None,:],a[:-2,3:5]];S.append(np.c_[a[:-1],old,dp,dt])
S=np.vstack(S);a=S[:,:5];u=a[:,3];w=a[:,4];up=S[:,5];wp=S[:,6];dp=S[:,7:9];dt=S[:,9];th=a[:,2];local=(dp[:,0]+1j*dp[:,1])*np.exp(-1j*th)
for target,nm in [(local.real,'forward'),(local.imag,'side'),(dt,'theta')]:
 for names,F in [('current',np.c_[np.ones(len(a)),u,w]),('current_previous',np.c_[np.ones(len(a)),u,w,up,wp]),('headingonly',np.c_[np.ones(len(a)),w,wp]),('inputcubic',np.c_[np.ones(len(a)),w,w**3,wp,wp**3])]:
  coef=np.linalg.lstsq(F,target,rcond=None)[0];r=target-F@coef;print(nm,names,coef,'RMSE',np.sqrt(np.mean(r*r)),'max',max(abs(r)))
# fitted arc: dx= gain*u*cos(theta + frac*gainw*w), dy corresponding
for old in [False,True]:
 def fun(p):
  uu=p[0]*u+(p[3]*up if old else 0);dw=p[1]*w+(p[4]*wp if old else 0); pred=np.c_[uu*np.cos(th+p[2]*dw),uu*np.sin(th+p[2]*dw),dw];return (pred-np.c_[dp,dt]).ravel()
 p0=[.16,.133,.5,0,0] if old else [.16,.133,.5];res=least_squares(fun,p0); rr=fun(res.x).reshape(-1,3);print('arc old',old,'params',res.x,'RMSE',np.sqrt(np.mean(rr*rr,axis=0)))
for j in range(3):
 resid=[local.real-.1666667*u, local.imag,dt-.1333333*w][j];print('resid',j,'change RMSE',np.sqrt(np.mean(resid[(u!=up)|(w!=wp)]**2)),'steady RMSE',np.sqrt(np.mean(resid[(u==up)&(w==wp)]**2)))
np.savez('helper_kinematic_arrays.npz',S=S)
