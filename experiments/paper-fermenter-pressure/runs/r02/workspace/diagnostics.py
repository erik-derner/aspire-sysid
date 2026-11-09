import numpy as np,pandas as pd,json
from pathlib import Path
from fit_models import D,rollout,transitions
from sklearn.linear_model import Lasso
R=json.loads(Path('fit_results.json').read_text());lines=[]
def report(s):lines.append(str(s));print(s)
for label in ['linear','power','nozzle','resistance']:
 a=next(x for x in R if x['label']==label);t=np.array(a['parameters'])
 report('\n'+label)
 for name,d in D.items():
  sr=rollout(t,d,a['family'],a['valvekind'])-d[:,0];tr=transitions(t,d,a['family'],a['valvekind']);df=pd.DataFrame(d[:-1],columns=['p','valve','flow','dp']);df['simulation']=sr[:-1];df['transition']=tr
  report(name)
  for c,bins in [('p',[.97,1.1,1.3,1.5,1.7,1.9,2.3]),('valve',[0,30,50,65,75,85,100]),('flow',[0,10,15,20,25,35])]:
   report(df.groupby(pd.cut(df[c],bins),observed=True)[['simulation','transition']].agg(['mean','std','count']).to_string())
  report('RMSE consecutive 6 blocks: '+str([float(np.sqrt(np.mean(x*x))) for x in np.array_split(sr[1:],6)]))
  report('transition autocorrelations '+str([float(np.corrcoef(tr[:-j],tr[j:])[0,1]) for j in [1,2,3,5,10]]))
# Sparse polynomial diagnostic of mass balance: features q and z * pressure/valve monomials.
d=D['train'];z=d[:,0]-1;v=d[:,1]/100
labels=['flow']+[f'z**{i+1}*v**{j}' for i in range(3) for j in range(4)]
X=np.column_stack([d[:,2]]+[z**(i+1)*v**j for i in range(3) for j in range(4)])
scale=np.sqrt(np.mean(X**2,axis=0));target=np.r_[np.diff(d[:,0])/5,0];X=X[:-1];target=target[:-1]
for alpha in [1e-6,1e-5,1e-4]:
 fit=Lasso(alpha=alpha,fit_intercept=False,max_iter=200000,tol=1e-10).fit(X/scale,target);co=fit.coef_/scale
 report('\nLasso alpha '+str(alpha)+' coefficients '+str(dict(zip(labels,co.tolist()))))
 for name,d in D.items():
  z=d[:,0]-1;v=d[:,1]/100;XX=np.column_stack([d[:,2]]+[z**(i+1)*v**j for i in range(3) for j in range(4)])
  report(name+' derivative error '+str(np.sqrt(np.mean((XX[:-1]@co-np.diff(d[:,0])/5)**2))))
 # evaluate stability of continuous pressure/closure derivatives over observed-range grid
 z,v=np.meshgrid(np.linspace(0,1.2,101),np.linspace(0,1,101));dpdp=np.zeros_like(z);dpdv=np.zeros_like(z)
 for i in range(3):
  for j in range(4):
   cc=co[1+i*4+j];dpdp+=cc*(i+1)*z**i*v**j
   if j:dpdv+=cc*j*z**(i+1)*v**(j-1)
 report('max pressure derivative '+str(dpdp.max())+' min closure derivative '+str(dpdv.min())+' closed zero-flow derivative range '+str((dpdv.shape,float(np.min(sum(co[1+i*4+j]*np.linspace(0,1.2,101)**(i+1) for i in range(3) for j in range(4)))))))
Path('diagnostics.txt').write_text('\n'.join(lines))
