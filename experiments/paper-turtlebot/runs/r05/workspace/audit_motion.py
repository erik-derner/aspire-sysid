import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); ts=.2
A=[]
for tr,g in D.groupby('trajectory'):
 p=g[['x','y','phi']].to_numpy(); ph=np.unwrap(p[:,2]); dp=np.diff(p[:,:2],axis=0); dh=np.diff(ph); mid=ph[:-1]+dh/2
 z=pd.DataFrame({'tr':tr,'k':np.arange(len(g)-1),'vf':g.v_f.to_numpy()[:-1],'va':g.v_a.to_numpy()[:-1],'dx':dp[:,0],'dy':dp[:,1],'dh':dh,'phi':ph[:-1],'mid':mid,'speed':(dp[:,0]*np.cos(mid)+dp[:,1]*np.sin(mid))/ts,'lateral':(-dp[:,0]*np.sin(mid)+dp[:,1]*np.cos(mid))/ts})
 for j in range(1,5):
  z['vf_l'+str(j)]=g.v_f.shift(j).to_numpy()[:-1];z['va_l'+str(j)]=g.v_a.shift(j).to_numpy()[:-1]
 z['phase']=z.k%5;A.append(z)
A=pd.concat(A,ignore_index=True); A.to_csv('audit_increments.csv',index=False)
print('RANGES',D.agg(['min','max']).to_string()); print('PHASE SUMMARY',A.groupby('phase')[['speed','lateral','dh']].agg(['mean','std']).to_string())
def fit(name,cols,target,sel=None):
 a=A if sel is None else A.loc[sel];a=a.dropna(subset=cols+[target]); X=a[cols].to_numpy(); y=a[target].to_numpy();b=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@b
 print(name,'N',len(a),'coeff',dict(zip(cols,b)),'RMSE',np.sqrt(np.mean(r*r)),'acf1',np.corrcoef(r[:-1],r[1:])[0,1]);return b,r,a
A['one']=1.; A['omega']=A.dh/ts;A['vf2']=A.vf**2;A['va2']=A.va**2;A['va3']=A.va**3;A['vfva']=A.vf*A.va;A['vfva2']=A.vf*A.va**2;A['vf2va']=A.vf**2*A.va
for tar,cmd in [('speed','vf'),('omega','va')]:
 fit(tar+' static',[cmd,'one'],tar)
 fit(tar+' lag1',[cmd,cmd+'_l1','one'],tar)
 fit(tar+' lag4',[cmd]+[cmd+'_l'+str(j) for j in range(1,5)]+['one'],tar)
 for phase in range(5):fit(tar+' phase '+str(phase),[cmd,cmd+'_l1','one'],tar,A.phase==phase)
fit('speed nonlinear',['vf','vf2','vfva2','one'],'speed');fit('omega nonlinear',['va','va3','vfva','vf2va','one'],'omega')
for tr in range(1,4):
 fit('speed tr '+str(tr),['vf','vf_l1','one'],'speed',A.tr==tr);fit('omega tr '+str(tr),['va','va_l1','one'],'omega',A.tr==tr)
print('LATERAL RMS m/s',np.sqrt(np.mean(A.lateral**2)),'max abs',np.max(np.abs(A.lateral)))
print('LATERAL corr with omega',np.corrcoef(A.lateral,A.omega)[0,1]);print('SMALLEST SPEED COMMANDS',A.nsmallest(12,'vf')[['tr','k','vf','va','speed','lateral','omega']].to_string(index=False))
# heading used for each displacement; tests midpoint vs previous vs next heading
for frac in [0,.5,1]:
 h=A.phi+frac*A.dh;l=-A.dx*np.sin(h)+A.dy*np.cos(h)
 print('heading frac',frac,'transverse increment RMS m',np.sqrt(np.mean(l*l)))
# command holds and wrap diagnostics
for tr,g in D.groupby('trajectory'):
 changes=np.where((g.v_f.diff().fillna(1)!=0)|(g.v_a.diff().fillna(1)!=0))[0]; print('tr',tr,'changes',changes.tolist(),'raw wrap count',np.sum(np.abs(np.diff(g.phi))>np.pi))
print('FIRST STATES',D.groupby('trajectory').first().to_string())
