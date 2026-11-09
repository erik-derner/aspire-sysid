import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); frames=[]
for tid,g in D.groupby('trajectory'):
 g=g.copy(); a=g[['y','x1','x2','x3','x4']].to_numpy(); pos=a[:,:2]; delta=np.diff(pos,axis=0); th=a[:-1,2]; dth=np.angle(np.exp(1j*np.diff(a[:,2]))); speed=np.linalg.norm(delta,axis=1)/.2; direction=np.arctan2(delta[:,1],delta[:,0]); amid=th+dth/2
 f=pd.DataFrame({'traj':tid,'k':np.arange(len(g)-1),'dy':delta[:,0],'dx1':delta[:,1],'theta':th,'dtheta':dth,'v':speed,'u':a[:-1,3],'w':a[:-1,4], 'along':(delta[:,0]*np.cos(th)+delta[:,1]*np.sin(th))/.2,'cross':(-delta[:,0]*np.sin(th)+delta[:,1]*np.cos(th))/.2,'direrr':np.angle(np.exp(1j*(direction-amid)))})
 for name in ['v','dtheta','u','w','along','cross']:
  for lag in [1,2,3]:f[name+str(lag)]=f[name].shift(lag)
 frames.append(f)
F=pd.concat(frames,ignore_index=True); F.to_csv('explore_helper_kinematics_derived.csv',index=False)
print('ALL 447 TRANSITIONS summary');print(F[['dy','dx1','dtheta','v','along','cross','direrr']].describe().to_string())
print('WRAP transitions');
for tid,g in D.groupby('trajectory'):
 dd=np.diff(g.x2); idx=np.where(abs(dd)>np.pi)[0];print(tid,[(int(i),float(g.x2.iloc[i]),float(g.x2.iloc[i+1]),float(np.angle(np.exp(1j*dd[i])))) for i in idx])
def fit(target,columns,subset=None):
 ff=F if subset is None else F.loc[subset];ff=ff.dropna(subset=[target]+columns); X=np.column_stack([np.ones(len(ff))]+[ff[c] for c in columns]); z=ff[target].to_numpy(); b=np.linalg.lstsq(X,z,rcond=None)[0]; e=z-X@b; print(target,columns,'n',len(ff),'coef',b,'RMSE',np.sqrt(np.mean(e*e)),'MAX',np.max(abs(e)));return b,e
for target in ['v','along','dtheta']:
 for cols in [['u','w'],['u','u1','w','w1'],['u','u1','u2','w','w1','w2'],[target+'1','u','w'],[target+'1',target+'2','u','u1','w','w1']]:fit(target,cols)
print('DIRECTION projections');print('midpoint dir err RMS',np.sqrt(np.mean(F.direrr**2)),'quantiles',np.quantile(F.direrr,[0,.01,.1,.5,.9,.99,1]));
# Compare directional angle at variable theta interpolation; unsigned displacement can reverse under noise
for alpha in [0,.25,.5,.75,1]:
 angle=F.theta+alpha*F.dtheta; perp=-F.dy*np.sin(angle)+F.dx1*np.cos(angle); print('alpha',alpha,'perpRMSE',np.sqrt(np.mean(perp**2)),'max',max(abs(perp)))
# nonlinear velocity and turn-rate direct fit with simple bicycle-like families
for terms in [['u'],['u','w'],['u','u1'],['u','u1','u2'],['u','u1','u2','u3']]:fit('along',terms)
F['uw']=F.u*F.w; F['utanw']=F.u*np.tan(F.w); F['w2sq']=F.w**2
for cols in [['w'],['uw'],['utanw'],['dtheta1','w'],['dtheta1','uw'],['dtheta1','utanw'],['w','w1','w2'],['uw','w','u']]:fit('dtheta',cols)
print('INPUT changes detailed first 30');print(F.head(30).to_string(index=False))
