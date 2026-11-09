import numpy as np,pandas as pd,json,time,os
from scipy.optimize import least_squares
T=.01

def prepare(split):
 d=pd.read_csv('data/'+split+'.csv');gs=list(d.groupby('trajectory',sort=False));nmax=max(len(g) for k,g in gs);Y=np.zeros((nmax,len(gs)));V=Y.copy();U=Y.copy();M=np.zeros(Y.shape,bool)
 for j,(k,g) in enumerate(gs):
  n=len(g);Y[:n,j]=g.y;V[:n,j]=g.x1;U[:n,j]=g.x2;M[1:n,j]=True
 return Y,V,U,M
D={s:prepare(s) for s in ['train','val']}

def accel(y,v,u,p,fam):
 b,a,d,k,F,w=p[:6]
 drive=b+a*u-k*(y if 'linear' in fam else y+p[6]*y**3 if 'poly' in fam else np.sin(y))
 idx=7 if 'poly' in fam else 6
 if 'cos' in fam:drive=drive+p[idx]*np.cos(y);idx+=1
 if 'input' in fam:drive=drive+p[idx]*u*np.abs(u);idx+=1
 if 'harm' in fam:drive=drive+p[idx]*np.sin(2*y);idx+=1
 if 'asym' in fam:F=F+p[idx]*np.tanh(v/w);idx+=1
 if 'clamp' in fam: fr=np.clip(drive+w*v,-F,F)
 elif 'atan' in fam:fr=F*2/np.pi*np.arctan(v/w)
 else:fr=F*np.tanh(v/w)
 return drive-d*v-fr

def simulate(p,fam,split,full=False):
 Y,V,U,M=D[split];y=Y[0].copy();v=V[0].copy();ys=np.empty_like(Y);vs=np.empty_like(Y);ys[0]=y;vs[0]=v
 for i in range(len(Y)-1):
  u=U[i];a=accel(y,v,u,p,fam);b=accel(y+T/2*v,v+T/2*a,u,p,fam);c=accel(y+T/2*(v+T/2*a),v+T/2*b,u,p,fam);dd=accel(y+T*(v+T/2*b),v+T*c,u,p,fam)
  y=y+T*v+T*T/6*(a+b+c);v=v+T/6*(a+2*b+2*c+dd)
  ys[i+1]=y;vs[i+1]=v
  if not np.all(np.isfinite(y)) or np.max(abs(y))>100:
   return (np.nan_to_num(ys),np.nan_to_num(vs)) if full else np.full(np.sum(M),1e3)
 return (ys,vs) if full else (ys-Y)[M]

def start(fam):
 p=[1.7,26.4,1.5,105.6,19.7,100 if 'clamp' in fam else .4];lo=[-30,5,0,20,1,5 if 'clamp' in fam else .08];hi=[30,60,8,200,40,220 if 'clamp' in fam else 5]
 if 'poly' in fam:p+=[-.127];lo+=[-.17];hi+=[0]
 for t in ['cos','input','harm','asym']:
  if t in fam:p+=[0];lo+=[-30 if t!='input' else -5];hi+=[30 if t!='input' else 5]
 return np.array(p),np.array(lo),np.array(hi)

def fit(fam):
 p,lo,hi=start(fam);t=time.time();r=least_squares(lambda p:simulate(p,fam,'train'),p,bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=140,ftol=1e-7,xtol=1e-7,gtol=1e-6)
 results={'family':fam,'p':r.x.tolist(),'start':p.tolist(),'bounds':[lo.tolist(),hi.tolist()],'nfev':r.nfev,'status':r.message,'train_rmse':float(np.sqrt(np.mean(r.fun**2))),'val_rmse':float(np.sqrt(np.mean(simulate(r.x,fam,'val')**2))),'seconds':time.time()-t}
 for s in D:
  Y,V,U,M=D[s];ys,vs=simulate(r.x,fam,s,True);results[s+'_per_traj']=[float(np.sqrt(np.mean((ys[:,j]-Y[:,j])[M[:,j]]**2))) for j in range(Y.shape[1])]
 print(json.dumps(results),flush=True);return results
if __name__=='__main__':
 import sys
 families=sys.argv[1:] or ['sin_tanh','poly_tanh','sin_clamp','sin_clamp_cos','sin_tanh_cos','sin_clamp_harm','linear_clamp','sin_atan','sin_clamp_input','sin_clamp_asym']
 os.makedirs('results',exist_ok=True)
 for fam in families:
  r=fit(fam);json.dump(r,open('results/'+fam+'.json','w'),indent=2)
