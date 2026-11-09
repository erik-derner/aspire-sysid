import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from pathlib import Path
D=pd.read_csv('data/train.csv'); TS=.2
trajs=[]
for tid,d in D.groupby('trajectory'):
 s=d[['x','y','phi']].to_numpy();s[:,2]=np.unwrap(s[:,2]);trajs.append((s,d[['v_f','v_a']].to_numpy()))
# parameterized families; all velocity maps in SI units
spec={
 'euler':([.83,.70],([0,.1],[2,1.5])),
 'midpoint':([.83,.70],([0,.1],[2,1.5])),
 'phase':([.83,.70,0,-.05],([0,.1,-.3,-.5],[2,1.5,.3,.5])),
 'affine':([.83,.70,0,-.05,0,0],([0,.1,-.3,-.5,-.05,-.1],[2,1.5,.3,.5,.05,.1])),
 'cubic':([.83,.60,0,-.05,.15],([0,.1,-.3,-.5,-1],[2,1.5,.3,.5,1])),
 'coupled':([.83,.60,0,-.05,.15,.5],([0,.1,-.3,-.5,-1,-3],[2,1.5,.3,.5,1,3])),
 'deadzone':([.83,.80,0,-.05,.10],([0,.1,-.3,-.5,0],[2,1.5,.3,.5,.5])),
 'turnspeed':([.83,.60,0,-.05,.15,.5,0],([0,.1,-.3,-.5,-1,-3,-1],[2,1.5,.3,.5,1,3,1])),
 'quadratic':([.83,.60,0,-.05,.15,.5,0],([0,.1,-.3,-.5,-1,-3,-3],[2,1.5,.3,.5,1,3,3])),
 'asymmetric':([.83,.60,0,-.05,.15,0],([0,.1,-.3,-.5,-1,-.5],[2,1.5,.3,.5,1,.5])),
 'arc':([.83,.70,0],([0,.1,-.3],[2,1.5,.3])),
}
def maps(p,f,u):
 v,w=u[...,0],u[...,1];F=p[0]*v;W=p[1]*w;offset=0
 if f not in ['euler','midpoint']:
  offset=p[2]
  if f not in ['arc']: offset=offset+p[3]*w
 if f=='affine': F+=p[4];W+=p[5]
 if f in ['cubic','coupled','turnspeed','quadratic','asymmetric']: W+=p[4]*w**3
 if f in ['coupled','turnspeed','quadratic']: W+=p[5]*v*w
 if f=='turnspeed':F+=p[6]*v*w*w
 if f=='quadratic':F+=p[6]*v*v
 if f=='asymmetric':W+=p[5]*w*w
 if f=='deadzone':W=p[1]*np.sign(w)*np.maximum(abs(w)-p[4],0)
 return F,W,offset

def windows(ids,H=25,stride=2):
 starts=[];us=[];targets=[]
 for i in ids:
  s,u=trajs[i]
  for k in range(0,len(s)-H,stride):starts.append(s[k]);us.append(u[k:k+H]);targets.append(s[k+1:k+H+1])
 return np.array(starts),np.array(us),np.array(targets)

def simulate(p,f,z):
 starts,u,t=z;F,W,off=maps(p,f,u);ph=starts[:,2,None]+TS*np.cumsum(W,axis=1)-TS*W
 if f in ['midpoint','arc']:ph+=TS*W/2
 ph+=off
 dist=TS*F
 if f=='arc':dist*=np.sinc(TS*W/(2*np.pi))
 pred=np.empty(t.shape);pred[:,:,0]=starts[:,0,None]+np.cumsum(dist*np.cos(ph),axis=1);pred[:,:,1]=starts[:,1,None]+np.cumsum(dist*np.sin(ph),axis=1);pred[:,:,2]=starts[:,2,None]+TS*np.cumsum(W,axis=1)
 return pred

def residual(p,f,z,weight=.2):return ((simulate(p,f,z)-z[2])*np.array([1,1,weight])).ravel()
def fit(f,ids,H=25,weight=.2):
 init,bounds=spec[f];z=windows(ids,H);out=least_squares(residual,init,bounds=bounds,args=(f,z,weight),max_nfev=400,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return out.x

def stats(p,f,z):
 e=simulate(p,f,z)-z[2];return np.sqrt(np.mean(e*e,axis=(0,1))).tolist()
if __name__=='__main__':
 results={}
 for f in spec:
  p=fit(f,[0,1,2]);cv=[];fold=[]
  for i in range(3):
   q=fit(f,[j for j in range(3) if j!=i]);fold.append(q.tolist());cv.append(stats(q,f,windows([i])))
  full=stats(p,f,windows([0,1,2],149))
  results[f]={'parameters':p.tolist(),'train25':stats(p,f,windows([0,1,2])),'cv25':cv,'foldparams':fold,'full':full}
  print(f,'p',np.round(p,5),'train',np.round(results[f]['train25'],5),'CV',np.round(np.sqrt(np.mean(np.array(cv)**2,axis=0)),5),'full',np.round(full,5),flush=True)
 Path('fit_results.json').write_text(json.dumps(results,indent=2))
