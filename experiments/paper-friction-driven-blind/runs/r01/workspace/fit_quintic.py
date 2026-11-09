from fit_models import *
from fit_final import FNAMES
R=json.load(open('final_results.json'))
@njit
def qacc(y,v,u,p):
 c,a,b,g,e,F,s,h,q,k=p
 return c-a*y+q*y*y+e*y**3-k*y**5-b*np.exp(min(max(-h*y,-40.),40.))*v+g*u-F*np.tanh(v/s)
@njit
def qsim(p,A,L):
 out=np.zeros((A.shape[0],A.shape[1],2))
 for j in range(A.shape[0]):
  y,v=A[j,0,0],A[j,0,1];out[j,0,0]=y;out[j,0,1]=v
  for k in range(L[j]-1):
   u=A[j,k,2];a1=qacc(y,v,u,p);k1=v
   a2=qacc(y+.005*k1,v+.005*a1,u,p);k2=v+.005*a1
   a3=qacc(y+.005*k2,v+.005*a2,u,p);k3=v+.005*a2
   a4=qacc(y+.01*k3,v+.01*a3,u,p);k4=v+.01*a3
   y+=.01/6*(k1+2*k2+2*k3+k4);v+=.01/6*(a1+2*a2+2*a3+a4)
   if not np.isfinite(y) or not np.isfinite(v) or abs(y)>1000 or abs(v)>1000:
    for kk in range(k+1,L[j]):out[j,kk,0]=1000;out[j,kk,1]=1000
    break
   out[j,k+1,0]=y;out[j,k+1,1]=v
 return out

def qmet(p):
 tr=qsim(p,A,L);va=qsim(p,Av,Lv)
 return dict(train_rmse=float(np.sqrt(np.mean((tr[:,:,0]-A[:,:,0])[M]**2))),val_rmse=float(np.sqrt(np.mean((va[:,:,0]-Av[:,:,0])[Mv]**2))),val_per_trajectory=[float(np.sqrt(np.mean((va[j,1:l,0]-Av[j,1:l,0])**2))) for j,l in enumerate(Lv)])
if __name__=='__main__':
 src=R['polynomial']['train_p'];init=np.r_[src[:9],.5];lo=np.array([-10,1,.05,1,0,0,.12,-1,-30,.005]);hi=np.array([10,300,30,100,50,60,5,1,30,8]);active=np.array([0,1,2,3,4,5,7,8,9])
 def fit(initial,joined):
  def unpack(z):p=initial.copy();p[active]=z;return p
  def fun(z):
   p=unpack(z);e=(qsim(p,A,L)[:,:,0]-A[:,:,0])[M]
   if joined:e=np.r_[e,(qsim(p,Av,Lv)[:,:,0]-Av[:,:,0])[Mv]]
   return e
  op=least_squares(fun,initial[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  return unpack(op.x),op.nfev
 pp,n=fit(init,False);m=qmet(pp);print('TRAIN',pp,m,flush=True)
 final,nf=fit(pp,True);mf=qmet(final);print('JOINED',final,mf,flush=True)
 json.dump(dict(initial=init.tolist(),bounds=[lo.tolist(),hi.tolist()],active=active.tolist(),train_p=pp.tolist(),train_nfev=n,selection_metrics=m,p=final.tolist(),joined_nfev=nf,refit_metrics=mf),open('quintic_results.json','w'),indent=2)
