import fit_models as fm
import numpy as np,json
from scipy.optimize import least_squares
fm.SPECS.update({
 'speed_deadzone':(['gf','ga','df','ba'],[.9,.75,.009,.01],[.2,.2,0,-.15],[1.5,1.5,.08,.15]),
 'speed_saturation':(['gf','ga','bf','ba','sf'],[.9,.75,-.008,.01,0],[.2,.2,-.04,-.15,-1],[2,1.5,.04,.15,5]),
 'turn_abs':(['gf','ga','bf','ba','qa'],[.9,.75,-.008,.01,0],[.2,0,-.04,-.15,-1.5],[1.5,2,.04,.15,1.5]),
 'speed_turn_loss':(['gf','ga','bf','ba','lf'],[.9,.75,-.008,.01,0],[.2,.2,-.04,-.15,-1],[1.5,1.5,.04,.15,1]),
})
original_motion=fm.motion
def motion(p,u,family):
 if family in ['speed_deadzone','speed_saturation','turn_abs','speed_turn_loss']:
  v=u[:,0];a=u[:,1];gf,ga,bf,ba=p[:4];f=gf*v+bf;w=ga*a+ba
  if family=='speed_deadzone':f=gf*np.maximum(v-bf,0)
  if family=='speed_saturation':f=gf*v/(1+p[4]*v)+bf
  if family=='turn_abs':w+=p[4]*a*np.abs(a)
  if family=='speed_turn_loss':f+=p[4]*v*a*a
  return f,w,np.zeros_like(v)
 return original_motion(p,u,family)
fm.motion=motion

def fit(family,ids,weights=(1,.35,.05)):
 names,start,lo,hi=fm.SPECS[family];data=fm.make_windows(ids)
 def fun(p):return ((fm.rollout(p,family,data)-data[1])*np.array(weights)).ravel()
 sol=least_squares(fun,start,bounds=(lo,hi),max_nfev=400,ftol=1e-10,xtol=1e-10,gtol=1e-10,x_scale='jac')
 return sol.x,{'cost':float(sol.cost),'nfev':sol.nfev,'success':bool(sol.success)}
if __name__=='__main__':
 results={}
 for weights in [(1,.35,.05),(1,0,0)]:
  for fam in ['linear_midpoint','linear_euler','cubic_turn','deadzone_turn','body_slip','speed_deadzone','speed_saturation','turn_abs','speed_turn_loss','wheel_deadzone']:
   p,info=fit(fam,[0,1,2],weights);cv=[]
   for test in range(3):
    q,inf=fit(fam,[i for i in range(3) if i!=test],weights)
    cv.append({'test_trajectory':test+1,'parameters':q.tolist(),'metrics':fm.metrics(q,fam,[test]),'info':inf})
   key=fam+('_x' if weights[1]==0 else '_weighted')
   results[key]={'family':fam,'weights':weights,'names':fm.SPECS[fam][0],'parameters':p.tolist(),'info':info,'training':fm.metrics(p,fam,[0,1,2]),'full_trajectory_training':fm.full_metric(p,fam,[0,1,2]),'cv':cv,'cv_x':float(np.sqrt(np.mean([v['metrics']['x']**2 for v in cv])))}
   print(key,'p',p,'train x',results[key]['training']['x'],'cv',results[key]['cv_x'],flush=True)
   with open('refine_results.json','w') as f:json.dump(results,f,indent=2)
