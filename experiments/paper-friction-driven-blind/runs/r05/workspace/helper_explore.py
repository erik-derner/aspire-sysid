import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from scipy.signal import savgol_filter
T=.01
D={s:pd.read_csv('data/'+s+'.csv') for s in ['train','val']}
def arrays(d):return [d[c].to_numpy() for c in ['y','x1','x2','dx1']]
def matrix(d,family,eps=.3,dz=.1):
 y,v,u,z=arrays(d); f=[np.ones(len(d)),u,v]; names=['offset','input','velocity']
 if 'sin' in family:f += [np.sin(y)];names+=['sin_y']
 elif 'cubic' in family:f += [y,y**3];names+=['y','y_cubed']
 elif 'dead' in family:f += [np.sign(y)*np.maximum(np.abs(y)-dz,0)];names+=['dead_y']
 else:f += [y];names+=['y']
 if 'coul' in family:f += [np.sign(v)];names+=['sign_v']
 if 'tanh' in family:f += [np.tanh(v/eps)];names+=['tanh_v']
 if 'quadratic' in family:f += [v*np.abs(v)];names+=['v_abs_v']
 return np.column_stack(f),names
def rmse(a):return float(np.sqrt(np.mean(a*a)))
def rollout(g,family,b,eps,dz):
 y,v,u,z=arrays(g); q=np.array([y[0],v[0]]); pred=[q.copy()]
 def rhs(q,uk):
  yy,vv=q
  fs=[1,uk,vv]
  if 'sin' in family:fs += [np.sin(yy)]
  elif 'cubic' in family:fs += [yy,yy**3]
  elif 'dead' in family:fs += [np.sign(yy)*max(abs(yy)-dz,0)]
  else:fs += [yy]
  if 'coul' in family:fs += [np.sign(vv)]
  if 'tanh' in family:fs += [np.tanh(vv/eps)]
  if 'quadratic' in family:fs += [vv*abs(vv)]
  return np.array([vv,np.dot(fs,b)])
 for uk in u[:-1]:
  k1=rhs(q,uk);k2=rhs(q+T*k1/2,uk);k3=rhs(q+T*k2/2,uk);k4=rhs(q+T*k3,uk);q=q+T*(k1+2*k2+2*k3+k4)/6
  if np.any(~np.isfinite(q)) or np.max(abs(q))>1000:return float('inf')
  pred.append(q.copy())
 return rmse(np.array(pred)[1:,0]-y[1:])
results=[]
for family in ['affine','sin','cubic','affine_coul','sin_coul','cubic_coul','sin_tanh','cubic_tanh','dead_tanh','sin_tanh_quadratic']:
 best=None
 for eps in ([.05,.1,.2,.4,.8,1.6,3.2] if 'tanh' in family else [.3]):
  for dz in (np.arange(0,.301,.025) if 'dead' in family else [.1]):
   X,names=matrix(D['train'],family,eps,dz);b=np.linalg.lstsq(X,D['train'].dx1,rcond=None)[0];e=X@b-D['train'].dx1.to_numpy();score=rmse(e)
   if best is None or score<best['train_derivative_rmse']:best={'family':family,'eps':eps,'dz':float(dz),'coefficients':dict(zip(names,b.tolist())),'train_derivative_rmse':score,'b':b}
 b=best.pop('b');eps=best['eps'];dz=best['dz'];best['per_trajectory']={}
 for split,d in D.items():
  X,_=matrix(d,family,eps,dz);e=d.dx1.to_numpy()-X@b;best[split+'_derivative_rmse']=rmse(e)
  sq=0;n=0
  for k,g in d.groupby('trajectory',sort=False):
   Xg,_=matrix(g,family,eps,dz);eg=g.dx1.to_numpy()-Xg@b;r=rollout(g,family,b,eps,dz)
   best['per_trajectory'][split+'_'+str(k)]={'derivative_rmse':rmse(eg),'residual_mean':float(np.mean(eg)),'y_rollout_rmse':r,'n':len(g)};sq+=r*r*(len(g)-1);n+=len(g)-1
  best[split+'_y_rollout_rmse']=float(np.sqrt(sq/n))
 results.append(best)
