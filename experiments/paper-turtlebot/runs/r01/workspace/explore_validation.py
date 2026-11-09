import fit_models as F
import numpy as np,json
out={}
for criterion in ['x','joint']:
 for H in [5,10,25,50,149]:
  for name in ['midpoint','affine','deadzone','phase','cross']:
   p,info=F.fit(name,F.traj,criterion=criterion,H=H)
   cvs=[]
   for i in range(3):
    pc,ii=F.fit(name,[g for j,g in enumerate(F.traj) if i!=j],criterion=criterion,H=H)
    cvs.append(F.metrics(name,pc,[F.traj[i]])['x'])
   key=f'{name}_{criterion}_{H}';out[key]={'p':p.tolist(),'cv':float(np.sqrt(np.mean(np.array(cvs)**2))),'folds':cvs,'train':F.metrics(name,p,F.traj),'full':F.full_metrics(name,p,F.traj)}
   print(key,'p',np.round(p,5),'CV',round(out[key]['cv'],5),'train',round(out[key]['train']['x'],5),'full',np.round(out[key]['full'],4),flush=True)
open('explore_results.json','w').write(json.dumps(out,indent=2))
