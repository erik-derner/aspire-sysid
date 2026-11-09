"""Independent nonlinear oscillator diagnostics; no model submission files.
Units: Y, V, U denote unspecified recorded units of y, x1, x2; dx1 is V/s.
All derivative errors are RMS(predicted dx1 - recorded dx1). Rollout errors
are RMS(predicted y - recorded y), excluding initial row per trajectory.
"""
import json
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import pearsonr
train=pd.read_csv('data/train.csv'); val=pd.read_csv('data/val.csv')

def features(d):
 y=d.y.values; v=d.x1.values; u=d.x2.values
 return {'1':np.ones(len(d)),'y':y,'x1':v,'x2':u,'sin(y)':np.sin(y),'y**3':y**3,'y**5':y**5,'x1*Abs(x1)':v*np.abs(v),'x1**3':v**3,'sign(x1)':np.sign(v),'x2*Abs(x2)':u*np.abs(u),'x2**3':u**3,'sign(x2)':np.sign(u),'y*x1':y*v,'y**2*x1':y*y*v,'y*x2':y*u,'y**2*x2':y*y*u,'x1*x2':v*u,'x1**2*x2':v*v*u,'x1*x2**2':v*u*u,'cos(y)*x2':np.cos(y)*u,'sin(y)*x1**2':np.sin(y)*v*v}
F=features(train); G=features(val)
models={}
def fit(label,names):
 X=np.column_stack([F[n] for n in names]); Z=np.column_stack([G[n] for n in names]); c=np.linalg.lstsq(X,train.dx1,rcond=None)[0]
 models[label]={'names':names,'coef':c.tolist(),'train_rmse':float(np.sqrt(np.mean((X@c-train.dx1)**2))),'val_rmse':float(np.sqrt(np.mean((Z@c-val.dx1)**2))),'condition':float(np.linalg.cond(X))}
 return X@c,Z@c
families={
'linear':['1','y','x1','x2'],
'pendulum':['1','sin(y)','x1','x2'],
'duffing':['1','y','y**3','x1','x2'],
'pendulum_coulomb':['1','sin(y)','x1','sign(x1)','x2'],
'duffing_coulomb':['1','y','y**3','x1','sign(x1)','x2'],
'linear_coulomb':['1','y','x1','sign(x1)','x2'],
'pendulum_drag':['1','sin(y)','x1','x1*Abs(x1)','sign(x1)','x2'],
'duffing_drag':['1','y','y**3','x1','x1*Abs(x1)','sign(x1)','x2'],
'input_cubic':['1','sin(y)','x1','sign(x1)','x2','x2**3'],
'input_quadratic':['1','sin(y)','x1','sign(x1)','x2','x2*Abs(x2)'],
'input_sign':['1','sin(y)','x1','sign(x1)','x2','sign(x2)'],
'input_projection':['1','sin(y)','x1','sign(x1)','x2','cos(y)*x2'],
'poly_extended':['1','y','y**3','y**5','x1','x1*Abs(x1)','x1**3','sign(x1)','x2','x2*Abs(x2)','x2**3'],
'cross_terms':['1','sin(y)','x1','sign(x1)','x2','y**2*x1','y**2*x2','x1*x2**2','sin(y)*x1**2'],
}
preds={}
for label,names in families.items(): preds[label]=fit(label,names)
# Smooth friction and input saturation scans; chosen scales are in recorded units.
for scale in np.logspace(-2,1.5,35):
 name=f'tanh(x1/{scale:.16g})'; F[name]=np.tanh(train.x1/scale); G[name]=np.tanh(val.x1/scale)
 label='tanh_'+str(scale); preds[label]=fit(label,['1','sin(y)','x1',name,'x2']); models[label]['scale']=float(scale)
for scale in np.logspace(-1,1,25):
 name=f'tanh(x2/{scale:.16g})'; F[name]=np.tanh(train.x2/scale); G[name]=np.tanh(val.x2/scale)
 label='input_tanh_'+str(scale); preds[label]=fit(label,['1','sin(y)','x1','sign(x1)',name]); models[label]['scale']=float(scale)
