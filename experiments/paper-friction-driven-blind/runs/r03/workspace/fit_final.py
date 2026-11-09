import numpy as np,pandas as pd,json
from numba import njit
from scipy.optimize import least_squares
from helper_rollout_core import T,V,nt,nv,mT,mV
@njit
def acceleration(y,v,u,p,mode):
 a,b,c,d,e,w,h,j,s=p
 if mode==0:return a*np.sin(y)+h*np.cos(y)+b*v+c*u+d+e*np.tanh(v/w)*(1+j*np.cos(y))
 if mode==1:return a*y+h*y**3+j*y**5+b*v+c*u+d+e*np.tanh(v/w)
 F=a*np.sin(y)+h*np.cos(y)+b*v+c*u+d
 return F-e*np.tanh(v/w)-np.minimum(np.maximum(F,-s),s)*np.exp(-(v/j)**2)
@njit
def rollout(p,A,ns,mode):
 out=np.empty(A.shape[0]);vel=np.empty(A.shape[0]);start=0
 for n in ns:
  y=A[start,0];v=A[start,1];out[start]=y;vel[start]=v
  for z in range(start,start+n-1):
   u=A[z,2];a=acceleration(y,v,u,p,mode);b=acceleration(y+.005*v,v+.005*a,u,p,mode);c=acceleration(y+.005*(v+.005*a),v+.005*b,u,p,mode);d=acceleration(y+.01*(v+.005*b),v+.01*c,u,p,mode)
   y+=.01/6*(v+2*(v+.005*a)+2*(v+.005*b)+(v+.01*c));v+=.01/6*(a+2*b+2*c+d)
   out[z+1]=y;vel[z+1]=v
  start+=n
 return out,vel

def run():
 W=np.vstack([T,V]);nw=np.r_[nt,nv];mask=np.r_[mT,mV];D=pd.concat([pd.read_csv('data/train.csv'),pd.read_csv('data/val.csv')],ignore_index=True)
 wr=json.load(open('width_results.json')); sr=json.load(open('stick_results.json'))
 p0s=[next(r['params'] for r in wr if r['mode']==6 and r['width']==.3),next(r['params'] for r in wr if r['mode']==0 and r['width']==.3),sr[3]['params']]
 bounds=[([-180,-10,5,-15,-50,.3,-20,-.8,.1],[-50,0,50,15,0,.3,30,.8,20]),([-180,-10,5,-15,-50,.3,0,-10,.1],[-50,0,50,15,0,.3,40,0,20]),([-180,-10,5,-15,0,.09,-20,.05,1],[-50,0,50,15,60,3,30,4,60])]
 labels=['angle_friction','polynomial_friction','force_deadzone'];out=[]
 for mode in range(3):
  p0=np.array(p0s[mode]);ids=np.array([0,1,2,3,4,6,7] if mode<2 else list(range(9)));lo,hi=map(np.array,bounds[mode])
  def unpack(q):
   p=p0.copy();p[ids]=q;return p
  def fun(q):return (rollout(unpack(q),W,nw,mode)[0]-W[:,0])[mask]
  fit=least_squares(fun,p0[ids],bounds=(lo[ids],hi[ids]),max_nfev=350,diff_step=1e-4,ftol=2e-8,xtol=2e-8,gtol=2e-8)
  p=unpack(fit.x);r=dict(label=labels[mode],mode=mode,params=p.tolist(),start=p0.tolist(),ids=ids.tolist(),lower=lo.tolist(),upper=hi.tolist(),evaluations=fit.nfev,status=fit.message)
  for name,A,ns,mask0,dt in [('train',T,nt,mT,pd.read_csv('data/train.csv')),('val',V,nv,mV,pd.read_csv('data/val.csv'))]:
   y,v=rollout(p,A,ns,mode);err=y-A[:,0];res=acceleration(A[:,0],A[:,1],A[:,2],p,mode)-dt.dx1.to_numpy()
   ypre,_=rollout(p0,A,ns,mode)
   r[name+'_rmse']=float(np.sqrt(np.mean(err[mask0]**2)));r[name+'_prefit_rmse']=float(np.sqrt(np.mean((ypre[mask0]-A[mask0,0])**2)))
   r[name+'_derivative_rmse']=float(np.sqrt(np.mean(res**2)));r[name+'_max_abs_states']=[float(np.max(np.abs(y))),float(np.max(np.abs(v)))]
   r[name+'_residual_correlations']=np.corrcoef(np.column_stack([res,A]).T)[0,1:].tolist()
   r[name+'_speed_bands']=[dict(range=[low,high],n=int(np.sum((np.abs(A[:,1])>=low)&(np.abs(A[:,1])<high))),mean=float(np.mean(res[(np.abs(A[:,1])>=low)&(np.abs(A[:,1])<high)])),rmse=float(np.sqrt(np.mean(res[(np.abs(A[:,1])>=low)&(np.abs(A[:,1])<high)]**2)))) for low,high in [(0,.2),(.2,1),(1,5),(5,30)]]
  out.append(r);print(json.dumps(r),flush=True)
 json.dump(out,open('final_fit_results.json','w'),indent=2)
if __name__=='__main__':run()
