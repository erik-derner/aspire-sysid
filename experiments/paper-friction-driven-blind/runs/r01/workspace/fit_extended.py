from fit_models import *
BASE=json.load(open('fit_results.json'))
ENAMES=['asymmetric','stribeck','smooth_stiction','karnopp','input_asymmetric','input_deadzone','quadratic_drag','mixed_restoring','linear_friction','saturating_cubic']
@njit
def exacc(y,v,u,p,f):
 c,a,b,g,w,F,s=p[:7]
 force=c-a*np.sin(w*y)+g*u
 t=np.tanh(v/s)
 if f==0:return force-b*v-F*t-p[7]*t*t
 if f==1:return force-b*v-(F+p[7]*np.exp(-(v/p[8])**2))*t
 if f==2:
  z=np.exp(-(v/p[8])**2)
  # soft static force threshold, sharpness fixed to 0.1 acceleration unit
  st=.5*((force-p[7])+np.sqrt((force-p[7])**2+.01))-.5*((-force-p[7])+np.sqrt((-force-p[7])**2+.01))
  return (1-z)*(force-b*v-F*t)+z*(st-100*v)
 if f==3:
  if abs(v)<p[8]:return np.sign(force)*max(abs(force)-p[7],0)-100*v
  return force-b*v-F*np.sign(v)
 if f==4:return force+p[7]*abs(u)-b*v-F*t
 if f==5:
  uu=.5*((u-p[7])+np.sqrt((u-p[7])**2+p[8]**2))-.5*((-u-p[7])+np.sqrt((-u-p[7])**2+p[8]**2))
  return c-a*np.sin(w*y)+g*uu-b*v-F*t
 if f==6:return force-b*v-F*t-p[7]*v*abs(v)
 if f==7:return force-p[7]*y-b*v-F*t
 if f==8:return c-a*y+g*u-b*v-F*t
 # rational bounded restoring: cubic-like Taylor term without unstable sign reversal
 return c-a*y/(1+p[7]*y*y)+g*u-b*v-F*t
@njit
def exsim(p,f,A,lengths):
 out=np.zeros((A.shape[0],A.shape[1],2))
 for j in range(A.shape[0]):
  y,v=A[j,0,0],A[j,0,1];out[j,0,0]=y;out[j,0,1]=v
  for k in range(lengths[j]-1):
   u=A[j,k,2];a1=exacc(y,v,u,p,f);k1=v
   a2=exacc(y+.005*k1,v+.005*a1,u,p,f);k2=v+.005*a1
   a3=exacc(y+.005*k2,v+.005*a2,u,p,f);k3=v+.005*a2
   a4=exacc(y+.01*k3,v+.01*a3,u,p,f);k4=v+.01*a3
   y+=.01/6*(k1+2*k2+2*k3+k4);v+=.01/6*(a1+2*a2+2*a3+a4)
   if not np.isfinite(y) or not np.isfinite(v) or abs(y)>1000 or abs(v)>1000:
    for kk in range(k+1,lengths[j]):out[j,kk,0]=1000;out[j,kk,1]=1000
    break
   out[j,k+1,0]=y;out[j,k+1,1]=v
 return out

def exres(p,f):return (exsim(p,f,A,L)[:,:,0]-A[:,:,0])[M]
def exmet(p,f):
 tr=exsim(p,f,A,L);va=exsim(p,f,Av,Lv)
 return {'train_rmse':float(np.sqrt(np.mean((tr[:,:,0]-A[:,:,0])[M]**2))), 'val_rmse':float(np.sqrt(np.mean((va[:,:,0]-Av[:,:,0])[Mv]**2))), 'val_per_trajectory':[float(np.sqrt(np.mean((va[j,1:l,0]-Av[j,1:l,0])**2))) for j,l in enumerate(Lv)],'train_per_trajectory':[float(np.sqrt(np.mean((tr[j,1:l,0]-A[j,1:l,0])**2))) for j,l in enumerate(L)]}

if __name__=='__main__':
 results={}
 for f,name in enumerate(ENAMES):
  q=BASE['sine_friction']['p'];lo=[-10,1,0,1,.4,0,.12];hi=[10,300,30,100,1.6,60,5]
  extras=[[0],[3,2],[20,.3],[20,.15],[0],[.1,.1],[0],[0],[],[.2]][f]
  elo=[[-15],[0,.2],[0,.05],[0,.03],[-20],[0,.02],[-.05],[-80],[],[0]][f]
  ehi=[[15],[40,8],[50,2],[50,1],[20],[2,1],[1],[80],[],[1]][f]
  p=np.r_[q,extras];bounds=(lo+elo,hi+ehi)
  if f>=8:p[1]=110
  # Frequency is redundant for nontrigonometric models; remove it from optimization.
  active=np.array([i for i in range(len(p)) if not(f>=8 and i==4)])
  def restore(z):pp=p.copy();pp[active]=z;return pp
  z0=p[active]
  opt=least_squares(lambda z:exres(restore(z),f),z0,bounds=(np.array(bounds[0])[active],np.array(bounds[1])[active]),x_scale='jac',diff_step=1e-4 if f==3 else None,max_nfev=300,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  pp=restore(opt.x);m=exmet(pp,f)
  print(name,pp,m,flush=True)
  results[name]={'family':f,'p':pp.tolist(),'initial':p.tolist(),'bounds':bounds,'active':active.tolist(),'nfev':opt.nfev,'metrics':m}
  json.dump(results,open('extended_results.json','w'),indent=2)
