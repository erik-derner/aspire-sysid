import pandas as pd,numpy as np
P=pd.read_csv('helper_pairs.csv');P['uprev']=P.groupby('tr').u.shift();P['wprev']=P.groupby('tr').w.shift();P=P.dropna();np.set_printoptions(precision=10)
def regress(name,X,y):
 b=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@b;print(name,'n',len(y),'coef',b,'rmse',np.sqrt(np.mean(e*e)))
for phase in range(5):
 a=P[P.phase==phase];u=a.u.to_numpy();v=a.uprev.to_numpy();w=a.w.to_numpy();z=a.wprev.to_numpy();ones=np.ones(len(a));f=lambda x:np.sign(x)*np.maximum(abs(x)-.0923009705,0)
 regress('phase '+str(phase)+' step',np.array([ones,u,v]).T,a.midforward.to_numpy())
 regress('phase '+str(phase)+' angle',np.array([ones,f(w),f(z)]).T,a.dtheta.to_numpy())
a=P[P.phase==0]; print('phase0 step previous only RMSE',np.sqrt(np.mean((a.midforward-.1666184871*a.uprev)**2)));print('phase0 angle previous only RMSE',np.sqrt(np.mean((a.dtheta-.1591916941*np.sign(a.wprev)*np.maximum(abs(a.wprev)-.0923009705,0))**2)))
print('phase0 initial heading lateral RMSE',np.sqrt(np.mean(a.lateral**2)),'midpoint lateral RMSE',np.sqrt(np.mean(a.midlateral**2)))
