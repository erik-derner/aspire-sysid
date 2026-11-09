import numpy as np,pandas as pd
from scipy.optimize import least_squares
a=pd.read_csv('helper_transitions.csv');s=a[a.phase>=2]
print('counts',a.groupby('phase').size().to_dict(),'steady',len(s))
for target,cmd in [('f','u'),('r','w')]:
 z=a.copy();z['last']=z.groupby('tr')[target].shift(1);z=z.dropna(); X=np.c_[np.ones(len(z)),z[cmd],z['last']];q=np.linalg.lstsq(X,z[target],rcond=None)[0];e=z[target]-X@q;print('ARX',target,q,'rmse',np.sqrt(np.mean(e*e)))
 X=np.c_[np.ones(len(s)),s[cmd],s[cmd]*(s.k/149)];q=np.linalg.lstsq(X,s[target],rcond=None)[0];print('time gain',target,q,'rmse',np.sqrt(np.mean((X@q-s[target])**2)))
 for tr in [1,2,3]:
  z=s[s.tr==tr];X=np.c_[np.ones(len(z)),z[cmd],z[cmd]*(z.k/149)];q=np.linalg.lstsq(X,z[target],rcond=None)[0];print('pertr time gain',tr,target,q,'rmse',np.sqrt(np.mean((X@q-z[target])**2)))
# correlations among residual within blocks: evaluate stable linear
for target,cmd in [('f','u'),('r','w')]:
 X=np.c_[np.ones(len(a)),a[cmd]];stable=a.phase>=2;q=np.linalg.lstsq(X[stable],a.loc[stable,target],rcond=None)[0];e=a[target]-X@q
 print('steady fit residual phase groups',target)
 for p in [2,3,4]:
  z=a[a.phase==p];print(p,'rms',np.sqrt(np.mean(e[z.index]**2)))
 ee=pd.DataFrame({'tr':a.tr,'block':a.k//5,'phase':a.phase,'e':e}).pivot(index=['tr','block'],columns='phase',values='e');print('phase residual correlation',ee[[2,3,4]].corr().values)
# correlation geometric residual vs lag measured angular increments
z=a.copy();z['dp_prev']=z.groupby('tr').dp.shift(1);z=z.dropna()
fun=lambda q: -z.dx*np.sin(z.phi+q[0]*z.dp+q[1]*z.dp_prev+q[2])+z.dy*np.cos(z.phi+q[0]*z.dp+q[1]*z.dp_prev+q[2])
r=least_squares(fun,[.46,0,0]);print('geometry alpha/beta/offset',r.x,'lateral RMSE',np.sqrt(np.mean(r.fun**2)))
