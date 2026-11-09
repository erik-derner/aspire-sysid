import fit_extensions as fe
fm=fe.fm
import numpy as np,json
from pathlib import Path
base=fm.maps
def maps(p,f,u):
 if f=='rectified':
  v,w=u[...,0],u[...,1];return np.maximum(p[0]*v+p[4],0),p[1]*w+p[5],p[2]+p[3]*w
 return base(p,f,u)
fm.maps=maps
fm.spec['rectified']=fm.spec['affine']
if __name__=='__main__':
 p=fm.fit('rectified',[0,1,2]);cv=[];fold=[]
 for i in range(3):
  q=fm.fit('rectified',[j for j in range(3) if j!=i]);fold.append(q.tolist());cv.append(fm.stats(q,'rectified',fm.windows([i])))
 R={'parameters':p.tolist(),'train25':fm.stats(p,'rectified',fm.windows([0,1,2])),'cv25':cv,'foldparams':fold,'full':fm.stats(p,'rectified',fm.windows([0,1,2],149))}
 print('rectified',R)
 Path('rectified_results.json').write_text(json.dumps(R,indent=2))
