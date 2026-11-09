import numpy as np, pandas as pd, json, os, time
from scipy.optimize import least_squares
from numba import njit

@njit(cache=True)
def accel(t,w,u,p,fam):
 a,b,g,c=p[0:4]
 f=a*u-g*np.sin(t)
 if fam==0: # smooth Coulomb
  return f-b*w-c*np.tanh(w/p[4])
 if fam==1: # force projection
  k=p[4]
  return f-b*w-min(max(f+k*w,-c),c)
 if fam==2: # smooth Stribeck
  v,ds,ws=p[4:7]
  return f-b*w-(c+ds*np.exp(-(w/ws)**2))*np.tanh(w/v)
 if fam==3: # smooth static/kinetic blend
  fs,v,k=p[4:7];h=np.exp(-(w/v)**2)
  z=max(f-fs,0)+min(f+fs,0)
  return h*z+(1-h)*(f-c*np.tanh(w/v))-b*w-k*h*w
 if fam==4: # projection anharmonic
  k,h=p[4:6];f=a*u-g*np.sin(t)*(1+h*np.cos(t))
  return f-b*w-min(max(f+k*w,-c),c)
 if fam==5: # projection asymmetric
  k,h=p[4:6]
  return f-b*w-min(max(f+k*w,-c*(1-h)),c*(1+h))
 if fam==6: # projection quadratic speed friction
  k,q=p[4:6]
  return f-b*w-q*w*abs(w)-min(max(f+k*w,-c),c)
 if fam==7: # projection Stribeck
  k,ds,vs=p[4:7];cs=c+ds*np.exp(-(w/vs)**2)
  return f-b*w-min(max(f+k*w,-cs),cs)
 if fam==8: # projection nonlinear monotone input
  k,q=p[4:6];f=a*u*(1+q*u*u)-g*np.sin(t)
  return f-b*w-min(max(f+k*w,-c),c)
 if fam in [9,10,11,12,13,14,15]:
  k,hs,hc=p[4:7];ct=c*(1+hs*np.sin(t)+hc*np.cos(t))
  if fam==9:
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==10:
   return f-b*w-ct*np.tanh(w/k)
  if fam==11:
   f=a*u*(1+p[7]*u*u)-g*np.sin(t)
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==12:
   f=a*u-g*np.sin(t)*(1+p[7]*np.cos(t))
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==13:
   asym=p[7]
   return f-b*w-min(max(f+k*w,-ct*(1-asym)),ct*(1+asym))
  if fam==14:
   f=a*u-g*np.sin(t)*(1+p[7]*np.sin(t))
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==15:
   fs,v=p[7:9];h=np.exp(-(w/v)**2)
   z=max(f-fs*ct,0)+min(f+fs*ct,0)
   return h*z+(1-h)*(f-ct*np.tanh(w/v))-b*w-k*h*w
 if fam==16: # angle-dependent projected Stribeck friction
  k,hs,hc,ds,vs=p[4:9];ct=c*(1+hs*np.sin(t)+hc*np.cos(t))+ds*np.exp(-(w/vs)**2)
  return f-b*w-min(max(f+k*w,-ct),ct)
 if fam==17: # static friction no smaller than kinetic
  k,hs,hc,ds,v=p[4:9];ct=c*(1+hs*np.sin(t)+hc*np.cos(t));h=np.exp(-(w/v)**2);fs=ct*(1+ds)
  z=max(f-fs,0)+min(f+fs,0)
  return h*z+(1-h)*(f-ct*np.tanh(w/v))-b*w-k*h*w
 if fam==18: # asymmetric projection with extra restoring harmonic
  k,hs,hc,asym,hg=p[4:9];ct=c*(1+hs*np.sin(t)+hc*np.cos(t));f=a*u-g*np.sin(t)*(1+hg*np.cos(t))
  return f-b*w-min(max(f+k*w,-ct*(1-asym)),ct*(1+asym))
 if fam==19: # equal static and kinetic friction, smooth blend
  k,hs,hc,v=p[4:8];ct=c*(1+hs*np.sin(t)+hc*np.cos(t));h=np.exp(-(w/v)**2)
  z=max(f-ct,0)+min(f+ct,0)
  return h*z+(1-h)*(f-ct*np.tanh(w/v))-b*w-k*h*w
 if fam==20: # identified Stribeck asymptote was zero; remove it
  v,vs=p[4:6]
  return f-b*w-c*np.exp(-(w/vs)**2)*np.tanh(w/v)
 return 0.

