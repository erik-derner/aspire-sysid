from fit_models import *
R=json.loads(Path('fit_results.json').read_text())
print('25STEP FIRST-WINDOW HOLDOUT, saved fits:')
for f,r in R.items():
 es=[]
 for i in range(3):
  z=windows([i],25,150);es.append(stats(np.array(r['foldparams'][i]),f,z))
 print(f,np.round(np.sqrt(np.mean(np.array(es)**2,axis=0)),5),'fold',np.round(es,5).tolist())
print('\nWeight sensitivity Euler and structural extensions')
for f in ['euler','affine','coupled','deadzone','arc']:
 for wt in [0,.1,.4]:
  cv=[];es=[]
  for i in range(3):
   p=fit(f,[j for j in range(3) if j!=i],weight=wt)
   cv.append(stats(p,f,windows([i])));es.append(stats(p,f,windows([i],25,150)))
  p=fit(f,[0,1,2],weight=wt)
  print(f,wt,'p',np.round(p,5),'cv',np.round(np.sqrt(np.mean(np.array(cv)**2,axis=0)),5),'first',np.round(np.sqrt(np.mean(np.array(es)**2,axis=0)),5))
print('\nONE-STEP EULER RESIDUALS')
p=np.array(R['euler']['parameters'])
for phase in range(5):
 res=[];du=[]
 for s,u in trajs:
  f,w,_=maps(p,'euler',u[:-1]);pred=s[:-1].copy();pred[:,0]+=.2*f*np.cos(s[:-1,2]);pred[:,1]+=.2*f*np.sin(s[:-1,2]);pred[:,2]+=.2*w
  e=s[1:]-pred;ii=np.arange(149);sel=ii%5==phase;res.extend(e[sel]);prev=np.vstack([np.zeros(2),u[:-2]]);du.extend((u[:-1]-prev)[sel])
 res=np.array(res);du=np.array(du)
 print('phase',phase,'RMSE',np.sqrt(np.mean(res**2,axis=0)),'corr angular residual with command change',np.corrcoef(res[:,2],du[:,1])[0,1])
