from fit_models import *
from search_terms import ssim,met
from fit_extended import exsim
# Parameter slots: c,a,b,g,w,F,s,h,q,r,d. Their meaning depends on family.
FNAMES=['trig_exponential','polynomial','rational','static_blend','trig_linear']
@njit
def facc(y,v,u,p,f):
 c,a,b,g,w,F,s,h,q,r,d=p
 damp=b*np.exp(min(max(-h*y,-40.),40.))
 if f==1:
  force=c-a*y+w*y*y*y+q*y*y+g*u
 elif f==2:
  force=c-a*y/(1+w*y*y)**r+g*u+q*y*y/(1+w*y*y)
 else:
  force=c-a*np.sin(w*y)+q*(np.cos(w*y)-1)+g*u
  if f==4:damp=b-h*y
 moving=force-damp*v-F*np.tanh(v/s)
 if f==3:
  gate=np.exp(-(v/d)**2)
  threshold=r
  st=.5*(force-threshold+np.sqrt((force-threshold)**2+.01))-.5*(-force-threshold+np.sqrt((-force-threshold)**2+.01))
  return (1-gate)*moving+gate*(st-100*v)
 return moving
@njit
def fsim(p,f,A,L):
 out=np.zeros((A.shape[0],A.shape[1],2))
 for j in range(A.shape[0]):
  y,v=A[j,0,0],A[j,0,1];out[j,0,0]=y;out[j,0,1]=v
  for k in range(L[j]-1):
   u=A[j,k,2];a1=facc(y,v,u,p,f);k1=v
   a2=facc(y+.005*k1,v+.005*a1,u,p,f);k2=v+.005*a1
   a3=facc(y+.005*k2,v+.005*a2,u,p,f);k3=v+.005*a2
   a4=facc(y+.01*k3,v+.01*a3,u,p,f);k4=v+.01*a3
   y+=.01/6*(k1+2*k2+2*k3+k4);v+=.01/6*(a1+2*a2+2*a3+a4)
   if not np.isfinite(y) or not np.isfinite(v) or abs(y)>1000 or abs(v)>1000:
    for kk in range(k+1,L[j]):out[j,kk,0]=1000;out[j,kk,1]=1000
    break
   out[j,k+1,0]=y;out[j,k+1,1]=v
 return out

def fmet(p,f):
 tr=fsim(p,f,A,L);va=fsim(p,f,Av,Lv)
 return dict(train_rmse=float(np.sqrt(np.mean((tr[:,:,0]-A[:,:,0])[M]**2))),val_rmse=float(np.sqrt(np.mean((va[:,:,0]-Av[:,:,0])[Mv]**2))),val_per_trajectory=[float(np.sqrt(np.mean((va[j,1:l,0]-Av[j,1:l,0])**2))) for j,l in enumerate(Lv)])

def fit_one(init,f,active,lo,hi,joined=False):
 def unpack(z):p=init.copy();p[active]=z;return p
 def res(z):
  p=unpack(z);e=(fsim(p,f,A,L)[:,:,0]-A[:,:,0])[M]
  if joined:e=np.r_[e,(fsim(p,f,Av,Lv)[:,:,0]-Av[:,:,0])[Mv]]
  return e
 op=least_squares(res,init[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return unpack(op.x),op
if __name__=='__main__':
 results={};TR=json.load(open('term_results.json'));ER=json.load(open('extended_results.json'))
 for f,name in enumerate(FNAMES):
  src=TR['cubic_friction_1' if f==1 else 'sine_friction_1']['p'];init=np.r_[src[:7],src[7]/src[2],0.,1.,.2]
  if f==4:init[7]=src[7]
  if f==2:
   init=np.array([2,110,1.8,28,.12,20,.2,.25,0,2,.2])
  if f==3:
   src=ER['smooth_stiction']['p'];init=np.r_[src[:7],.25,0,src[7],src[8]]
  active=np.array([0,1,2,3,4,5,7,8]+([9] if f==2 else [6,9,10] if f==3 else []))
  lo=np.array([-10,1,.05,1,.4,0,.12,-1,-30,.6,.06]);hi=np.array([10,300,30,100,1.6,60,5,1,30,5,2.])
  if f==1:lo[4]=0;hi[4]=50
  if f==2:lo[4]=.005;hi[4]=2;hi[9]=8
  if f==3:lo[9]=0;hi[9]=50
  pp,op=fit_one(init,f,active,lo,hi);m=fmet(pp,f)
  print('TRAIN',name,pp,m,flush=True)
  final,opf=fit_one(pp,f,active,lo,hi,True);mf=fmet(final,f)
  print('JOINED',name,final,mf,flush=True)
  results[name]={'family':f,'initial':init.tolist(),'active':active.tolist(),'bounds':[lo.tolist(),hi.tolist()],'train_p':pp.tolist(),'train_nfev':op.nfev,'selection_metrics':m,'p':final.tolist(),'joined_nfev':opf.nfev,'refit_metrics':mf}
  json.dump(results,open('final_results.json','w'),indent=2)
