exec(open('explore_helper_kinematics.py').read().split("print('ALL 447")[0])
from scipy.optimize import minimize_scalar
alpha=minimize_scalar(lambda a:np.mean((-F.dy*np.sin(F.theta+a*F.dtheta)+F.dx1*np.cos(F.theta+a*F.dtheta))**2),bounds=(0,1),method='bounded');print('optimal alpha',alpha.x,'perpRMSE',np.sqrt(alpha.fun))
for tid,g in D.groupby('trajectory'):
 a=g.x2.to_numpy(); print('angle quantization traj',tid,'max centidegree discrepancy',np.max(abs(a*180/np.pi*100-np.round(a*180/np.pi*100))))
F['absw']=abs(F.w);F['w2']=F.w**2;F['uabsw']=F.u*abs(F.w); F['uw']=F.u*F.w; F['u2']=F.u**2;F['u3cube']=F.u**3
F['deadw']=np.sign(F.w)*np.maximum(abs(F.w)-.1,0)
F['phase']=F.k%5
for target in ['v','dtheta']:
 for sublabel,ff in [('all',F),('interior',F[F.phase>=2])]:
  for cols in [['u','w'],['u','absw','uabsw'],['u','w','absw','uabsw','uw','u2','w2'],['deadw'],['u','deadw']]:
   X=np.column_stack([np.ones(len(ff))]+[ff[c] for c in cols]);z=ff[target].to_numpy();b=np.linalg.lstsq(X,z,rcond=None)[0];e=z-X@b;print(target,sublabel,cols,'n',len(ff),'coeff',b,'RMSE',np.sqrt(np.mean(e*e)))
print('phase direct input residuals')
for target,cols in [('v',['u']),('dtheta',['w'])]:
 X=np.column_stack([np.ones(len(F))]+[F[c] for c in cols]);z=F[target].to_numpy();b=np.linalg.lstsq(X,z,rcond=None)[0]; e=z-X@b
 for phase in range(5):print(target,phase,'RMSE',np.sqrt(np.mean(e[F.phase==phase]**2)))
print('per trajectory interior affine')
for tid,ff in F[F.phase>=2].groupby('traj'):
 for target,col in [('v','u'),('dtheta','w')]:
  X=np.column_stack([np.ones(len(ff)),ff[col]]);z=ff[target].to_numpy();b=np.linalg.lstsq(X,z,rcond=None)[0];print(tid,target,'n',len(ff),'coef',b,'RMSE',np.sqrt(np.mean((z-X@b)**2)))
