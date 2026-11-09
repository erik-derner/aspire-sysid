import numpy as np, pandas as pd, json, time
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv')
TRAJ=[]
for k,g in D.groupby('trajectory',sort=True):
 a=g[['x','y','phi','v_f','v_a']].to_numpy(); a[:,2]=np.unwrap(a[:,2]); TRAJ.append(a)
TS=.2
# All candidates use midpoint quadrature. Bounds are physically conservative constraints, not estimated constants.
SPECS={
'linear':dict(names=['gv','gw'],init=[.83,.68],lo=[.1,.1],hi=[1.5,1.5]),
'affine':dict(names=['gv','gw','bv','bw','beta'],init=[.83,.68,0,0,0],lo=[.1,.1,-.05,-.3,-.3],hi=[1.5,1.5,.05,.3,.3]),
'deadzone':dict(names=['gv','gw','dead'],init=[.83,.78,.08],lo=[.1,.1,0],hi=[1.5,1.5,.4]),
'poly':dict(names=['gv','gw','cvturn','cwthree','cwforward'],init=[.83,.68,0,0,0],lo=[.1,.1,-1,-1,-2],hi=[1.5,1.5,1,1,2]),
'asymmetric':dict(names=['gv','gw','gasym','cvturn'],init=[.83,.68,0,0],lo=[.1,.1,-.4,-1],hi=[1.5,1.5,.4,1]),
'body':dict(names=['gv','gw','lever','bw'],init=[.83,.68,0,0],lo=[.1,.1,-.3,-.3],hi=[1.5,1.5,.3,.3]),
'power':dict(names=['gv','gw','power'],init=[.83,.75,1.2],lo=[.1,.1,.5],hi=[1.5,1.5,2.5]),
'wheel':dict(names=['gv','gw','halftrack','fric'],init=[.83,.68,.115,.005],lo=[.1,.1,.06,0],hi=[1.5,1.5,.22,.06])}

def response(p,u,fam):
 f,a=u[...,0],u[...,1]; beta=0; lat=0
 if fam=='linear': v=p[0]*f; w=p[1]*a
 elif fam=='affine': v=p[0]*f+p[2]; w=p[1]*a+p[3]; beta=p[4]
 elif fam=='deadzone': v=p[0]*f; w=p[1]*np.sign(a)*np.maximum(np.abs(a)-p[2],0)
 elif fam=='poly': v=f*(p[0]+p[2]*a*a); w=a*(p[1]+p[3]*a*a+p[4]*f)
 elif fam=='asymmetric': v=f*(p[0]+p[3]*np.abs(a)); w=p[1]*a+p[2]*np.abs(a)
 elif fam=='body': v=p[0]*f; w=p[1]*a+p[3]; lat=p[2]*w
 elif fam=='power': v=p[0]*f; w=p[1]*np.sign(a)*np.abs(a)**p[2]
 elif fam=='wheel':
  r=f+p[2]*a; l=f-p[2]*a
  r=np.sign(r)*np.maximum(np.abs(r)-p[3],0); l=np.sign(l)*np.maximum(np.abs(l)-p[3],0)
  v=p[0]*(r+l)/2; w=p[1]*(r-l)/(2*p[2])
 return v,w,beta,lat

def windows(ids,h=25,stride=5):
 init=[]; u=[]; target=[]
 for i in ids:
  a=TRAJ[i]
  for st in range(0,len(a)-h,stride):
   init.append(a[st,:3]); u.append(a[st:st+h,3:]); target.append(a[st+1:st+h+1,:3])
 return np.array(init),np.array(u),np.array(target)

def simulate(p,pack,fam):
 state=pack[0].copy(); u=pack[1]; out=[]
 v,w,b,lat=response(p,u,fam)
 for k in range(u.shape[1]):
  angle=state[:,2]+TS*w[:,k]/2+b
  lk=lat[:,k] if isinstance(lat,np.ndarray) else lat
  state[:,0]+=TS*(v[:,k]*np.cos(angle)-lk*np.sin(angle))
  state[:,1]+=TS*(v[:,k]*np.sin(angle)+lk*np.cos(angle))
  state[:,2]+=TS*w[:,k]
  out.append(state.copy())
 return np.stack(out,axis=1)

def residual(p,pack,fam,kind='joint'):
 err=simulate(p,pack,fam)-pack[2]
 if kind=='joint': err=err*np.array([1,1,.25])
 elif kind=='xy': err=err[:,:,:2]
 elif kind=='x': err=err[:,:,:1]
 return err.ravel()

def fit(fam,ids,kind='joint',h=25):
 s=SPECS[fam]; pack=windows(ids,h)
 r=least_squares(residual,s['init'],bounds=(s['lo'],s['hi']),args=(pack,fam,kind),method='trf',max_nfev=300,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return r.x,dict(cost=float(r.cost),nfev=r.nfev,status=r.status)

def scores(p,ids,fam,h=25,stride=5):
 pack=windows(ids,h,stride); err=simulate(p,pack,fam)-pack[2]
 return np.sqrt(np.mean(err*err,axis=(0,1))).tolist()

def longscores(p,ids,fam):
 es=[]
 for i in ids:
  a=TRAJ[i]; pack=(a[None,0,:3],a[None,:-1,3:],a[None,1:,:3]); es.append((simulate(p,pack,fam)-pack[2])[0])
 e=np.concatenate(es); return np.sqrt(np.mean(e*e,axis=0)).tolist()

if __name__=='__main__':
 results={}
 for fam in SPECS:
  results[fam]={}
  for kind in ['joint','xy','x']:
   p,info=fit(fam,[0,1,2],kind); folds=[]
   for held in range(3):
    q,_=fit(fam,[i for i in range(3) if i!=held],kind)
    folds.append(dict(parameters=q.tolist(),rmse=scores(q,[held],fam),long=longscores(q,[held],fam)))
   results[fam][kind]=dict(parameters=p.tolist(),info=info,train=scores(p,[0,1,2],fam),long=longscores(p,[0,1,2],fam),folds=folds,cv_x=float(np.sqrt(np.mean([f['rmse'][0]**2 for f in folds]))))
   print(fam,kind,'parameters',np.round(p,5),'train',np.round(results[fam][kind]['train'],5),'long',np.round(results[fam][kind]['long'],4),'CVx',round(results[fam][kind]['cv_x'],5),flush=True)
 json.dump(results,open('explore_results.json','w'),indent=2)
