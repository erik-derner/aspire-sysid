from fit_kinematic import *
R=json.load(open('fast_results.json'));z=np.load('kinematics.npz');m=np.load('motion.npz');X=z['X'];dy=z['Y'];G=z['G']
for name in ['rational_10','deadzone_25','smooth_149','cubic_10','wheelsoft_149']:
 r=R[name];p=r['p'];f=r['f'];s,w=maps(p,X[:,3],X[:,4],f);mid=X[:,2]+w/2;e=np.column_stack([s*np.cos(mid),s*np.sin(mid),w])-np.column_stack([dy[:,:2],z['dth']])
 print(name,'one step RMSE',np.sqrt(np.mean(e**2,axis=0)))
 for j in range(3):print('state/input correlations e',j,np.corrcoef(np.column_stack([e[:,j],X]).T)[0,1:])
 for g,a in enumerate(TRAJS):
  pred=sim(p,a,f);er=pred-a[:,:3];er[:,2]=np.arctan2(np.sin(er[:,2]),np.cos(er[:,2]));print('trajectory',g+1,'final error',er[-1], 'mean error',er.mean(axis=0))
 print('input change vs steady angular RMSE',np.sqrt(np.mean(e[~m['steady'],2]**2)),np.sqrt(np.mean(e[m['steady'],2]**2)))
