import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); TS=.2
G=[]
for _,g in D.groupby('trajectory'):
 z=g[['x','y','phi']].to_numpy();z[:,2]=np.unwrap(z[:,2]);u=g[['v_f','v_a']].to_numpy();G.append((z,u))
# Parameter names, starts and bounds. All speeds and biases below are per second.
SPECS={
 'linear_euler':(['gf','ga','bf','ba'],[.8,.65,0,0],[.2,.2,-.04,-.15],[1.5,1.5,.04,.15]),
 'linear_midpoint':(['gf','ga','bf','ba'],[.8,.65,0,0],[.2,.2,-.04,-.15],[1.5,1.5,.04,.15]),
 'cubic_turn':(['gf','ga','bf','ba','ca'],[.8,.55,0,0,.2],[.2,0,-.04,-.15,-1],[1.5,1.5,.04,.15,1]),
 'deadzone_turn':(['gf','ga','bf','ba','da'],[.8,.75,0,0,.08],[.2,.2,-.04,-.15,0],[1.5,1.5,.04,.15,.3]),
 'smooth_turn':(['gf','ga','bf','ba','na','sa'],[.8,.75,0,0,-.06,.1],[.2,.2,-.04,-.15,-.4,.01],[1.5,1.8,.04,.15,.3,.7]),
 'coupled_turn':(['gf','ga','bf','ba','ca','cfa'],[.8,.55,0,0,.2,0],[.2,0,-.04,-.15,-1,-2],[1.5,1.5,.04,.15,1,2]),
 'body_slip':(['gf','ga','bf','ba','ca','sl'],[.8,.55,0,0,.2,0],[.2,0,-.04,-.15,-1,-.15],[1.5,1.5,.04,.15,1,.15]),
 'wheel_deadzone':(['gw','ell','dw','bf','ba'],[.85,.23,.01,0,0],[.2,.1,0,-.04,-.15],[1.5,.7,.08,.04,.15]),
}
def motion(p,u,family):
 v=u[:,0];a=u[:,1];par=dict(zip(SPECS[family][0],p))
 if family=='wheel_deadzone':
  gw,ell,dw,bf,ba=p;r=v+ell*a/2;l=v-ell*a/2
  r=gw*np.sign(r)*np.maximum(np.abs(r)-dw,0);l=gw*np.sign(l)*np.maximum(np.abs(l)-dw,0)
  return (r+l)/2+bf,(r-l)/ell+ba,np.zeros_like(v)
 gf,ga,bf,ba=p[:4];f=gf*v+bf;w=ga*a+ba
 if family in ['cubic_turn','coupled_turn','body_slip']:w+=par['ca']*a**3
 if family=='coupled_turn':w+=par['cfa']*v*a
 if family=='deadzone_turn':w=ga*np.sign(a)*np.maximum(np.abs(a)-par['da'],0)+ba
 if family=='smooth_turn':w+=par['na']*np.tanh(a/par['sa'])
 lateral=par.get('sl',0)*f
 return f,w,lateral

def make_windows(ids,H=25,stride=1):
 initial=[];targets=[];inputs=[]
 for i in ids:
  z,u=G[i]
  for s in range(0,len(z)-H,stride):
   initial.append(z[s]);targets.append(z[s+1:s+H+1]);inputs.append(u[s:s+H])
 return np.array(initial),np.array(targets),np.array(inputs)

def rollout(p,family,data):
 z,t,u=data;z=z.copy();out=np.empty_like(t)
 for k in range(t.shape[1]):
  f,w,l=motion(p,u[:,k],family);dp=TS*w
  angle=z[:,2]+(0 if family=='linear_euler' else dp/2)
  # exact arc equivalent using sinc; stable at zero angular rate
  fac=1 if family=='linear_euler' else np.sinc(dp/(2*np.pi))
  z[:,0]+=TS*fac*(f*np.cos(angle)-l*np.sin(angle));z[:,1]+=TS*fac*(f*np.sin(angle)+l*np.cos(angle));z[:,2]+=dp
  out[:,k]=z
 return out

def fit(family,ids,start=None,weight=.15):
 names,p0,lo,hi=SPECS[family];data=make_windows(ids);p0=p0 if start is None else start
 def fun(p):
  r=rollout(p,family,data)-data[1];r[:,:,2]*=weight;return r.ravel()
 sol=least_squares(fun,p0,bounds=(lo,hi),max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10,x_scale='jac')
 return sol.x,{'cost':float(sol.cost),'nfev':sol.nfev,'success':bool(sol.success),'optimality':float(sol.optimality)}

def metrics(p,family,ids,H=25):
 data=make_windows(ids,H);r=rollout(p,family,data)-data[1]
 return {'x':float(np.sqrt(np.mean(r[:,:,0]**2))),'y':float(np.sqrt(np.mean(r[:,:,1]**2))),'phi':float(np.sqrt(np.mean(r[:,:,2]**2)))}

def full_metric(p,family,ids):
 data=make_windows(ids,149);r=rollout(p,family,data)-data[1]
 return np.sqrt(np.mean(r*r,axis=(0,1))).tolist()

if __name__=='__main__':
 results={};tic=time.time()
 for fam in SPECS:
  p,info=fit(fam,[0,1,2]);cv=[]
  for test in range(3):
   train=[i for i in range(3) if i!=test];q,inf=fit(fam,train)
   cv.append({'test_trajectory':test+1,'parameters':q.tolist(),'metrics':metrics(q,fam,[test]),'info':inf})
  results[fam]={'names':SPECS[fam][0],'parameters':p.tolist(),'info':info,'training':metrics(p,fam,[0,1,2]),'full_trajectory_training':full_metric(p,fam,[0,1,2]),'cv':cv,'cv_x':float(np.sqrt(np.mean([v['metrics']['x']**2 for v in cv])))}
  print(fam,'params',p,'train',results[fam]['training'],'CV X',results[fam]['cv_x'],'full',results[fam]['full_trajectory_training'],'time',time.time()-tic,flush=True)
  with open('fit_results.json','w') as f:json.dump(results,f,indent=2)
