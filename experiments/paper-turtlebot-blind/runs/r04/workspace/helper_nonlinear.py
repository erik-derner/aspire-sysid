import numpy as np,pandas as pd
from scipy.optimize import least_squares
S=np.load('helper_kinematic_arrays.npz')['S'];u,w=S[:,3:5].T;up,wp=S[:,5:7].T;dp=S[:,7:9];dt=S[:,9];th=S[:,2];forward=(dp[:,0]+1j*dp[:,1])*np.exp(-1j*th);n=len(S)
phase=np.tile(np.arange(149)%5,3);sel=phase>=2
print('selected n',sel.sum())
features={'linear':[np.ones(n),u,w],'yawpoly':[np.ones(n),w,w**3,u*w,u**2*w,np.sign(w),np.sign(w)*u],'wheels':[np.ones(n),u,w,np.abs(u+w*.1),np.abs(u-w*.1)],'yawabs':[np.ones(n),w,w*np.abs(w),w*u,np.sign(w)*np.maximum(.08-np.abs(u),0)]}
for target,name in [(forward.real,'forward'),(dt,'theta')]:
 for family,ff in features.items():
  F=np.array(ff).T;c=np.linalg.lstsq(F[sel],target[sel],rcond=None)[0];r=target-F@c;print(name,family,c,'steady_rmse',np.sqrt(np.mean(r[sel]**2)),'all',np.sqrt(np.mean(r**2)))
for target,name in [(forward.real,'forward'),(dt,'theta')]:
 print(name,'trajectory gain')
 for tid in range(3):
  mask=sel&(np.arange(n)//149==tid);F=np.c_[np.ones(n),u,w];c=np.linalg.lstsq(F[mask],target[mask],rcond=None)[0];r=target-F@c;print(tid+1,c,np.sqrt(np.mean(r[mask]**2)))
# dead-zone wheel model commands u +/- width*w; wheel deadzone output sign(cmd)*max(abs(cmd)-d,0)
def calc(p):
 width,d,g,b=p;left=u-width*w;right=u+width*w;left=np.sign(left)*np.maximum(abs(left)-d,0);right=np.sign(right)*np.maximum(abs(right)-d,0);return np.c_[g*(left+right)/2, b*(right-left)]
Y=np.c_[forward.real,dt]
res=least_squares(lambda p:(calc(p)[sel]-Y[sel]).ravel(),[.08,.02,.18,1.],bounds=([.001,0,0,0],[1,1,3,10]));print('wheel deadzone',res.x,'steady rmse',np.sqrt(np.mean((calc(res.x)[sel]-Y[sel])**2,axis=0)),'all rmse',np.sqrt(np.mean((calc(res.x)-Y)**2,axis=0)))
# instantaneous local direction versus observed theta increment
for mask,label in [(np.ones(n,dtype=bool),'all'),(sel,'steady')]:
 c=np.linalg.lstsq(np.c_[np.ones(n),forward.real*dt][mask],forward.imag[mask],rcond=None)[0];r=forward.imag-(c[0]+c[1]*forward.real*dt);print('midpoint',label,c,'rmse',np.sqrt(np.mean(r[mask]**2)))
# phase RMSE and mean
for phaseval in range(5):
 mask=phase==phaseval
 print('phase',phaseval,'n',mask.sum(),'forward/u median',np.median(forward.real[mask]/u[mask]),'theta residual rms',np.sqrt(np.mean((dt[mask]-.133333*w[mask])**2)))
# quantify angle grid
ang=pd.read_csv('data/train.csv')['x2'].values;grid=np.pi/18000;err=ang/grid-np.round(ang/grid);print('angle grid step',grid,'rms grid error',np.sqrt(np.mean(err**2)),'max',max(abs(err)))
