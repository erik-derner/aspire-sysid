import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
tr=pd.read_csv('data/train.csv').values;va=pd.read_csv('data/val.csv').values
# columns y,x1,x2,dy
@njit
def features(y,u,v,powers,kind):
 if kind==0:z=(y-1.3)/.3
 elif kind==1:z=np.sqrt(max(y-.99,1e-8))
 else:z=np.log(max(y-.98,.001))
 return z**powers[:,0]*u**powers[:,1]*v**powers[:,2]
@njit
def sim(co,d,powers,kind,teacher=False):
 yy=np.empty(len(d)); yy[0]=d[0,0]
 for k in range(len(d)-1):
  y=d[k,0] if teacher else yy[k];u=d[k,1]/70;v=d[k,2]/20
  a=np.dot(co,features(y,u,v,powers,kind));b=np.dot(co,features(y+2.5*a,u,v,powers,kind));c=np.dot(co,features(y+2.5*b,u,v,powers,kind));e=np.dot(co,features(y+5*c,u,v,powers,kind));yy[k+1]=y+5/6*(a+2*b+2*c+e)
  if not np.isfinite(yy[k+1]) or abs(yy[k+1])>100: yy[k+1:]=100;break
 return yy[1:]-d[1:,0]
def fit(label,powers,kind=0):
 powers=np.array(powers);X=np.array([features(y,u/70,v/20,powers,kind) for y,u,v,dy in tr]); co=np.linalg.lstsq(X,tr[:,3],rcond=None)[0];start=co.copy()
 one=least_squares(lambda c:sim(c,tr,powers,kind,True),co,max_nfev=100,ftol=1e-10,xtol=1e-10,gtol=1e-10);co=one.x
 res=least_squares(lambda c:sim(c,tr,powers,kind),co,max_nfev=180,ftol=1e-9,xtol=1e-9,gtol=1e-9);co=res.x
 rt=np.sqrt(np.mean(sim(co,tr,powers,kind)**2));rv=np.sqrt(np.mean(sim(co,va,powers,kind)**2));dr=np.sqrt(np.mean((X@co-tr[:,3])**2));V=np.array([features(y,u/70,v/20,powers,kind) for y,u,v,dy in va]);dv=np.sqrt(np.mean((V@co-va[:,3])**2)); print(label,'dim',len(co),'roll',rt,rv,'deriv',dr,dv,'nfev',res.nfev,flush=True)
 return dict(label=label,powers=powers.tolist(),kind=kind,start=start.tolist(),onestep=one.x.tolist(),coefficients=co.tolist(),rt=rt,rv=rv,dr=dr,dv=dv)
base=json.load(open('poly_results.json'));out=[]
for kind,deg in [('raw',2),('raw',3),('sqrt',2),('sqrt',3)]:
 item=next(q for q in base if q['kind']==kind and q['degree']==deg);out.append(fit(kind+str(deg),item['powers'],0 if kind=='raw' else 1))
for label,powers in [
 ('bilinear',[(0,0,0),(1,0,0),(0,0,1),(1,1,0)]),
 ('bilinear_quad',[(0,0,0),(1,0,0),(0,0,1),(1,1,0),(2,0,0),(0,1,0),(0,2,0)]),
 ('bilinear_cubic',[(0,0,0),(1,0,0),(0,0,1),(1,1,0),(2,0,0),(0,1,0),(0,2,0),(1,2,0),(3,0,0)]),
 ('inputgain',[(0,0,0),(1,0,0),(0,0,1),(1,1,0),(2,0,0),(0,1,0),(0,2,0),(1,2,0),(1,0,1),(0,1,1),(0,0,2)]),
 ('sqrt_bilinear',[(0,0,0),(1,0,0),(0,0,1),(1,1,0),(0,1,0),(0,2,0)])]:
 out.append(fit(label,powers,1 if label.startswith('sqrt') else 0))
json.dump(out,open('dynamic_results.json','w'),indent=2)
