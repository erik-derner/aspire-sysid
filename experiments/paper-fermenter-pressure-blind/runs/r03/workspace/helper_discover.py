import numpy as np, pandas as pd, json
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import OrthogonalMatchingPursuit
from scipy.optimize import least_squares
A=pd.read_csv('data/train.csv'); B=pd.read_csv('data/val.csv'); X=A[['y','x1','x2']].values; V=B[['y','x1','x2']].values; z=A.dy.values; w=B.dy.values
out=[]
def score(name,pred,pars=None,extra=None):
 pt,pv=pred; r=z-pt; rv=w-pv
 row={'name':name,'train_derivative_RMSE':float(np.sqrt(np.mean(r*r))),'val_derivative_RMSE':float(np.sqrt(np.mean(rv*rv))),'val_bias':float(rv.mean()),'parameters':pars,'extra':extra}
 out.append(row); print(name,row['train_derivative_RMSE'],row['val_derivative_RMSE'],pars)
 return row
def fit(name,F,G,names):
 c=np.linalg.lstsq(F,z,rcond=None)[0]; return score(name,(F@c,G@c),dict(zip(names,c.tolist())))
for dat in [A,B]:
 print('increment discrepancy',np.sqrt(np.mean((dat.dy.values[:-1]-np.diff(dat.y)/5)**2)))
mu=X.mean(0); scale=X.std(0); U=(X-mu)/scale; W=(V-mu)/scale
for d in range(1,6):
 poly=PolynomialFeatures(d); F=poly.fit_transform(U); G=poly.transform(W); names=poly.get_feature_names_out(['Y','U','V']).tolist()
 fit('poly'+str(d),F,G,names)
 if d in [2,3,4]:
  norm=np.linalg.norm(F,axis=0); Fs=F/norm; Gs=G/norm
  for k in [3,5,8,12,16]:
   if k>=F.shape[1]:continue
   m=OrthogonalMatchingPursuit(n_nonzero_coefs=k,fit_intercept=False).fit(Fs,z); c=m.coef_/norm
   score('omp_d%d_k%d'%(d,k),(F@c,G@c),{names[j]:float(c[j]) for j in np.where(c)[0]})
# raw additive/transformed libraries and variable relaxation interactions
for yt in ['y','log','sqrt','square','inv']:
 for xt in ['linear','log','sqrt','square','cube','inv','sat']:
  def design(T):
   y,x1,x2=T.T
   yh={'y':y,'log':np.log(y),'sqrt':np.sqrt(y),'square':y*y,'inv':1/y}[yt]
   if xt=='linear':h1,h2=x1,x2
   if xt=='log':h1,h2=np.log(x1),np.log(x2)
   if xt=='sqrt':h1,h2=np.sqrt(x1),np.sqrt(x2)
   if xt=='square':h1,h2=x1*x1,x2*x2
   if xt=='cube':h1,h2=x1**3,x2**3
   if xt=='inv':h1,h2=1/x1,1/x2
   if xt=='sat':h1,h2=x1/(20+x1),x2/(10+x2)
   return np.stack([np.ones(len(y)),yh,h1,h2],axis=1)
  fit('add_'+yt+'_'+xt,design(X),design(V),['one',yt,'x1_'+xt,'x2_'+xt])
# Generalized power additive and interactions: power arguments positive in supplied data
for kind in ['addpower','powrelax','powproduct','expadd','exp_relax']:
 def f(p,T):
  y,u,v=T.T;u=u/60;v=v/18
  if kind=='addpower':return p[0]+p[1]*y**p[4]+p[2]*u**p[5]+p[3]*v**p[6]
  if kind=='powrelax':return (p[0]+p[2]*u**p[5]+p[3]*v**p[6]-y**p[4])*np.exp(p[1])
  if kind=='powproduct':return p[0]+p[1]*y**p[4]+p[2]*u**p[5]*v**p[6]+p[3]*v**p[6]
  if kind=='expadd':return p[0]+p[1]*y+p[2]*np.exp(p[4]*u)+p[3]*np.exp(p[5]*v)
  if kind=='exp_relax':return p[0]+p[1]*y+p[2]*u+p[3]*v+p[4]*u*y+p[5]*v*y
 if kind=='powrelax': p0=[1,-4,0.1,0.1,1,1,1];lo=[-100,-15,-100,-100,-5,-3,-3];hi=[100,2,100,100,8,8,8]
 elif kind in ['addpower','powproduct']:p0=[0,-.02,.01,.01,1,1,1];lo=[-10,-10,-10,-10,-5,-3,-3];hi=[10,10,10,10,8,8,8]
 else:p0=[0,-.02,.01,.01,1,1] if kind=='expadd' else [0,-.02,.01,.01,0,0];lo=[-10]*len(p0);hi=[10]*len(p0)
 res=least_squares(lambda p:f(p,X)-z,p0,bounds=(lo,hi),max_nfev=2000,xtol=1e-11,ftol=1e-11,gtol=1e-11)
 score(kind,(f(res.x,X),f(res.x,V)),res.x.tolist(),{'success':bool(res.success),'cost':float(res.cost)})
json.dump({'normalization':{'mean':mu.tolist(),'scale':scale.tolist()},'results':out},open('helper_results.json','w'),indent=2)
