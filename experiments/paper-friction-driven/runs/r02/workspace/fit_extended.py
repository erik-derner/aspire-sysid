import numpy as np,json,time
from scipy.optimize import least_squares,differential_evolution
from numba import njit
from fit_models import load,stats
@njit
def acc(t,w,u,p,f):
 a,g,b,c,v,fs=p[:6]
 D=a*u-g*np.sin(t)
 if f==8 or f==12:D=a*p[6]*np.tanh(u/p[6])-g*np.sin(t)
 if f==9:D=a*u-g*np.sin(t)*(1+p[6]*np.sin(t))
 if f==10 or f==11:D=a*u-g*np.sin(t)*(1+p[6]*np.cos(t)+p[7]*np.sin(t))
 cf=c
 if f==11:cf+=p[8]*np.tanh(w/v)
 if f==12:cf+=p[7]*np.tanh(w/v)
 if f==13:
  h=max(1-abs(w)/v,0.)
  return (1-h)*(D-b*w-c*np.sign(w))+h*(D-min(max(D,-fs),fs)-p[6]*w)
 if f==14:
  h=max(1-(w/v)**2,0.)**2
  return (1-h)*(D-b*w-c*np.sign(w))+h*(D-min(max(D,-fs),fs)-p[6]*w)
 if f==15:
  # weakening, bounded viscous drag plus directional dry friction
  cf+=p[8]*np.tanh(w/v)
  return D-b*w/(1+p[6]*abs(w))-cf*np.tanh(w/v)-np.exp(-(w/v)**2)*min(max(D,-fs),fs)
 return D-b*w-cf*np.tanh(w/v)-np.exp(-(w/v)**2)*min(max(D,-fs),fs)
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
 tr,rows,lens=load('data/train.csv');va,vr,vl=load('data/val.csv');orig=json.load(open('fit_results.json'));res={}
 for f in [8,9,10,11,12,13,14]:
  p=orig['1']['p'].copy();lo=[10,50,0,8,.15,1];hi=[50,180,8,45,3,45]
  if f==8:p+=[8];lo+=[1];hi+=[100]
  if f==9:p+=[0];lo+=[-.5];hi+=[.5]
  if f in [10,11]:p+=[.05,0];lo+=[-.4,-.4];hi+=[.4,.4]
  if f==11:p+=[-1];lo+=[-7];hi+=[7]
  if f==12:p+=[8,-1];lo+=[1,-7];hi+=[100,7]
  if f in [13,14]:p[4]=.6;p+=[50];lo[4]=.15;hi[4]=3;lo+=[5];hi+=[150]
  start=time.time()
  fit=least_squares(lambda p:sim(p,f,rows,lens)-rows[:,0],p,bounds=(lo,hi),diff_step=1e-4,max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  r={'p':fit.x.tolist(),'initial':p,'bounds':[lo,hi],'train':score(fit.x,f,rows,lens),'val':score(fit.x,f,vr,vl),'nfev':fit.nfev}
  res[str(f)]=r;print('EXT',f,json.dumps(r),'seconds',time.time()-start,flush=True)
  json.dump(res,open('extended_results.json','w'),indent=2)
