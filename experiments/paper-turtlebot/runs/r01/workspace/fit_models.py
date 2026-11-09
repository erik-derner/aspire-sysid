import numpy as np, pandas as pd, json, time
from scipy.optimize import least_squares
from pathlib import Path
D=pd.read_csv('data/train.csv'); traj=[g[['x','y','phi','v_f','v_a']].to_numpy() for _,g in D.groupby('trajectory')]
for g in traj:g[:,2]=np.unwrap(g[:,2])
Ts=.2
# Plan: physics integrators, affine calibration, odd nonlinear command maps, dead zone,
# and a phase-shifted midpoint residual model. No state-location corrections.
SPECS={
 'euler':([.83,.68],([.2,.1],[1.5,1.5])),
 'midpoint':([.83,.68],([.2,.1],[1.5,1.5])),
 'arc':([.83,.68],([.2,.1],[1.5,1.5])),
 'affine':([.83,.68,0,0],([.2,.1,-.04,-.15],[1.5,1.5,.04,.15])),
 'deadzone':([.83,.8,.08,0],([.2,.1,0,-.15],[1.5,1.5,.35,.15])),
 'cubic':([.83,.6,.15,0],([.2,.1,-.4,-.15],[1.5,1.5,1,.15])),
 'tanh':([.83,.8,.7,0],([.2,.1,.02,-.15],[1.5,2,3,.15])),
 'phase':([.83,.68,0,0],([.2,.1,-.15,-4],[1.5,1.5,.15,2])),
 'deadphase':([.83,.8,.08,0,0],([.2,.1,0,-.15,-4],[1.5,1.5,.35,.15,2])),
 'cross':([.83,.6,.15,0,0,0],([.2,.1,-.4,-.15,-2,-1],[1.5,1.5,1,.15,2,1])),
}
def velocities(name,p,u,w):
 s=p[0]*u
 if name in ['euler','midpoint','arc']:r=p[1]*w
 elif name=='affine':s+=p[2];r=p[1]*w+p[3]
 elif name in ['deadzone','deadphase']:r=p[1]*np.sign(w)*np.maximum(np.abs(w)-p[2],0)+p[3]
 elif name=='cubic':r=p[1]*w+p[2]*w**3+p[3]
 elif name=='tanh':r=p[1]*np.tanh(p[2]*w)/p[2]+p[3]
 elif name=='phase':r=p[1]*w+p[2]
 elif name=='cross':r=p[1]*w+p[2]*w**3+p[3]+p[4]*(u-.13)*w;s=s*(1+p[5]*w*w)
 return s,r

def step(name,p,S,u,w):
 s,r=velocities(name,p,u,w); a=Ts*r
 alpha=0 if name=='euler' else .5
 if name=='phase':alpha=p[3]
 if name=='deadphase':alpha=p[4]
 h=S[:,2]+alpha*a
 scale=np.sinc(a/(2*np.pi)) if name=='arc' else 1.
 return S+np.column_stack([Ts*s*scale*np.cos(h),Ts*s*scale*np.sin(h),a])

def batches(gs,H=25,stride=5):
 states=[];us=[];ws=[];targets=[]
 for g in gs:
  for k in range(0,len(g)-H,stride):
   states.append(g[k,:3]); us.append(g[k:k+H,3]);ws.append(g[k:k+H,4]);targets.append(g[k+1:k+H+1,:3])
 return np.array(states),np.array(us),np.array(ws),np.array(targets)

def predict(name,p,B):
 S,u,w,Y=B;S=S.copy();pred=[]
 for j in range(u.shape[1]):S=step(name,p,S,u[:,j],w[:,j]);pred.append(S.copy())
 return np.stack(pred,axis=1)

def residual(name,p,B,criterion='joint'):
 e=predict(name,p,B)-B[3]
 if criterion=='x':return e[:,:,0].ravel()
 e[:,:,2]=np.arctan2(np.sin(e[:,:,2]),np.cos(e[:,:,2]))*.25
 return e.ravel()

def fit(name,gs,criterion='joint',initial=None,H=25,stride=5):
 p,b=SPECS[name];p=p if initial is None else initial
 B=batches(gs,H,stride)
 opt=least_squares(lambda p:residual(name,p,B,criterion),p,bounds=b,ftol=1e-10,xtol=1e-10,gtol=1e-10,max_nfev=400)
 return opt.x,{'cost':float(opt.cost),'nfev':opt.nfev,'optimality':float(opt.optimality)}

def metrics(name,p,gs,H=25,stride=1):
 B=batches(gs,H,stride);e=predict(name,p,B)-B[3];e[:,:,2]=np.arctan2(np.sin(e[:,:,2]),np.cos(e[:,:,2]))
 return {'x':float(np.sqrt(np.mean(e[:,:,0]**2))),'y':float(np.sqrt(np.mean(e[:,:,1]**2))),'phi':float(np.sqrt(np.mean(e[:,:,2]**2))),'endpoint_x':float(np.sqrt(np.mean(e[:,-1,0]**2)))}

def full_metrics(name,p,gs):
 out=[]
 for g in gs:
  B=(g[:1,:3],g[:-1,3][None,:],g[:-1,4][None,:],g[1:,:3][None,:,:]);e=predict(name,p,B)-B[3]
  out.append(float(np.sqrt(np.mean(e[:,:,0]**2))))
 return out

def main():
 results={}
 for name in SPECS:
  t=time.time();p,info=fit(name,traj);cv=[];cvps=[]
  for i in range(3):
   pc,ci=fit(name,[g for j,g in enumerate(traj) if i!=j]);cv.append(metrics(name,pc,[traj[i]]));cvps.append(pc.tolist())
  results[name]={'parameters':p.tolist(),'optimization':info,'train':metrics(name,p,traj),'full_x':full_metrics(name,p,traj),'validation':cv,'validation_parameters':cvps,'cv_x':float(np.sqrt(np.mean([a['x']**2 for a in cv])))}
  print(name,'p',p,'train',results[name]['train'],'CV',results[name]['cv_x'],'folds',[a['x'] for a in cv],'full',results[name]['full_x'],'seconds',time.time()-t,flush=True)
 Path('fit_results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
