import fit_extensions as X
import numpy as np,json
F=X.F
original=F.velocities
F.SPECS.update({'clipped':([.9,.71,.008,.01],([.2,.1,0,-.15],[1.5,1.5,.06,.15])), 'sparse_clipped':([.9,.68,-.06,.41,.0075,.008],([.2,.1,-.4,-2,-.15,0],[1.5,1.5,1,2,.15,.06]))})
def velocities(name,p,u,w):
 if name=='clipped':return p[0]*np.sign(u)*np.maximum(np.abs(u)-p[2],0),p[1]*w+p[3]
 if name=='sparse_clipped':return p[0]*np.sign(u)*np.maximum(np.abs(u)-p[5],0),p[1]*w+p[2]*w**3+p[3]*u*w+p[4]
 return original(name,p,u,w)
F.velocities=velocities
if __name__=='__main__':
 R={}
 for name in ['clipped','sparse_clipped']:
  p,info=F.fit(name,F.traj);cv=[];cvps=[]
  for i in range(3):
   pc,ci=F.fit(name,[g for j,g in enumerate(F.traj) if i!=j]);cv.append(F.metrics(name,pc,[F.traj[i]]));cvps.append(pc.tolist())
  R[name]={'parameters':p.tolist(),'optimization':info,'train':F.metrics(name,p,F.traj),'full_x':F.full_metrics(name,p,F.traj),'validation':cv,'validation_parameters':cvps,'cv_x':float(np.sqrt(np.mean([a['x']**2 for a in cv])))}
  print(name,json.dumps(R[name]),flush=True)
 open('clipped_results.json','w').write(json.dumps(R,indent=2))
