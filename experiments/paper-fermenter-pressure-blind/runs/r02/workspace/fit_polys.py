import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from scipy.linalg import lstsq
from sklearn.preprocessing import PolynomialFeatures
from numba import njit
@njit
def rollout(c,pw,yy,a,b):
 n=len(yy);res=np.empty(n-1);v=yy[0]
 for i in range(n-1):
  ks=np.empty(4)
  for s in range(4):
   z=v-1
   if s==1:z+=2.5*ks[0]
   if s==2:z+=2.5*ks[1]
   if s==3:z+=5*ks[2]
   vv=0.
   for j in range(len(c)):vv+=c[j]*z**pw[j,0]*a[i]**pw[j,1]*b[i]**pw[j,2]
   ks[s]=vv
  v+=5/6*(ks[0]+2*ks[1]+2*ks[2]+ks[3])
  if not np.isfinite(v) or abs(v)>100:
   for k in range(i,n-1):res[k]=1000
   return res
  res[i]=v-yy[i+1]
 return res

def design(d,pw):
 z=np.column_stack([d.y-1,d.x1/60,d.x2/20]);return np.prod(z[:,None,:]**pw[None,:,:],axis=2)
def score(c,pw,ds):
 out={}
 for fn,d in ds.items():
  r=rollout(c,pw,d.y.values,d.x1.values/60,d.x2.values/20);out[fn+'_roll']=np.mean(r*r)**.5;out[fn+'_der']=np.mean((design(d,pw)@c-d.dy.values)**2)**.5
 return out

def fit(d,pw,c):
 args=(pw,d.y.values,d.x1.values/60,d.x2.values/20)
 f=lambda v:rollout(v,*args)
 sol=least_squares(f,c,x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return sol

if __name__=='__main__':
 ds={n:pd.read_csv('data/'+n+'.csv') for n in ['train','val']};d=ds['train'];records=[]
 def save(label,pw,c,method,start=None):
  r={'label':label,'powers':pw.tolist(),'c':c.tolist(),'method':method,'start':None if start is None else start.tolist(),**score(c,pw,ds)};records.append(r);print({k:v for k,v in r.items() if k not in ['powers','c','start']});json.dump(records,open('fit_polys_results.json','w'),indent=2)
 for degree in [1,2,3]:
  p=PolynomialFeatures(degree).fit(np.zeros((1,3)));pw=p.powers_;X=design(d,pw);c=lstsq(X,d.dy)[0];save('poly'+str(degree)+'_der',pw,c,'derivative OLS')
  sol=fit(d,pw,c);save('poly'+str(degree)+'_roll',pw,sol.x,'rollout LS',c)
  if degree==1:continue
  # Greedy backward elimination: remove term producing lowest refitted derivative SSE each step.
  for count in range(len(pw)-1,3,-1):
   best=None
   for j in range(len(pw)):
    keep=np.arange(len(pw))!=j;xx=X[:,keep];cc=lstsq(xx,d.dy)[0];loss=np.sum((xx@cc-d.dy)**2)
    if best is None or loss<best[0]:best=(loss,keep,cc)
   _,keep,c=best;pw=pw[keep];X=X[:,keep]
   if count in [15,12,10,9,8,7,6,5,4]:
    save('sparse'+str(degree)+'_'+str(count)+'_der',pw,c,'backward OLS')
    sol=fit(d,pw,c);save('sparse'+str(degree)+'_'+str(count)+'_roll',pw,sol.x,'backward OLS then rollout LS',c)