# Joint nonlinear least-squares: pendulum angle scale, smooth friction, input saturation.
def nonlinear_prediction(d,p,form):
 y=d.y.values;v=d.x1.values;u=d.x2.values
 b,k,c,f,g=p[:5]
 restoring=np.sin(y) if form not in ('freq','freq_friction') else np.sin(np.exp(p[5])*y)
 friction=np.sign(v) if form not in ('friction','freq_friction') else np.tanh(v/np.exp(p[-1]))
 return b+k*restoring+c*v+f*friction+g*u
base=models['pendulum_coulomb']['coef']
for form in ['freq','friction','freq_friction']:
 p0=base+[0.] if form=='freq' else base+[-2.] if form=='friction' else base+[0.,-2.]
 fun=lambda p:nonlinear_prediction(train,p,form)-train.dx1.values
 opt=least_squares(fun,p0,max_nfev=500,bounds=([-np.inf]*5+([-3.] if form=='freq' else [-8.] if form=='friction' else [-3.,-8.]),[np.inf]*5+([2.] if form=='freq' else [4.] if form=='friction' else [2.,4.])))
 pt=nonlinear_prediction(train,opt.x,form);pv=nonlinear_prediction(val,opt.x,form)
 models['nonlinear_'+form]={'parameters':opt.x.tolist(),'train_rmse':float(np.sqrt(np.mean((pt-train.dx1)**2))),'val_rmse':float(np.sqrt(np.mean((pv-val.dx1)**2))),'success':bool(opt.success),'initial':p0}
 preds['nonlinear_'+form]=(pt,pv)
# Dataset kinematics and quantization.
metadata={}
for label,d in [('train',train),('val',val)]:
 err=[]; dv=[]; ystep=[]
 for tid,a in d.groupby('trajectory',sort=False):
  err.extend((a.y.values[2:]-a.y.values[:-2])/.02-a.x1.values[1:-1]);dv.extend((a.x1.values[2:]-a.x1.values[:-2])/.02-a.dx1.values[1:-1]);ystep.extend(np.diff(a.y))
 metadata[label]={'ranges':{n:[float(d[n].min()),float(d[n].max())] for n in ['y','x1','x2','dx1']},'dy_cd_rmse':float(np.sqrt(np.mean(np.array(err)**2))),'dx1_cd_rmse':float(np.sqrt(np.mean(np.array(dv)**2))),'zero_velocity_fraction':float(np.mean(d.x1==0)),'zero_input_fraction':float(np.mean(d.x2==0)),'min_nonzero_y_step':float(np.min(np.abs(np.array(ystep)[np.array(ystep)!=0])))}
residuals={}
for label in ['linear','pendulum','pendulum_coulomb','duffing_coulomb','input_cubic','input_quadratic','cross_terms','nonlinear_freq','nonlinear_friction']:
 residuals[label]={}
 for tag,d,p in [('train',train,preds[label][0]),('val',val,preds[label][1])]:
  r=d.dx1.values-p
  corrs={n:float(np.corrcoef(r,features(d)[n])[0,1]) for n in ['y','sin(y)','y**3','x1','sign(x1)','x1*Abs(x1)','x2','sign(x2)','x2**3','y**2*x1','y**2*x2','x1*x2**2']}
  bytraj={str(t):{'n':len(a),'rmse':float(np.sqrt(np.mean(r[a.index]**2))),'bias':float(np.mean(r[a.index]))} for t,a in d.groupby('trajectory')}
  bins={}
  for n,edges in [('x1',[-np.inf,-10,-3,-.5,-.001,.001,.5,3,10,np.inf]),('y',[-np.inf,-1,-.3,-.05,.05,.3,1,np.inf]),('x2',[-np.inf,-2,-.5,-.001,.001,.5,2,np.inf])]:
   q=d[n].values
   bins[n]=[{'lower':str(lo),'upper':str(hi),'n':int(np.sum((q>=lo)&(q<hi))),'bias':float(np.mean(r[(q>=lo)&(q<hi)])) if np.any((q>=lo)&(q<hi)) else None,'rmse':float(np.sqrt(np.mean(r[(q>=lo)&(q<hi)]**2))) if np.any((q>=lo)&(q<hi)) else None} for lo,hi in zip(edges[:-1],edges[1:])]
  adjacent=[]
  for t,a in d.groupby('trajectory'): adjacent.extend(zip(r[a.index][:-1],r[a.index][1:]))
  residuals[label][tag]={'correlations':corrs,'by_trajectory':bytraj,'bins':bins,'lag1':float(np.corrcoef(np.array(adjacent).T)[0,1])}
