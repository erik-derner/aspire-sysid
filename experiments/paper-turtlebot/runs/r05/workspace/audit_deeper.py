import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv');A=pd.read_csv('audit_increments.csv');A['omega']=A.dh/.2; A['block']=A.k//5
B=A[A.phase>0].groupby(['tr','block']).agg(vf=('vf','first'),va=('va','first'),speed=('speed','mean'),omega=('omega','mean'),speed_std=('speed','std'),omega_std=('omega','std')).reset_index();B['gv']=B.speed/B.vf;B['gw']=B.omega/B.va
print('BLOCKS',B.to_string(index=False)); print('CORRELATIONS',B[['vf','va','speed','omega','gv','gw']].corr().to_string())
for step in [np.pi/3600,np.pi/18000,np.pi/1800]:
 q=D.phi/step; print('phi quantum rad',step,'RMS fraction to closest integer',np.sqrt(np.mean((q-np.round(q))**2)),'max',np.max(np.abs(q-np.round(q))))
# Fit steady forward/angular linear, coupled, polynomial; compare within-block noise to unexplained block means.
for y,cols in [('speed',['vf']),('speed',['vf','one']),('omega',['va']),('omega',['va','vf','one']),('omega',['va','vfva','one']),('omega',['va','vfva','vf2va','va3','one'])]:
 B['one']=1.;B['vfva']=B.vf*B.va;B['vf2va']=B.vf**2*B.va;B['va3']=B.va**3
 X=B[cols].to_numpy(); z=B[y].to_numpy();coef=np.linalg.lstsq(X,z,rcond=None)[0];r=z-X@coef
 print('STEADY FIT',y,cols,'coeff',coef,'RMSE',np.sqrt(np.mean(r*r)),'resid lag1',np.corrcoef(r[:-1],r[1:])[0,1])
# Joint command gains and transient implied offset. Block trend/error localization
for tr,g in B.groupby('tr'):
 print('tr',tr,'mean gv vf>.03',g.loc[g.vf>.03,'gv'].mean(),'std',g.loc[g.vf>.03,'gv'].std(),'mean gw absva>.1',g.loc[g.va.abs()>.1,'gw'].mean(),'std',g.loc[g.va.abs()>.1,'gw'].std())
print('pooled within steady block RMS speed m/s',np.sqrt(np.mean(B.speed_std**2)),'angular rad/s',np.sqrt(np.mean(B.omega_std**2)))
# Physically motivated wheel clipping: rates from calibrated forward and angular combinations, learn max wheel speed.
def wheel(par,a):
 gf,ga,track,cap=par;left=gf*a.vf-ga*track*a.va/2;right=gf*a.vf+ga*track*a.va/2
 left=np.clip(left,-cap,cap);right=np.clip(right,-cap,cap)
 return (left+right)/2,(right-left)/track
# residual scales to equalize translational/angular metrics; exploratory only
for start in [[.85,.7,.23,.2],[.85,.7,.23,.3],[.85,.7,.23,.15]]:
 f=least_squares(lambda p:np.r_[(wheel(p,B)[0]-B.speed)/.01,(wheel(p,B)[1]-B.omega)/.08],start,bounds=([.1,.1,.05,.01],[2,2,1,1]))
 v,w=wheel(f.x,B);print('WHEEL CLIP params gf ga track_m cap_m/s',f.x,'RMSEspeed',np.sqrt(np.mean((v-B.speed)**2)),'RMSEomega',np.sqrt(np.mean((w-B.omega)**2)))
