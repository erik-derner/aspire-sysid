import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
from numba import njit
@njit
def accel(y,v,u,p,kind):
 if kind==0:return -p[0]*y-p[1]*v+p[2]*u
 if kind==1:return -p[0]*np.sin(y)-p[1]*v+p[2]*u
 if kind==3:force=-p[0]*y+p[5]*y**3+p[2]*u
 elif kind==5:force=-p[0]*np.sin(p[5]*y)+p[2]*u
 else:force=-p[0]*np.sin(y)+p[2]*u
 if kind==4:force+=p[5]
 if kind==6:friction=p[3]*v/np.sqrt(v*v+p[4]*p[4])
 elif kind==7:
  if abs(v)<p[4] and abs(force)<p[3]:return 0.
  friction=p[3]*np.sign(v)
 elif kind==8:friction=(p[3]+p[5]*np.exp(-(v/p[6])**2))*np.tanh(v/p[4])
 else:friction=p[3]*np.tanh(v/p[4])
 return force-p[1]*v-friction
@njit
def sim(a,p,kind):
 out=np.empty((a.shape[0],2));out[0,:]=a[0,:2]
 for k in range(len(a)-1):
  y,v=out[k];u=a[k,2]
  d1=accel(y,v,u,p,kind); y2=y+.005*v;v2=v+.005*d1
  d2=accel(y2,v2,u,p,kind);y3=y+.005*v2;v3=v+.005*d2
  d3=accel(y3,v3,u,p,kind);y4=y+.01*v3;v4=v+.01*d3
  d4=accel(y4,v4,u,p,kind)
  out[k+1,0]=y+.01/6*(v+2*v2+2*v3+v4)
  out[k+1,1]=v+.01/6*(d1+2*d2+2*d3+d4)
  if not np.isfinite(out[k+1,0]) or abs(out[k+1,0])>100:
   out[k+1:,:]=100.;break
 return out
def load(fn):return [g[['y','x1','x2','dx1']].to_numpy() for _,g in pd.read_csv(fn).groupby('trajectory',sort=False)]
def residual(p,kind,groups):return np.concatenate([sim(a,p,kind)[1:,0]-a[1:,0] for a in groups])
def score(p,kind,groups):
 r=residual(p,kind,groups);return float(np.sqrt(np.mean(r*r)))
def main():
 tr=load('data/train.csv');va=load('data/val.csv')
 specs={
 'linear':(0,[66.52908,3.85349,24.76025],[1,0,0],[300,30,100]),
 'pendulum':(1,[101.6866,3.88218,25.5109],[1,0,0],[300,30,100]),
 'tanh':(2,[108.38543,1.61815,26.51269,19.02603,.3],[1,0,0,0,.08],[300,30,100,60,3]),
 'cubic':(3,[105.49389,1.64549,26.70383,18.92769,.3,13.87064],[1,0,0,0,.08,-10],[300,30,100,60,3,40]),
 'offset':(4,[108.25695,1.58579,26.59573,19.33214,.3,1.22047],[1,0,0,0,.08,-20],[300,30,100,60,3,20]),
 'scaled':(5,[108.38543,1.61815,26.51269,19.02603,.3,1.],[1,0,0,0,.08,.3],[300,30,100,60,3,1.5]),
 'algebraic':(6,[108.38543,1.61815,26.51269,19.02603,.3],[1,0,0,0,.08],[300,30,100,60,3]),
 'stick':(7,[108.38543,1.61815,26.51269,19.02603,.15],[1,0,0,0,.02],[300,30,100,60,.5]),
 'stribeck':(8,[108.38543,1.61815,26.51269,19.02603,.3,5.,1.],[1,0,0,0,.08,-15,.2],[300,30,100,60,3,30,5])}
 results={}
 for name,(kind,start,lo,hi) in specs.items():
  t=time.time();p=np.array(start)
  print(name,'initial',score(p,kind,tr),score(p,kind,va),flush=True)
  fit=least_squares(residual,p,args=(kind,tr),bounds=(lo,hi),diff_step=1e-4 if kind==7 else None,max_nfev=200,x_scale='jac',ftol=1e-8,xtol=1e-8,gtol=1e-8)
  p=fit.x;results[name]={'kind':kind,'start':start,'lower':lo,'upper':hi,'p':p.tolist(),'train':score(p,kind,tr),'val':score(p,kind,va),'nfev':fit.nfev,'status':fit.message}
  print(name,results[name],'seconds',time.time()-t,flush=True)
  open('rollout_results.json','w').write(json.dumps(results,indent=2))
if __name__=='__main__':main()