@njit(cache=True)
def simulate(p,fam,initial,inputs,lengths):
 ns,nt=inputs.shape;out=np.zeros((ns,nt))
 for j in range(ns):
  t,w=initial[j];out[j,0]=t
  for i in range(lengths[j]-1):
   u=inputs[j,i]
   d1=accel(t,w,u,p,fam);v1=w
   d2=accel(t+.005*v1,w+.005*d1,u,p,fam);v2=w+.005*d1
   d3=accel(t+.005*v2,w+.005*d2,u,p,fam);v3=w+.005*d2
   d4=accel(t+.01*v3,w+.01*d3,u,p,fam);v4=w+.01*d3
   t+=.01/6*(v1+2*v2+2*v3+v4);w+=.01/6*(d1+2*d2+2*d3+d4)
   if not np.isfinite(t) or abs(t)>100 or abs(w)>1000:
    out[j,i+1:]=100.;break
   out[j,i+1]=t
 return out

def pack(df):
 gs=list(df.groupby('trajectory',sort=False));n=max(len(g) for _,g in gs);u=np.zeros((len(gs),n));y=u.copy();mask=np.zeros_like(u,dtype=bool);ini=[];lens=[]
 for j,(key,g) in enumerate(gs):
  lens.append(len(g));ini.append(g[['theta','omega']].iloc[0].to_numpy());u[j,:len(g)]=g.u;y[j,:len(g)]=g.theta;mask[j,1:len(g)]=True
 return np.array(ini),u,np.array(lens),y,mask

