import numpy as np,pandas as pd
from scipy.optimize import least_squares
P=pd.read_csv('helper_pairs.csv'); B=pd.read_csv('helper_blocks.csv');np.set_printoptions(precision=10,suppress=True)
forms={'linear':(lambda p,x:p[0]+p[1]*x,[0,.14]),'cubic':(lambda p,x:p[0]+p[1]*x+p[2]*x**3,[0,.12,.035]),'deadzone':(lambda p,x:p[0]+p[1]*np.sign(x)*np.maximum(abs(x)-abs(p[2]),0),[0,.17,.1]),'power':(lambda p,x:p[0]+p[1]*np.sign(x)*abs(x)**p[2],[0,.15,1.3]),'tan_scaled':(lambda p,x:p[0]+p[1]*np.tan(p[2]*x),[0,.15,.85]),'tanh_scaled':(lambda p,x:p[0]+p[1]*np.tanh(p[2]*x),[0,.15,1]),'linear_step':(lambda p,x:p[0]+p[1]*x,[0,.167]),'deadzone_step':(lambda p,x:p[0]+p[1]*np.maximum(x-abs(p[2]),0),[0,.167,.005])}
for target in ['dtheta','step']:
 names=['linear','cubic','deadzone','power','tan_scaled','tanh_scaled'] if target=='dtheta' else ['linear_step','deadzone_step']; inp='w' if target=='dtheta' else 'u'
 print('\nTARGET',target)
 for name in names:
  fn,p0=forms[name];x=B[inp].values;y=B[target].values
  fit=least_squares(lambda p:fn(p,x)-y,p0,max_nfev=5000);pred=fn(fit.x,x);err=y-pred
  print(name,'p',fit.x,'fit_rmse',np.sqrt(np.mean(err**2)),'held',end=' ')
  for tr in [1,2,3]:
   m=B.tr.values!=tr;f=least_squares(lambda p:fn(p,x[m])-y[m],p0,max_nfev=5000);print(np.sqrt(np.mean((fn(f.x,x[~m])-y[~m])**2)),end=' ')
  print('resid lag1',np.corrcoef(np.concatenate([err[B.tr==t][:-1] for t in [1,2,3]]),np.concatenate([err[B.tr==t][1:] for t in [1,2,3]]))[0,1])
  if name in ['linear','deadzone','linear_step']:
   for tr in [1,2,3]:
    e=err[B.tr==tr];print('tr',tr,'first10,last10means',e[:10].mean(),e[-10:].mean())
 # differences of neighboring block interior means reduces slow offsets
 x=B[inp].values;y=B[target].values;m=(B.tr.values[1:]==B.tr.values[:-1]);dx=x[1:][m]-x[:-1][m];dy=y[1:][m]-y[:-1][m]
 for name in names:
  fn,p0=forms[name];res=lambda p: (fn(p,x[1:])-fn(p,x[:-1]))[m]-dy
  f=least_squares(res,p0,max_nfev=5000);print('differenced',name,'p',f.x,'rmse',np.sqrt(np.mean(res(f.x)**2)))
print('\nphase errors, simple gain from differenced blocks .167 u and .166 deadzone .1')
for target,pred in [('dtheta',.166*np.sign(P.w)*np.maximum(abs(P.w)-.1,0)),('midforward',.167*P.u)]:
 e=P[target]-pred
 print(target)
 for phase in range(5):
  v=e[P.phase==phase]; print('phase',phase,'n',len(v),'rmse',np.sqrt(np.mean(v*v)),'bias',v.mean())
print('midlateral rmse',np.sqrt(np.mean(P.midlateral**2)),'initial heading lateral rmse',np.sqrt(np.mean(P.lateral**2)))
