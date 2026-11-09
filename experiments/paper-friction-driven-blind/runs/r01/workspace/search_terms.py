from fit_models import *
R=json.load(open('sensitivity_results.json'))
TERMS=['y**2','y*x1','y**2*x1','x2*y','x2*y**2','x2*Abs(x2)','x2**3','cos(w*y)-1','x1*cos(w*y)','x2*cos(w*y)']
@njit
def feat(y,v,u,w,j):
 if j==0:return y*y
 if j==1:return y*v
 if j==2:return y*y*v
 if j==3:return u*y
 if j==4:return u*y*y
 if j==5:return u*abs(u)
 if j==6:return u*u*u
 if j==7:return np.cos(w*y)-1
 if j==8:return v*np.cos(w*y)
 return u*np.cos(w*y)
@njit
def accel(y,v,u,p,cubic,terms):
 force=p[0]-p[1]*y+p[4]*y**3 if cubic else p[0]-p[1]*np.sin(p[4]*y)
 out=force-p[2]*v+p[3]*u-p[5]*np.tanh(v/p[6])
 for k in range(len(terms)):out+=p[k+7]*feat(y,v,u,p[4] if not cubic else 1.,terms[k])
 return out
@njit
def ssim(p,cubic,terms,A,L):
 out=np.zeros((A.shape[0],A.shape[1],2))
 for j in range(A.shape[0]):
  y,v=A[j,0,0],A[j,0,1];out[j,0,0]=y;out[j,0,1]=v
  for k in range(L[j]-1):
   u=A[j,k,2];a1=accel(y,v,u,p,cubic,terms);k1=v
   a2=accel(y+.005*k1,v+.005*a1,u,p,cubic,terms);k2=v+.005*a1
   a3=accel(y+.005*k2,v+.005*a2,u,p,cubic,terms);k3=v+.005*a2
   a4=accel(y+.01*k3,v+.01*a3,u,p,cubic,terms);k4=v+.01*a3
   y+=.01/6*(k1+2*k2+2*k3+k4);v+=.01/6*(a1+2*a2+2*a3+a4)
   if not np.isfinite(y) or not np.isfinite(v) or abs(y)>1000 or abs(v)>1000:
    for kk in range(k+1,L[j]):out[j,kk,0]=1000;out[j,kk,1]=1000
    break
   out[j,k+1,0]=y;out[j,k+1,1]=v
 return out

def met(p,cubic,terms):
 tr=ssim(p,cubic,terms,A,L);va=ssim(p,cubic,terms,Av,Lv)
 return dict(train_rmse=float(np.sqrt(np.mean((tr[:,:,0]-A[:,:,0])[M]**2))),val_rmse=float(np.sqrt(np.mean((va[:,:,0]-Av[:,:,0])[Mv]**2))),val_per_trajectory=[float(np.sqrt(np.mean((va[j,1:l,0]-Av[j,1:l,0])**2))) for j,l in enumerate(Lv)])
if __name__=='__main__':
 results={}
 for cubic in [False,True]:
  name='cubic_friction' if cubic else 'sine_friction';base=np.array(R[name+'_w0.2']['p']);br=json.load(open('fit_results.json'))[name];blo=br['bounds'][0];bhi=br['bounds'][1]
  for j,term in enumerate(TERMS):
   if cubic and j==7:continue
   terms=np.array([j]);init=np.r_[base,0.];active=np.array([i for i in range(8) if i!=6]);lo=np.r_[blo,-50.];hi=np.r_[bhi,50.]
   def unpack(z):p=init.copy();p[active]=z;return p
   op=least_squares(lambda z:(ssim(unpack(z),cubic,terms,A,L)[:,:,0]-A[:,:,0])[M],init[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=200,ftol=1e-9,xtol=1e-9,gtol=1e-9)
   p=unpack(op.x);m=met(p,cubic,terms);print(name,term,p,m,flush=True)
   results[name+'_'+str(j)]={'p':p.tolist(),'initial':init.tolist(),'cubic':cubic,'terms':terms.tolist(),'metrics':m}
 json.dump(results,open('term_results.json','w'),indent=2)
