import numpy as np,pandas as pd,json
import fit_models as F
from scipy.optimize import least_squares
from sklearn.linear_model import LassoLarsIC
D=pd.read_csv('helper_transitions.csv');print(D.columns.tolist())
R=json.load(open('fit_results.json'))
for name in ['midpoint','affine','deadzone','phase']:
 p=np.array(R[name]['parameters']);e=[];phase=[];cs=[]
 for g in F.traj:
  pred=F.step(name,p,g[:-1,:3],g[:-1,3],g[:-1,4]);r=pred-g[1:,:3];r[:,2]=np.arctan2(np.sin(r[:,2]),np.cos(r[:,2]));e.append(r);phase.extend(np.arange(len(g)-1)%5);cs.append(g[:-1,3:])
 e=np.concatenate(e);phase=np.array(phase);cs=np.concatenate(cs)
 print('\n',name,'one step RMS x y phi',np.sqrt(np.mean(e*e,axis=0)))
 print('phase rms',[(k,np.sqrt(np.mean(e[phase==k]**2,axis=0)).tolist()) for k in range(5)])
 print('lag1 residual corr', [np.corrcoef(e[:-1,j],e[1:,j])[0,1] for j in range(3)])
 print('correlation with vf va va3 sign va', [[round(np.corrcoef(e[:,j],q)[0,1],4) for q in [cs[:,0],cs[:,1],cs[:,1]**3,np.sign(cs[:,1])]] for j in range(3)])
 print('prefix25 x each traj', [F.full_metrics(name,p,[g[:26]])[0] for g in F.traj])
# Sparse command-response library in body coordinates, block averaged at phases 2-4.
# Grouping prevents counting within-block correlated residuals as independent.
rows=[]
for g in F.traj:
 for k in range(0,145,5):
  ix=np.arange(k+2,k+5);dp=g[ix+1,2]-g[ix,2];h=g[ix,2]+.5*dp
  v=((g[ix+1,0]-g[ix,0])*np.cos(h)+(g[ix+1,1]-g[ix,1])*np.sin(h))/.2
  rows.append([g[k,3],g[k,4],np.mean(v),np.mean(dp/.2)])
a=np.array(rows);u,w=a[:,:2].T
X=np.c_[u,w,u*u,w*w,u*w,w**3,u*w*w,np.sign(w)];names=['v_f','v_a','v_f**2','v_a**2','v_f*v_a','v_a**3','v_f*v_a**2','sign(v_a)'];sc=np.std(X,axis=0)
for j,name in [(2,'forward'),(3,'angular')]:
 model=LassoLarsIC(criterion='bic').fit(X/sc,a[:,j]);print('sparse BIC',name,'intercept',model.intercept_,'terms',list(zip(names,model.coef_/sc)),'alpha',model.alpha_)
