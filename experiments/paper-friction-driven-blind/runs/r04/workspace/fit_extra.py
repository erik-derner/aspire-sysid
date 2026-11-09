import numpy as np,json
from scipy.optimize import least_squares
from numba import njit
from fit_rollout import load
@njit
def acc(y,v,u,p,k):
 a,b,c,f,s=p[:5]
 force=-a*np.sin(y)+c*u
 if k==12:force=-a*np.sin(p[5]*y)+c*u+p[6]
 if k==13:force+=p[5]*y
 if k==14:force+=p[5]
 if k==15:force+=p[5]*u**3
 if k==16:force=-a*y+p[5]*y**3+c*u+p[6]
 if k==17:force=-a*np.sin(y+p[5])+c*u
 if k==18:force+=p[5]*v*abs(v)
 if k==19:force=-a*np.sin(p[5]*y)+c*u+p[6]
 if k in (9,12,16):fric=f*np.tanh(v/s)+max(-f,min(f,force))*(1-np.tanh(v/s)**2)
 elif k in (10,14,19):fric=max(-f,min(f,force+f*v/s))
 elif k==11:fric=f*np.tanh(v/s)+max(-f,min(f,force))*np.exp(-(v/s)**2)
 else:fric=f*np.tanh(v/s)
 return force-b*v-fric
@njit
def simx(a,p,k):
 out=np.empty((len(a),2));out[0,:]=a[0,:2]
 for i in range(len(a)-1):
  y,v=out[i];u=a[i,2]
  d1=acc(y,v,u,p,k);y2=y+.005*v;v2=v+.005*d1
  d2=acc(y2,v2,u,p,k);y3=y+.005*v2;v3=v+.005*d2
  d3=acc(y3,v3,u,p,k);y4=y+.01*v3;v4=v+.01*d3
  d4=acc(y4,v4,u,p,k)
  out[i+1,0]=y+.01/6*(v+2*v2+2*v3+v4);out[i+1,1]=v+.01/6*(d1+2*d2+2*d3+d4)
  if not np.isfinite(out[i+1,0]) or abs(out[i+1,0])>100:
   out[i+1:,:]=100.;break
 return out
def residual(p,k,groups):return np.concatenate([simx(a,p,k)[1:,0]-a[1:,0] for a in groups])
def score(p,k,g):return float(np.sqrt(np.mean(residual(p,k,g)**2)))
def main():
 tr=load('data/train.csv');va=load('data/val.csv');out={}
 base=[110.,1.8,28.,20.,.3];lo=[50.,0.,10.,5.,.1];hi=[200.,10.,50.,40.,3.]
 specs={'static_tanh':(9,[],[],[]),'static_clip':(10,[],[],[]),'static_gauss':(11,[],[],[]),'static_scaled':(12,[1.05,1.],[.7,-10.],[1.3,10.]),'mixed_restore':(13,[0.],[-40.],[40.]),'static_bias':(14,[1.],[-10.],[10.]),'nonlinear_input':(15,[0.],[-2.],[2.]),'static_cubic':(16,[15.,1.],[-5.,-10.],[30.,10.]),'shifted':(17,[0.],[-.2],[.2]),'quadratic_damp':(18,[0.],[-1.],[.15]),'clip_scaled':(19,[1.05,1.],[.7,-10.],[1.3,10.])}
 for name,(k,ps,ls,hs) in specs.items():
  best=None
  for s in [.15,.4,1.]:
   start=base+ps;start[4]=s
   fit=least_squares(residual,start,args=(k,tr),bounds=(lo+ls,hi+hs),x_scale='jac',max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-8)
   sc=score(fit.x,k,tr)
   print(name,s,sc,score(fit.x,k,va),fit.nfev,flush=True)
   if best is None or sc<best['train']:best={'kind':k,'p':fit.x.tolist(),'train':sc,'val':score(fit.x,k,va),'start':start,'lower':lo+ls,'upper':hi+hs,'nfev':fit.nfev,'status':fit.message}
  out[name]=best;print('BEST',name,best,flush=True)
  open('extra_results.json','w').write(json.dumps(out,indent=2))
if __name__=='__main__':main()
