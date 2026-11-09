import refine_models as rm,fit_models as fm
import numpy as np,json
fm.SPECS.update({
 'calibrated_theta':(['gf','ga','bf','ba','theta'],[.9,.75,-.007,.007,0],[.2,.2,-.04,-.15,-1],[1.5,1.5,.04,.15,1]),
 'rectified_euler':(['gf','ga','df','ba'],[.9,.75,.008,.007],[.2,.2,0,-.15],[1.5,1.5,.08,.15]),
 'proportional_euler':(['gf','ga'],[.85,.75],[.2,.2],[1.5,1.5]),
})
old_motion=fm.motion;old_rollout=fm.rollout
def motion(p,u,family):
 if family=='calibrated_theta':return p[0]*u[:,0]+p[2],p[1]*u[:,1]+p[3],np.zeros(len(u))
 if family=='rectified_euler':return p[0]*np.maximum(u[:,0]-p[2],0),p[1]*u[:,1]+p[3],np.zeros(len(u))
 if family=='proportional_euler':return p[0]*u[:,0],p[1]*u[:,1],np.zeros(len(u))
 return old_motion(p,u,family)
def rollout(p,family,data):
 if family not in ['calibrated_theta','rectified_euler','proportional_euler']:return old_rollout(p,family,data)
 z,t,u=data;z=z.copy();out=np.empty_like(t)
 for k in range(t.shape[1]):
  f,w,l=motion(p,u[:,k],family);dp=.2*w;angle=z[:,2]+(p[4]*dp if family=='calibrated_theta' else 0)
  z[:,0]+=.2*f*np.cos(angle);z[:,1]+=.2*f*np.sin(angle);z[:,2]+=dp;out[:,k]=z
 return out
fm.motion=motion;fm.rollout=rollout
if __name__=='__main__':
 results={}
 for fam in ['calibrated_theta','rectified_euler','proportional_euler']:
  p,info=rm.fit(fam,[0,1,2],(1,0,0));cv=[]
  for test in range(3):
   q,inf=rm.fit(fam,[i for i in range(3) if i!=test],(1,0,0));cv.append({'test_trajectory':test+1,'parameters':q.tolist(),'metrics':fm.metrics(q,fam,[test]),'info':inf})
  results[fam]={'family':fam,'weights':[1,0,0],'names':fm.SPECS[fam][0],'parameters':p.tolist(),'info':info,'training':fm.metrics(p,fam,[0,1,2]),'full_trajectory_training':fm.full_metric(p,fam,[0,1,2]),'cv':cv,'cv_x':float(np.sqrt(np.mean([v['metrics']['x']**2 for v in cv])))}
  print(fam,p,results[fam]['training'],results[fam]['cv_x'],flush=True)
 with open('theta_results.json','w') as f:json.dump(results,f,indent=2)