print('GLOBAL FITS coefficients: offset, input, velocity, restoring, friction as specified')
for r in results:print(json.dumps({k:v for k,v in r.items() if k!='per_trajectory'}))
print('BEST COMPACT per trajectory SIN TANH')
r=next(r for r in results if r['family']=='sin_tanh');print(json.dumps(r['per_trajectory'],indent=2))
print('PER-TRAJECTORY independent OLS SIN COUL; active means abs(x1)>.3')
hetero={}
for split,d in D.items():
 for k,g in d.groupby('trajectory'):
  active=g[np.abs(g.x1)>.3];X,names=matrix(active,'sin_coul');keep=np.ptp(X,axis=0)>1e-10;keep[0]=True;b=np.linalg.lstsq(X[:,keep],active.dx1,rcond=None)[0]
  z={'coefficients':dict(zip(np.array(names)[keep],b.tolist())),'active_n':len(active),'active_derivative_rmse':rmse(active.dx1.to_numpy()-X[:,keep]@b),'rest_n':int(np.sum(abs(g.x1)<1e-9)),'y_final':float(g.y.iloc[-1])}
  hetero[split+'_'+str(k)]=z;print(split,k,z)
print('FINITE DIFFERENCE AND QUANTIZATION')
quant={}
for split,d in D.items():
 fd=[];dy=[];jump=[]
 for k,g in d.groupby('trajectory'):
  y,v,u,z=arrays(g);fd.extend((np.gradient(v,T)[1:-1]-z[1:-1]).tolist());dy.extend((np.gradient(y,T)[1:-1]-v[1:-1]).tolist());jump.extend(np.diff(y).tolist())
 quant[split]={'interior_dx1_central_difference_rmse':rmse(np.array(fd)),'interior_dy_minus_x1_rmse':rmse(np.array(dy)), 'y_grid_pi_over_1000_max_error':float(np.max(abs(d.y/(np.pi/1000)-np.round(d.y/(np.pi/1000))))),'x1_grid_pi_over_20_max_error':float(np.max(abs(d.x1/(np.pi/20)-np.round(d.x1/(np.pi/20))))),'dx1_grid_2p5pi_max_error':float(np.max(abs(d.dx1/(2.5*np.pi)-np.round(d.dx1/(2.5*np.pi)))))}
 print(split,quant[split])
print('SMOOTHED DERIVATIVE FITS sin+coul, Savitzky-Golay over recorded x1, interior only')
smooth=[]
for window in [7,11,21]:
 pieces=[]
 for k,g in D['train'].groupby('trajectory'):
  h=g.copy();h['dx1']=savgol_filter(g.x1,window,3,deriv=1,delta=T);pieces.append(h.iloc[window//2:-window//2])
 d=pd.concat(pieces);X,names=matrix(d,'sin_coul');b=np.linalg.lstsq(X,d.dx1,rcond=None)[0];z={'window_samples':window,'n':len(d),'coefficients':dict(zip(names,b.tolist())),'smoothed_derivative_rmse':rmse(d.dx1.to_numpy()-X@b)};smooth.append(z);print(z)
print('RESIDUAL BINS sin+tanh')
r=next(r for r in results if r['family']=='sin_tanh');b=np.array(list(r['coefficients'].values()));bins={}
for split,d in D.items():
 X,_=matrix(d,'sin_tanh',r['eps'],r['dz']);e=d.dx1.to_numpy()-X@b;bins[split]={}
 for var,edges in [('x1',[-30,-8,-3,-1,-.15,.15,1,3,8,30]),('y',[-3,-1,-.3,-.1,.1,.3,1,3])]:
  out=[]
  for lo,hi in zip(edges[:-1],edges[1:]):
   m=(d[var]>=lo)&(d[var]<hi)
   if sum(m):out.append({'lo':lo,'hi':hi,'n':int(sum(m)),'mean_residual':float(np.mean(e[m])),'residual_rmse':rmse(e[m])})
  bins[split][var]=out;print(split,var,out)
with open('helper_explore_results.json','w') as f:json.dump({'fits':results,'heterogeneity':hetero,'quantization':quant,'smooth':smooth,'residual_bins':bins},f,indent=2)
