import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from scipy.linalg import lstsq
from fit_splines import sim,design
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv');prefix=va.iloc[:728].copy();hold=va.iloc[728:].copy()
q=next(q for q in json.load(open('spline_results.json')) if q['nk']==3 and q['count']==10)
codes=np.array(q['codes']);knots=np.array(q['knots']);start=np.array(q['p'])
def r(p,d,what):
 return design(d.values,codes,knots)@p-d.dy.values if what=='der' else sim(p,codes,knots,d.y.values,d.x1.values/60,d.x2.values/20)
def fit(ds,w):
 if w=='derivative':return lstsq(np.concatenate([design(d.values,codes,knots) for d in ds]),np.concatenate([d.dy.values for d in ds]))[0]
 def res(p):
  out=[]
  for d in ds:
   out.append(r(p,d,'roll'))
   if w>0:out.append(10*np.sqrt(w)*r(p,d,'der'))
  return np.concatenate(out)
 return least_squares(res,start,max_nfev=800,x_scale='jac',ftol=1e-10,gtol=1e-10,xtol=1e-10).x
selection=[]
for w in ['derivative',0,1,10]:
 p=fit([tr,prefix],w);rec={'weight':w,'p':p.tolist(),'holdout_roll':float(np.mean(r(p,hold,'roll')**2)**.5),'holdout_der':float(np.mean(r(p,hold,'der')**2)**.5)};selection.append(rec);print(rec)
best=min(selection,key=lambda x:x['holdout_roll']);w=best['weight'];p=fit([tr,va],w);rec={'label':'HingeSpline','kind':'spline','weight':w,'p':p.tolist(),'start':q['p'],'codes':q['codes'],'knots':q['knots'],'selection':selection,'source':'nk 3 count 10 derivative in spline_results.json'}
for fn,d in [('train',tr),('val',va)]:
 for what in ['roll','der']:rec[fn+'_'+what]=float(np.mean(r(p,d,what)**2)**.5)
print(rec);json.dump(rec,open('final_spline_results.json','w'),indent=2)
