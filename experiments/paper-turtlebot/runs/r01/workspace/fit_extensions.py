import fit_models as F
import numpy as np,json,time
from scipy.optimize import least_squares
orig=F.velocities
F.SPECS.update({
 'sparse':([.83,.54,.14,.42,0,.001],([.2,.1,-.4,-2,-.15,-.04],[1.5,1.5,1,2,.15,.04])),
 'wheels':([.83,.8,.115,.005],([.2,.1,.04,0],[1.5,1.5,.3,.04])),
 'mixing':([.83,.7,0,0],([.2,.1,-.03,-.5],[1.5,1.5,.03,.5])),
})
def velocities(name,p,u,w):
 if name=='sparse':return p[0]*u+p[5],p[1]*w+p[2]*w**3+p[3]*u*w+p[4]
 if name=='mixing':return p[0]*u+p[2]*w,p[1]*w+p[3]*u
 if name=='wheels':
  R=u+p[2]*w;L=u-p[2]*w
  R=np.sign(R)*np.maximum(np.abs(R)-p[3],0);L=np.sign(L)*np.maximum(np.abs(L)-p[3],0)
  return p[0]*(R+L)/2,p[1]*(R-L)/(2*p[2])
 return orig(name,p,u,w)
F.velocities=velocities
if __name__=='__main__':
 R={}
 for name in ['sparse','wheels','mixing']:
  p,info=F.fit(name,F.traj);cv=[];cvps=[]
  for i in range(3):
   pc,ci=F.fit(name,[g for j,g in enumerate(F.traj) if i!=j]);cv.append(F.metrics(name,pc,[F.traj[i]]));cvps.append(pc.tolist())
  R[name]={'parameters':p.tolist(),'optimization':info,'train':F.metrics(name,p,F.traj),'full_x':F.full_metrics(name,p,F.traj),'validation':cv,'validation_parameters':cvps,'cv_x':float(np.sqrt(np.mean([a['x']**2 for a in cv])))}
  print(name,json.dumps(R[name]),flush=True)
 open('extension_results.json','w').write(json.dumps(R,indent=2))