# RK4 trajectory validation, zero-order-hold input, identical to stated harness.
def force(z,u,model):
 y,v=z
 if 'names' in model:
  env={'y':y,'x1':v,'x2':u,'sin':np.sin,'cos':np.cos,'tanh':np.tanh,'Abs':np.abs,'sign':np.sign}
  return sum(c*eval(n,{'__builtins__':{}},env) for n,c in zip(model['names'],model['coef']))
 p=model['parameters'];form=model['form'];b,k,c,f,g=p[:5]
 s=np.exp(p[5]) if form in ('freq','freq_friction') else 1
 friction=np.tanh(v/np.exp(p[-1])) if form in ('friction','freq_friction') else np.sign(v)
 return b+k*np.sin(s*y)+c*v+f*friction+g*u
for form in ['freq','friction','freq_friction']:models['nonlinear_'+form]['form']=form
selected=list(families)+['nonlinear_freq','nonlinear_friction','nonlinear_freq_friction']
selected += [min((l for l in models if l.startswith('tanh_')),key=lambda l:models[l]['val_rmse']),min((l for l in models if l.startswith('input_tanh_')),key=lambda l:models[l]['val_rmse'])]
for label in selected:
 rollout={}
 for tag,d in [('train',train),('val',val)]:
  errors=[];trajectories={};failed=False
  for tid,a in d.groupby('trajectory',sort=False):
   z=a[['y','x1']].values[0].copy(); yy=[z[0]]
   def rhs(z,u):return np.array([z[1],force(z,u,models[label])])
   with np.errstate(all='ignore'):
    for u in a.x2.values[:-1]:
     k1=rhs(z,u);k2=rhs(z+.005*k1,u);k3=rhs(z+.005*k2,u);k4=rhs(z+.01*k3,u);z=z+.01*(k1+2*k2+2*k3+k4)/6
     yy.append(z[0])
     if not np.all(np.isfinite(z)) or np.max(np.abs(z))>1000:failed=True;break
   if len(yy)==len(a):
    e=np.array(yy)[1:]-a.y.values[1:]; errors.extend(e);trajectories[str(tid)]=float(np.sqrt(np.mean(e**2)))
   else:trajectories[str(tid)]=None
  rollout[tag]={'rmse':float(np.sqrt(np.mean(np.array(errors)**2))) if not failed else None,'per_trajectory':trajectories,'failed':failed}
 models[label]['rollout']=rollout
out={'units':'y: Y, x1: V, x2: U, dx1: V/s (all physical units unspecified); derivative RMSE: V/s; rollout RMSE: Y; correlations/fractions/condition numbers dimensionless','metadata':metadata,'models':models,'residuals':residuals}
with open('helper_results.json','w') as f:json.dump(out,f,indent=2,allow_nan=False)
for l in selected:
 m=models[l]; print(l,'derivative',m['train_rmse'],m['val_rmse'],'rollout',m['rollout']['train']['rmse'],m['rollout']['val']['rmse']);print(' ',m.get('coef',m.get('parameters')))
print('metadata',metadata)
