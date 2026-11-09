import numpy as np,pandas as pd
from scipy.optimize import least_squares
A=pd.read_csv('audit_increments.csv');A['omega']=A.dh/.2
S=A[A.phase>0].copy();S['block']=S.k//5
B=S.groupby(['tr','block']).agg(vf=('vf','first'),va=('va','first'),speed=('speed','mean'),omega=('omega','mean')).reset_index()
for label,a in [('early',S[S.k<75]),('late',S[S.k>=75])]:
 for out,cmd in [('speed','vf'),('omega','va')]:
  gain=np.dot(a[cmd],a[out])/np.dot(a[cmd],a[cmd]);print(label,out,'n',len(a),'gain',gain,'rms',np.sqrt(np.mean((a[out]-gain*a[cmd])**2)))
for model in ['linear','deadzone','power']:
 def predict(p,z):
  if model=='linear':return p[0]*z
  if model=='deadzone':return p[0]*np.sign(z)*np.maximum(np.abs(z)-p[1],0)
  return p[0]*np.sign(z)*np.abs(z)**p[1]
 start=[.7] if model=='linear' else ([.8,.1] if model=='deadzone' else [.7,1.2]); bounds=([0],[2]) if model=='linear' else ([0,0],[2,1] if model=='deadzone' else [2,4])
 f=least_squares(lambda p:predict(p,B.va)-B.omega,start,bounds=bounds);r=predict(f.x,B.va)-B.omega
 print('angular block model',model,'params',f.x,'RMSE rad/s',np.sqrt(np.mean(r*r)))
# AR diagnostics of command residuals distinguish white pose noise (negative differentiated lag) from persistent drift.
for out,cmd,gain in [('speed','vf',.83007286),('omega','va',.67656896)]:
 allr=[];allr1=[]
 for tr,g in A.groupby('tr'):
  r=g[out].to_numpy()-gain*g[cmd].to_numpy();keep=(g.phase.to_numpy()>0);valid=keep[:-1]&keep[1:];allr.extend(r[:-1][valid]);allr1.extend(r[1:][valid])
 print('adjacent within block residual corr',out,np.corrcoef(allr,allr1)[0,1])
# Per block average residual additive position errors would telescope; estimate steady command gain trend only diagnostically.
for tr,g in S.groupby('tr'):
 X=np.column_stack([g.vf,g.vf*g.k/149]); b=np.linalg.lstsq(X,g.speed,rcond=None)[0];print('forward trend tr',tr,'intercept gain',b[0],'end gain',b.sum(),'RMS m/s',np.sqrt(np.mean((X@b-g.speed)**2)))
# first transition values
print('first transitions',A[A.k==0][['tr','vf','va','speed','omega']].to_string(index=False))
