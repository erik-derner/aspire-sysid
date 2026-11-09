"""Train-only acceleration derivative regression; validation is diagnostics only."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
results=[]

def features(d,names,w=1.,s=1.):
 y=d.y.to_numpy(); z=d.x1.to_numpy(); u=d.x2.to_numpy()
 f={'1':np.ones(len(d)),'y':y,'x1':z,'x2':u,'sin(w*y)':np.sin(w*y),'cos(w*y)':np.cos(w*y),'sin(2*w*y)':np.sin(2*w*y),'sin(3*w*y)':np.sin(3*w*y),'x1*Abs(x1)':z*np.abs(z),'x1**3':z**3,'sign(x1)':np.sign(z),'tanh(x1/s)':np.tanh(z/s),'x2**3':u**3,'x2*Abs(x2)':u*np.abs(u),'x2*y':u*y,'x2*y**2':u*y*y,'x2*cos(w*y)':u*np.cos(w*y),'x2*sin(w*y)':u*np.sin(w*y),'x1*y':z*y,'x1*y**2':z*y*y,'x1*cos(w*y)':z*np.cos(w*y),'x1*sin(w*y)':z*np.sin(w*y),'x1*x2':z*u,'x1*x2**2':z*u*u,'y**3':y**3,'y**5':y**5,'y**7':y**7,'y*Abs(y)':y*np.abs(y)}
 return np.column_stack([f[n] for n in names])
def fit(label,names,w=1.,s=1.,record=True):
 X=features(tr,names,w,s); V=features(va,names,w,s); scale=np.linalg.norm(X,axis=0); scale[scale==0]=1
 a=np.linalg.lstsq(X/scale,tr.dx1,rcond=None)[0]/scale
 rt=tr.dx1.to_numpy()-X@a; rv=va.dx1.to_numpy()-V@a
 out={'label':label,'names':names,'w':w,'s':s,'a':a,'train_rmse':np.sqrt(np.mean(rt**2)),'val_rmse':np.sqrt(np.mean(rv**2)),'rt':rt,'rv':rv,'train_mae':np.mean(np.abs(rt)),'val_mae':np.mean(np.abs(rv))}
 if record: results.append(out)
 return out
base=['1','y','x1','x2']
fit('linear',base)
fit('cubic',['1','y','x1','x2','y**3'])
fit('quintic',['1','y','x1','x2','y**3','y**5'])
fit('septic',['1','y','x1','x2','y**3','y**5','y**7'])
trig=['1','sin(w*y)','x1','x2']
fit('sin_unit',trig)
# Frequency search using training SSE only, refine each local grid basin.
grid=np.linspace(.1,4.,160); costs=[fit('',trig,w=k,record=False)['train_rmse'] for k in grid]
candidates=[]
for i in range(1,len(grid)-1):
 if costs[i]<costs[i-1] and costs[i]<costs[i+1]:
  o=minimize_scalar(lambda w:fit('',trig,w=w,record=False)['train_rmse'],bounds=(grid[i-1],grid[i+1]),method='bounded',options={'xatol':1e-10}); candidates.append(o)
w=min(candidates,key=lambda o:o.fun).x if candidates else grid[np.argmin(costs)]
fit('sin_freq',trig,w=w)
fit('sin_freq_linear',trig+['y'],w=w)
fit('sin_freq_harmonics',trig+['sin(2*w*y)','sin(3*w*y)'],w=w)
for term in ['sign(x1)','x1*Abs(x1)','x1**3','x2**3','x2*Abs(x2)','x2*y','x2*y**2','x2*cos(w*y)','x2*sin(w*y)','x1*y','x1*y**2','x1*cos(w*y)','x1*sin(w*y)','x1*x2','x1*x2**2','cos(w*y)']:
 fit('single_'+term,trig+[term],w=w)
for s in [.05,.1,.2,.5,1.,2.,5.]: fit('friction_s'+str(s),trig+['tanh(x1/s)'],w=w,s=s)
fit('full_trig',trig+['y','sin(2*w*y)','sin(3*w*y)','x1*Abs(x1)','x1**3','sign(x1)','x2**3','x2*Abs(x2)','x2*y','x2*y**2','x2*sin(w*y)','x1*y','x1*y**2','x1*sin(w*y)','x1*x2','x1*x2**2'],w=w)
# Greedy forward term selection by training SSE, not validation.
remaining=['y','sin(2*w*y)','sin(3*w*y)','x1*Abs(x1)','x1**3','sign(x1)','x2**3','x2*Abs(x2)','x2*y','x2*y**2','x2*sin(w*y)','x1*y','x1*y**2','x1*sin(w*y)','x1*x2','x1*x2**2']; selected=list(trig)
for i in range(6):
 opts=[fit('',selected+[n],w=w,record=False) for n in remaining]; best=min(opts,key=lambda r:r['train_rmse']); chosen=best['names'][-1]; selected.append(chosen);remaining.remove(chosen);fit('forward_'+str(i+1),selected,w=w)
lines=[]
lines.append('Independent acceleration derivative analysis. Allowed sources: data/train.csv and data/val.csv only. No simulation and no candidate JSON.\n')
lines.append('Symbols: `y` and `x1` are logged states, `x2` is logged input, `dx1` is the logged derivative target; their physical units are unknown. Coefficient units follow derivative-unit divided by feature-unit; frequencies multiply `y` and have inverse-y-unit, friction scales have x1-unit. All errors below are in the unknown `dx1` unit.\n')
lines.append('Data: training uses all 3522 rows across 13 trajectories; validation diagnostics use all 1192 rows across 3 trajectories. RMSE = `sqrt(mean((dx1-prediction)**2))`; MAE = `mean(Abs(dx1-prediction))`. Residual = `dx1-prediction`.\n')
lines.append('Approaches: ordinary least squares linear, odd-polynomial restoring, sine restoring with a training-only frequency search, harmonics, friction and state/input interactions. OLS uses numpy.linalg.lstsq with column norm scaling, no starting values or random seed. Frequency uses 160 dimensionless grid indices over `0.1 <= w <= 4.0` inverse-y-unit, then scipy.optimize.minimize_scalar bounded local refinement to tolerance `1e-10` inverse-y-unit. Linear coefficients jointly refitted at each frequency. Smooth friction scales are fixed sensitivity trials, not optimized. Structures chosen as mathematical hypotheses, not asserted physical mechanisms.\n')
lines.append('Summary: each row lists label, training RMSE, validation RMSE, training MAE, validation MAE (unknown dx1-unit).\n')
for r in results: lines.append('%s: %.8g %.8g %.8g %.8g\n'%(r['label'],r['train_rmse'],r['val_rmse'],r['train_mae'],r['val_mae']))
lines.append('\nFull fitted expressions: coefficients below have derivative-unit/feature-unit (physical units unavailable); `w` inverse-y-unit and `s` x1-unit.\n')
for r in results:
 expr=' + '.join('(%0.12g)*(%s)'%(a,n) for a,n in zip(r['a'],r['names']))
 lines.append('%s: `%s`; `w = %.12g`, `s = %.12g`.\n'%(r['label'],expr,r['w'],r['s']))
# Correlations, bins, and trajectory diagnostics for core/best alternatives.
focus=[results[0],next(r for r in results if r['label']=='sin_freq'),next(r for r in results if r['label']=='full_trig'),min(results,key=lambda r:r['val_rmse'])]
for r in focus:
 lines.append('\nResidual diagnostics for '+r['label']+' (all residual statistics unknown dx1-unit; correlations dimensionless):\n')
 for d,res,tag in [(tr,r['rt'],'training'),(va,r['rv'],'validation')]:
  lines.append(tag+' trajectory RMSE, mean residual:\n')
  for tid in sorted(d.trajectory.unique()):
   mask=d.trajectory.to_numpy()==tid; lines.append('trajectory %s: %.7g, %.7g\n'%(tid,np.sqrt(np.mean(res[mask]**2)),np.mean(res[mask])))
  for col in ['y','x1','x2']:
   vals=d[col].to_numpy(); edges=np.unique(np.quantile(vals,[0,.1,.25,.5,.75,.9,1])); lines.append(tag+' '+col+' bin mean residual (bin boundaries in unknown '+col+' unit):\n')
   for l,h in zip(edges[:-1],edges[1:]):
    m=(vals>=l)&(vals<=h) if h==edges[-1] else (vals>=l)&(vals<h)
    if m.any(): lines.append('[%.5g,%.5g]: mean %.7g, RMSE %.7g, count %d\n'%(l,h,np.mean(res[m]),np.sqrt(np.mean(res[m]**2)),m.sum()))
  terms=['y','x1','x2','x1*Abs(x1)','x2**3','x2*y','x2*y**2','x1*y','x1*y**2','sign(x1)']; X=features(d,terms,w=w); cs=[np.corrcoef(res,X[:,i])[0,1] for i in range(len(terms))]; lines.append(tag+' residual correlations: '+', '.join('`%s`: %.5g'%(n,c) for n,c in zip(terms,cs))+'\n')
  pairs=[(res[g.index[:-1]],res[g.index[1:]]) for _,g in d.groupby('trajectory')]; aa=np.concatenate([p[0] for p in pairs]);bb=np.concatenate([p[1] for p in pairs]);lines.append(tag+' within-trajectory lag-one residual correlation %.6g (dimensionless; 0.01 s lag).\n'%np.corrcoef(aa,bb)[0,1])
# Inspect quantization without treating it as model physics.
for col in ['y','x1','dx1']:
 vals=tr[col].to_numpy(); unique=np.unique(np.round(vals,10)); diff=np.diff(unique); lines.append('\nTraining '+col+' unique nonzero spacing quantiles (unknown '+col+' unit): '+str(np.quantile(diff[diff>1e-8],[0,.1,.5,.9]))+'\n')
lines.append('\nLimitations: derivative fit does not assess free-run stability or output RMSE. Repeated zero-velocity and quantized target rows can dominate ordinary least squares. Frequency and polynomial coefficients are local descriptions only. Validation-selected best derivative model is diagnostic, not a claim of independent test performance. Method reference from memory, not externally checked: Golub and Van Loan, Matrix Computations (least squares).\n')
open('helper_report.txt','w').writelines(lines)
print('Best validation derivative:',min(results,key=lambda r:r['val_rmse'])['label'])
for r in results: print(r['label'],r['train_rmse'],r['val_rmse'])
print('Frequency',w)
