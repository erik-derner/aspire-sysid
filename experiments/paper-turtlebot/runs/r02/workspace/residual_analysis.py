import numpy as np,pandas as pd,json
import identify as I
from sklearn.linear_model import LassoCV
R=json.load(open('investigate_results.json'));F=json.load(open('fit_results.json'))
records={}
for label,key,mode in [('Euler','euler','xonly'),('Exact','bias','xhead'),('DeadZone','deadphase','xhead')]:
 p=np.array(R[key+'_'+mode]['parameters']);one=[];phases=[];commands=[];prefix=[];cvprefix=[]
 for i,(s,u) in enumerate(I.TRAJ):
  one.extend(I.step(s[:-1],u[:-1],p,key)-s[1:]);phases.extend(np.arange(len(s)-1)%5);commands.extend(u[:-1])
  cur=s[:1].copy();rr=[]
  for j in range(25):cur=I.step(cur,u[j:j+1],p,key);rr.append(cur[0]-s[j+1])
  prefix.append(np.sqrt(np.mean(np.array(rr)**2,axis=0)).tolist())
  pp=np.array(R[key+'_'+mode]['cv'][i]['parameters']);cur=s[:1].copy();rr=[]
  for j in range(25):cur=I.step(cur,u[j:j+1],pp,key);rr.append(cur[0]-s[j+1])
  cvprefix.append(np.sqrt(np.mean(np.array(rr)**2,axis=0)).tolist())
 one=np.array(one);phases=np.array(phases);commands=np.array(commands)
 records[label]={'one_step_rmse':np.sqrt(np.mean(one**2,axis=0)).tolist(),'phase_rmse':[np.sqrt(np.mean(one[phases==ph]**2,axis=0)).tolist() for ph in range(5)],'prefix_rmse':prefix,'cv_prefix_rmse':cvprefix,'angular_residual_command_correlation':np.corrcoef(one[:,2],commands[:,1])[0,1]}
 print(label,records[label])
# Sparse physically constructed diagnostic library on settled transitions only.
A=[];b=[];groups=[]
for i,(s,u) in enumerate(I.TRAJ):
 for k in range(len(s)-1):
  if k%5==0:continue
  vf,va=u[k];ph=s[k,2]
  A.append([va,va**3,np.sign(va),va*vf,np.sin(ph),np.cos(ph),vf,va*np.sin(ph),va*np.cos(ph)])
  b.append((s[k+1,2]-ph)/I.TS);groups.append(i)
A=np.array(A);b=np.array(b);scale=A.std(0);groups=np.array(groups)
folds=[(np.flatnonzero(groups!=g),np.flatnonzero(groups==g)) for g in range(3)]
l=LassoCV(alphas=np.logspace(-4,-1,40),cv=folds,max_iter=20000,tol=1e-9).fit(A/scale,b)
records['sparse_diagnostic']={'columns':['v_a','v_a**3','sign(v_a)','v_a*v_f','sin(phi)','cos(phi)','v_f','v_a*sin(phi)','v_a*cos(phi)'],'coefficients':(l.coef_/scale).tolist(),'intercept':l.intercept_,'alpha':l.alpha_,'training_rmse':float(np.sqrt(np.mean((l.predict(A/scale)-b)**2)))}
json.dump(records,open('residual_results.json','w'),indent=2)
print('sparse',records['sparse_diagnostic'])
