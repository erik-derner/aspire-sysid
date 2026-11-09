import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
from fit_models import load
@njit
def acc(t,w,u,p,f):
 a,g,b,c,tau=p[:5];D=a*u-g*np.sin(t)-b*w
 if f==31:D=a*u-g*np.sin(t)*(1+p[6]*np.cos(t))-b*w
 if f==32:D=a*p[6]*np.tanh(u/p[6])-g*np.sin(t)-b*w
 d=0. if f==30 else p[5]
 return D-min(max(D+w/tau,-c-d),c-d)
@njit
def sim(p,f,rows,lens):
 out=np.empty(len(rows));off=0
 for L in lens:
  t,w=rows[off,:2];out[off]=t
  for i in range(off,off+L-1):
   u=rows[i,2]
   z1=acc(t,w,u,p,f);v1=w
   z2=acc(t+.005*v1,w+.005*z1,u,p,f);v2=w+.005*z1
   z3=acc(t+.005*v2,w+.005*z2,u,p,f);v3=w+.005*z2
   z4=acc(t+.01*v3,w+.01*z3,u,p,f);v4=w+.01*z3
   t+=.01/6*(v1+2*v2+2*v3+v4);w+=.01/6*(z1+2*z2+2*z3+z4)
   if not np.isfinite(t) or abs(t)>100 or abs(w)>500:out[i+1:]=1000;return out
   out[i+1]=t
  off+=L
 return out

def score(p,f,rows,lens):
 r=sim(p,f,rows,lens)-rows[:,0];off=0;s=[]
 for l in lens:s.append(float(np.sqrt(np.mean(r[off+1:off+l]**2))));off+=l
 return float(np.sqrt(np.sum(r*r)/(len(r)-len(lens)))),s
if __name__=='__main__':
 _,rows,lens=load('data/train.csv');_,vr,vl=load('data/val.csv');res={}
 for f in [30,33,31,32]:
  p=[28,110,1.6,21,.015];lo=[10,50,0,8,.005];hi=[50,180,8,45,.15]
  if f!=30:p+=[2];lo+=[-7];hi+=[7]
  if f==31:p+=[.05];lo+=[-.6];hi+=[.6]
  if f==32:p+=[8];lo+=[1];hi+=[100]
  fit=least_squares(lambda p:sim(p,f,rows,lens)-rows[:,0],p,bounds=(lo,hi),diff_step=1e-4,max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  r={'p':fit.x.tolist(),'initial':p,'bounds':[lo,hi],'train':score(fit.x,f,rows,lens),'val':score(fit.x,f,vr,vl),'nfev':fit.nfev};res[str(f)]=r;print('PROJECT',f,json.dumps(r),flush=True);json.dump(res,open('projection_results.json','w'),indent=2)
