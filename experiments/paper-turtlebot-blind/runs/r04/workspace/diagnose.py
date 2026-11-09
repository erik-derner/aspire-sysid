exec(open('refine.py').read().split('\nR={}\n')[0])
R=json.load(open('select_results.json'))
for key in ['deadwheel_40','smoothyaw_12']:
 f=key.split('_')[0];p=np.array(R[key]['p']);errs=[];rows=[];simerrs=[]
 for i,g in enumerate(G):
  v,h,m=cal(p,g[:-1,3],g[:-1,4],f);step=np.c_[v*np.cos(g[:-1,2]+m*h),v*np.sin(g[:-1,2]+m*h),h];obs=np.c_[np.diff(g[:,:2],axis=0),np.diff(U[i])];e=obs-step;errs.append(e);rows.append(np.c_[np.arange(149)%5,g[:-1,3:5]]);ss=sim2(p,f,i);ee=ss-g[:,:3];ee[:,2]=ss[:,2]-U[i];simerrs.append(ee[1:]);print(key,'trajectory',i+1,'sim RMSE',np.sqrt(np.mean(ee[1:]**2,axis=0)),'final error',ee[-1],'ranges',ss.min(axis=0),ss.max(axis=0))
 errs=np.vstack(errs);rows=np.vstack(rows);print('one-step mean',errs.mean(axis=0),'RMSE',np.sqrt(np.mean(errs**2,axis=0)))
 for j in range(5):
  e=errs[rows[:,0]==j];print('phase',j,'n',len(e),'mean',e.mean(axis=0),'rmse',np.sqrt(np.mean(e**2,axis=0)))
 for j in [1,2]: print('resid corr input',j,np.corrcoef(np.c_[errs,rows[:,j]],rowvar=False)[-1,:3])
 print('aggregate rollout',np.sqrt(np.mean(np.vstack(simerrs)**2,axis=0)))
