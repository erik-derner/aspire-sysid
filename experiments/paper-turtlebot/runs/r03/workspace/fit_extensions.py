import fit_models as fm
import numpy as np,json
from pathlib import Path
oldmaps=fm.maps

def maps(p,f,u):
 v,w=u[...,0],u[...,1]
 if f=='bilinear':return p[0]*v,(p[1]+p[2]*v)*w,0
 if f=='saturating':return p[0]*v,p[1]*np.tanh(p[2]*w),0
 if f=='sparsepoly':return p[0]*v,p[1]*w+p[2]*v*w+p[3]*w**3,0
 return oldmaps(p,f,u)
fm.maps=maps
fm.spec.update({'bilinear':([.85,.70,.4],([0,.1,-3],[2,1.5,3])),'saturating':([.85,.8,1],([0,.1,.05],[2,10,5])),'sparsepoly':([.85,.7,.4,.1],([0,.1,-3,-1],[2,1.5,3,1]))})
if __name__=='__main__':
 R={}
 for f in ['bilinear','saturating','sparsepoly']:
  p=fm.fit(f,[0,1,2]);cv=[];fold=[]
  for i in range(3):
   q=fm.fit(f,[j for j in range(3) if j!=i]);fold.append(q.tolist());cv.append(fm.stats(q,f,fm.windows([i])))
  R[f]={'parameters':p.tolist(),'train25':fm.stats(p,f,fm.windows([0,1,2])),'cv25':cv,'foldparams':fold,'full':fm.stats(p,f,fm.windows([0,1,2],149))}
  print(f,'p',np.round(p,6),'cv',np.round(np.sqrt(np.mean(np.array(cv)**2,axis=0)),5),'full',np.round(R[f]['full'],5))
 Path('extension_results.json').write_text(json.dumps(R,indent=2))