specs={
 'smooth':(0,[26.49,1.59,108.53,19.29,.4],[1,0,20,0,.12],[60,10,200,60,5]),
 'projection':(1,[26.49,1.59,108.53,19.29,80],[1,0,20,0,3],[60,10,200,60,240]),
 'stribeck':(2,[26.49,1.59,108.53,19.29,.4,5,2],[1,0,20,0,.12,0,.2],[60,10,200,60,5,40,15]),
 'blend':(3,[26.49,1.59,108.53,19.29,22,.6,100],[1,0,20,0,0,.12,3],[60,10,200,60,60,5,220]),
 'harmonic':(4,[26.49,1.59,108.53,19.29,80,0],[1,0,20,0,3,-.95],[60,10,200,60,240,.95]),
 'asymmetric':(5,[26.49,1.59,108.53,19.29,80,0],[1,0,20,0,3,-.8],[60,10,200,60,240,.8]),
 'quadratic':(6,[26.49,1.59,108.53,19.29,80,.01],[1,0,20,0,3,0],[60,10,200,60,240,1]),
 'proj_stribeck':(7,[26.49,1.59,108.53,19.29,80,3,1],[1,0,20,0,3,0,.2],[60,10,200,60,240,40,10]),
 'cubic_input':(8,[26.49,1.59,108.53,19.29,80,.002],[1,0,20,0,3,0],[60,10,200,60,240,.1]),
 'angle_friction':(9,[26.46,1.6,110.2,24.56,80,-.30,-.30],[1,0,20,0,3,-.65,-.65],[60,10,200,60,240,.65,.65]),
 'angle_smooth':(10,[26.46,1.6,110.2,24.56,.2,-.30,-.30],[1,0,20,0,.12,-.65,-.65],[60,10,200,60,5,.65,.65]),
 'angle_cubic':(11,[26.46,1.6,110.2,24.56,80,-.30,-.30,.004],[1,0,20,0,3,-.65,-.65,0],[60,10,200,60,240,.65,.65,.1]),
 'angle_harmonic':(12,[26.46,1.6,110.2,24.56,80,-.30,-.30,0],[1,0,20,0,3,-.65,-.65,-.95],[60,10,200,60,240,.65,.65,.95]),
 'angle_asym':(13,[26.46,1.6,110.2,24.56,80,-.30,-.30,0],[1,0,20,0,3,-.65,-.65,-.8],[60,10,200,60,240,.65,.65,.8]),
 'angle_singrav':(14,[26.46,1.6,110.2,24.56,80,-.30,-.30,0],[1,0,20,0,3,-.65,-.65,-.95],[60,10,200,60,240,.65,.65,.95]),
 'angle_blend':(15,[26.46,1.6,110.2,24.56,80,-.30,-.30,1,.5],[1,0,20,0,3,-.65,-.65,.5,.12],[60,10,200,60,220,.65,.65,2,5]),
 'angle_stribeck':(16,[29,1.8,115,28,150,-.2,-.3,3,1],[1,0,20,0,3,-.65,-.65,0,.2],[60,10,200,60,240,.65,.65,40,15]),
 'physical_blend':(17,[29,1.8,115,28,80,-.2,-.3,.1,.5],[1,0,20,0,3,-.65,-.65,0,.12],[60,10,200,60,220,.65,.65,1,5]),
 'asym_harmonic':(18,[29,1.8,115,28,150,-.2,-.3,-.1,0],[1,0,20,0,3,-.65,-.65,-.8,-.95],[60,10,200,60,240,.65,.65,.8,.95]),
 'equal_blend':(19,[29.13,1.71,115.33,28.82,14.28,-.19,-.29,.435],[1,0,20,0,3,-.65,-.65,.12],[60,10,200,60,220,.65,.65,5]),
 'speed_weakening':(20,[28.46,3.056,111.67,19.95,.12,9.48],[1,0,20,0,.12,.2],[60,10,200,60,5,15])}

def run():
 train=pack(pd.read_csv('data/train.csv'));val=pack(pd.read_csv('data/val.csv'));results=json.load(open('fit_results.json')) if os.path.exists('fit_results.json') else {};
 for name,(fam,start,lb,ub) in specs.items():
  if name in results:continue
  def resid(p):return (simulate(p,fam,*train[:3])-train[3])[train[4]]
  starts=[start]
  if fam not in [0,2,10]:
   for k in [25,150]:
    s=start.copy();s[4 if fam!=3 else 6]=k;starts.append(s)
  else:
   s=start.copy();s[4]=1.;starts.append(s)
  best=None;tm=time.time()
  for s in starts:
   opt=least_squares(resid,s,bounds=(lb,ub),x_scale='jac',diff_step=1e-4,max_nfev=300,ftol=2e-8,xtol=2e-8,gtol=1e-7)
   if best is None or np.sum(opt.fun**2)<np.sum(best.fun**2):best=opt
  pred=simulate(best.x,fam,*val[:3]);rmse=np.sqrt(np.mean((pred-val[3])[val[4]]**2))
  train_rmse=np.sqrt(np.mean(best.fun**2));tr_by=[];va_by=[]
  for dat,errlist in [(train,tr_by),(val,va_by)]:
   pr=simulate(best.x,fam,*dat[:3]);
   for j,n in enumerate(dat[2]):errlist.append(float(np.sqrt(np.mean((pr[j,1:n]-dat[3][j,1:n])**2))))
  results[name]={'family':fam,'p':best.x.tolist(),'start':start,'lb':lb,'ub':ub,'train_rmse':train_rmse,'val_rmse':rmse,'train_by':tr_by,'val_by':va_by,'nfev':best.nfev}
  print(name,'params',best.x,'train',train_rmse,'val',rmse,'val_by',va_by,'sec',time.time()-tm,flush=True)
  with open('fit_results.json','w') as f:json.dump(results,f,indent=2)
if __name__=='__main__':run()
