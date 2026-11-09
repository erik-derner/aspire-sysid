import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); dt=0.2
rows=[]
for tr,g in D.groupby('trajectory'):
 g=g.reset_index(drop=True); p=np.unwrap(g.phi.values); dx=np.diff(g.x);dy=np.diff(g.y);dp=np.diff(p); phi=p[:-1]
 h=phi+dp/2
 f=(dx*np.cos(h)+dy*np.sin(h))/dt; lat=(-dx*np.sin(h)+dy*np.cos(h))/dt
 for k in range(len(g)-1):
  rows.append(dict(tr=tr,k=k,phase=k%5,u=g.v_f[k],w=g.v_a[k],up=g.v_f[max(k-1,0)],wp=g.v_a[max(k-1,0)],f=f[k],lat=lat[k],r=dp[k]/dt,dp=dp[k],phi=phi[k],dx=dx[k],dy=dy[k],h=h[k]))
a=pd.DataFrame(rows)
def fit(cols,target,mask=None):
 z=a if mask is None else a[mask]; X=np.array([np.ones(len(z))]+[np.asarray(c(z)) for c in cols]).T;y=z[target].values;b=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@b;return b,np.sqrt(np.mean(r*r)),r
families={'f linear':[lambda z:z.u], 'f quad':[lambda z:z.u,lambda z:z.u**2], 'f angular':[lambda z:z.u,lambda z:z.u*z.w**2], 'f delay':[lambda z:z.u,lambda z:z.up], 'r linear':[lambda z:z.w], 'r quadratic':[lambda z:z.w,lambda z:z.w*abs(z.w)], 'r cubic':[lambda z:z.w,lambda z:z.w**3], 'r speed':[lambda z:z.w,lambda z:z.w*z.u], 'r delay':[lambda z:z.w,lambda z:z.wp]}
print('ALL TRANSITIONS',len(a))
for name,cols in families.items():
 tar=name[0];b,rmse,r=fit(cols,tar);print(name,'coef',b,'RMSE',rmse,'lag1 corr',pd.Series(r).autocorr());
 for phase in range(5):
  ix=a.phase==phase; print(' phase',phase,'mean residual',r[ix].mean(),'rmse',np.sqrt(np.mean(r[ix]**2)))
print('\nSTEADY PHASE>=2')
for name,cols in families.items():
 if 'delay' not in name:
  print(name,fit(cols,name[0],a.phase>=2)[:2])
print('\nGEOMETRY')
for alpha in [0,0.25,0.5,0.75,1]:
 h=a.phi+alpha*a.dp;la=(-a.dx*np.sin(h)+a.dy*np.cos(h));print('alpha',alpha,'lateral displacement rms',np.sqrt(np.mean(la**2)),'max',abs(la).max())
res=least_squares(lambda q: -a.dx*np.sin(a.phi+q[0]*a.dp+q[1])+a.dy*np.cos(a.phi+q[0]*a.dp+q[1]),[0.5,0]);print('best alpha offset',res.x,'lateral rms',np.sqrt(np.mean(res.fun**2)))
for tr in [1,2,3]:
 z=a[a.tr==tr];res=least_squares(lambda q: -z.dx*np.sin(z.phi+q[0]*z.dp+q[1])+z.dy*np.cos(z.phi+q[0]*z.dp+q[1]),[0.5,0]);print('tr',tr,'geometry',res.x,np.sqrt(np.mean(res.fun**2)))
print('lat velocity rms',np.sqrt(np.mean(a.lat**2)),'f min max',a.f.min(),a.f.max())
print('\nPHASE ESTIMATES: intercept, current, previous')
for phase in range(5):
 print('phase',phase,'f',fit([lambda z:z.u,lambda z:z.up],'f',a.phase==phase)[:2],'r',fit([lambda z:z.w,lambda z:z.wp],'r',a.phase==phase)[:2])
print('\nBY TRAJECTORY')
for tr in [1,2,3]:
 for tar,col in [('f',lambda z:z.u),('r',lambda z:z.w)]:print(tr,tar,fit([col],tar,a.tr==tr)[:2])
# multistep means block displacement vs commands, omit initial transient step and average phases 2-4
s=a[a.phase>=2].groupby(['tr',(a.k//5).rename('block')]).mean(numeric_only=True).reset_index();print('\nBLOCK MEANS steady n',len(s))
for tar in ['f','r']:
 cols=np.c_[np.ones(len(s)),s.u if tar=='f' else s.w];b=np.linalg.lstsq(cols,s[tar],rcond=None)[0];r=s[tar]-cols@b;print(tar,'coef',b,'rmse',np.sqrt(np.mean(r*r)))
print('\nEXTREMES'); print(a.sort_values('f').head(7).to_string(index=False));print(a.sort_values('f').tail(7).to_string(index=False))
a.to_csv('helper_transitions.csv',index=False)
