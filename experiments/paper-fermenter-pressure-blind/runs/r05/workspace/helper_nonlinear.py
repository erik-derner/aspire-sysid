import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
Y=tr.dy.to_numpy(); V=va.dy.to_numpy(); out=[]
def features(d):
 y,u,v=[d[c].to_numpy() for c in ['y','x1','x2']]; f={'1':np.ones(len(y)),'y':y,'x1':u,'x2':v}
 for z,n in [(y,'y'),(u,'x1'),(v,'x2')]:
  for p in [-2,-1,-.5,.5,1.5,2,3]:f[f'{n}**{p}']=z**p
  f[f'log({n})']=np.log(z)
 for h in [.9,.95,.98,1,1.05,1.1,1.2,1.4]:
  f[f'sqrt(Abs(y-{h}))']=np.sqrt(np.abs(y-h));f[f'sign(y-{h})*sqrt(Abs(y-{h}))']=np.sign(y-h)*np.sqrt(np.abs(y-h));f[f'Max(y-{h},0)']=np.maximum(y-h,0)
 for n,z in [('x1',u),('x2',v)]:
  for w in [.01,.025,.05,.1,np.pi/180,2*np.pi/100]:
   f[f'sin({w}*{n})']=np.sin(w*z);f[f'cos({w}*{n})']=np.cos(w*z)
 for p in [-2,-1,-.5,.5,1,2]:
  for n,z in [('x1',u),('x2',v),('sqrt(x1)',np.sqrt(u)),('sqrt(x2)',np.sqrt(v)),('x1**2',u*u),('x2**2',v*v)]:f[f'{n}*y**{p}']=z*y**p
 f['x1*x2']=u*v;f['x1/x2']=u/v;f['x2/x1']=v/u
 return f
ft,fv=features(tr),features(va); names=list(ft); A=np.array([ft[n] for n in names]).T; B=np.array([fv[n] for n in names]).T
scale=np.linalg.norm(A,axis=0); An=A/scale; Bn=B/scale
selected=[0]; residual=Y.copy()
for k in range(1,21):
 if k>1:
  cor=np.abs(An.T@residual);cor[selected]=-1;selected.append(int(np.argmax(cor)))
 c=np.linalg.lstsq(An[:,selected],Y,rcond=None)[0]; residual=Y-An[:,selected]@c
 out.append({'family':'greedy_sparse','terms':[names[i] for i in selected],'coefficients':(c/scale[selected]).tolist(),'train_rmse':float(np.sqrt(np.mean(residual**2))),'val_rmse':float(np.sqrt(np.mean((V-Bn[:,selected]@c)**2)))})
# All compact fixed basis variants, no validation fitting.
for sp in [-3,-2,-1,-.5,.5,1,1.5,2,3]:
 for up in [.5,1,1.5,2]:
  for vp in [.5,1,1.5,2]:
   for divide in [0,1]:
    def mat(d):
     y,u,v=[d[c].to_numpy() for c in ['y','x1','x2']];return np.array([np.ones(len(y)),u**up/y**divide,v**vp/y**divide,y**sp]).T
    a,b=mat(tr),mat(va); c=np.linalg.lstsq(a,Y,rcond=None)[0]
    out.append({'family':'fixed_power','powers':[sp,up,vp,divide],'coefficients':c.tolist(),'train_rmse':float(np.sqrt(np.mean((Y-a@c)**2))),'val_rmse':float(np.sqrt(np.mean((V-b@c)**2)))})
# Profile linear coefficients while estimating exponents and threshold.
def profile(p,d):
 sp,up,vp,div,h=p;y,u,v=[d[c].to_numpy() for c in ['y','x1','x2']]
 return np.array([np.ones(len(y)),(u/60)**up/y**div,(v/20)**vp/y**div,np.sign(y-h)*np.abs(y-h)**sp/y**div]).T
for start in [[.5,1,1,0,0],[1,1,1,0,0],[.5,1,1,0,1],[1,1,1,1,0],[2,1,1,0,1],[.5,.5,.5,0,0]]:
 def fun(p):
  a=profile(p,tr);c=np.linalg.lstsq(a,Y,rcond=None)[0];return a@c-Y
 r=least_squares(fun,start,bounds=([.1,.1,.1,-3,-1],[4,3,3,3,1.5]),max_nfev=1500,ftol=1e-12,xtol=1e-12,gtol=1e-12)
 a,b=profile(r.x,tr),profile(r.x,va);c=np.linalg.lstsq(a,Y,rcond=None)[0]
 out.append({'family':'profile_power_threshold','start':start,'nonlinear_parameters':r.x.tolist(),'coefficients':c.tolist(),'train_rmse':float(np.sqrt(np.mean((Y-a@c)**2))),'val_rmse':float(np.sqrt(np.mean((V-b@c)**2)))})
out.sort(key=lambda r:r['val_rmse']);json.dump(out,open('helper_nonlinear_results.json','w'),indent=2)
print('TOP RESULTS');print(json.dumps(out[:12],indent=2));print('SPARSE PATH');print(json.dumps([r for r in out if r['family']=='greedy_sparse'],indent=2));print('PROFILE');print(json.dumps([r for r in out if r['family']=='profile_power_threshold'],indent=2))
print('forward difference errors',[(n,np.sqrt(np.mean(((d.y.to_numpy()[1:]-d.y.to_numpy()[:-1])/5-d.dy.to_numpy()[:-1])**2))) for n,d in [('train',tr),('val',va)]])
