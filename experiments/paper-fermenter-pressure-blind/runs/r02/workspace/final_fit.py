import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from fit_polys import rollout,design
import fit_nonlinear as nl
import fit_rational as rat
import fit_clamped as cl
from scipy.signal import lfilter

def load_cases():
 polys=json.load(open('fit_polys_results.json'));nr=json.load(open('nonlinear_results.json'));rr=json.load(open('rational_results.json'));cr=json.load(open('clamped_results.json'));hr=json.load(open('helper_results.json'))
 cases=[]
 q=next(q for q in polys if q['label']=='sparse3_15_der');cases.append({'label':'CubicSparse','kind':'poly','powers':q['powers'],'start':q['c'],'bounds':None,'source':'sparse3_15_der in fit_polys_results.json'})
 q=next(q for q in rr if q['mode']==0 and q['stage']=='der');cases.append({'label':'RationalQuadratic','kind':'rat','mode':0,'start':q['p'],'bounds':[[-10]*10+[0],[10]*10+[20]],'source':'mode 0 derivative in rational_results.json'})
 for label,m in [('LogFeedback',2),('BilinearPower',0)]:
  q=next(q for q in nr if q['model']==m and q['stage']=='der');cases.append({'label':label,'kind':'nl','mode':m,'start':q['p'],'bounds':q['bounds'],'source':q['name']+' derivative in nonlinear_results.json'})
 q=next(q for q in cr if q['mode']==3 and q['stage']=='der');cases.append({'label':'SigmoidRate','kind':'cl','mode':3,'start':q['p'],'bounds':q['bounds'],'source':'mode 3 derivative in clamped_results.json'})
 # power equilibrium starts copied explicitly from helper derivative fit; no bound reached.
 cases.append({'label':'PowerEquilibrium','kind':'power','start':[.027574278369010833,1.020084922428101,.0989027948210846,5.817338126145302,1.543651890065043],'bounds':[[.0001,.5,0,.01,.01],[.35,1.5,20,12,12]],'source':'power_product derivative in helper_results.json'})
 return cases

def residual(p,case,d,what):
 kind=case['kind'];a=d.x1.values/60;b=d.x2.values/20;y=d.y.values;t=d.dy.values
 if kind=='poly':
  pw=np.array(case['powers']);return design(d,pw)@p-t if what=='der' else rollout(p,pw,y,a,b)
 if kind=='power':
  k,y0,c,n,m=p;q=y0+c*np.maximum(a,0)**n*np.maximum(b,0)**m
  if what=='der':return k*(q-y)-t
  h=-5*k;r=1+h+h*h/2+h**3/6+h**4/24
  yh=lfilter([1-r],[1,-r],q[:-1],zi=[r*y[0]])[0];return yh-y[1:]
 module={'nl':nl,'rat':rat,'cl':cl}[kind];args=(case['mode'],y,a,b)
 return module.dr(p,*args,t) if what=='der' else module.sim(p,*args)

def criterion(p,case,ds,weight):
 rr=[]
 for d in ds:
  if weight=='derivative':rr.append(residual(p,case,d,'der'))
  else:
   rr.append(residual(p,case,d,'roll'))
   if weight>0:rr.append(10*np.sqrt(weight)*residual(p,case,d,'der'))
 return np.concatenate(rr)

def fit(case,ds,weight):
 bounds=(-np.inf,np.inf) if case['bounds'] is None else tuple(case['bounds'])
 sol=least_squares(lambda p:criterion(p,case,ds,weight),np.array(case['start']),bounds=bounds,max_nfev=800,x_scale='jac',ftol=1e-10,xtol=1e-10,gtol=1e-10)
 return sol
if __name__=='__main__':
 tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv');prefix=va.iloc[:728].copy();hold=va.iloc[728:].copy();results=[]
 for case in load_cases():
  selection=[]
  for weight in ['derivative',0,1,10]:
   sol=fit(case,[tr,prefix],weight);r={'weight':weight,'p':sol.x.tolist(),'nfev':sol.nfev,'holdout_roll':float(np.mean(residual(sol.x,case,hold,'roll')**2)**.5),'holdout_der':float(np.mean(residual(sol.x,case,hold,'der')**2)**.5)};selection.append(r);print(case['label'],r)
  best=min(selection,key=lambda r:r['holdout_roll']);weight=best['weight'];sol=fit(case,[tr,va],weight)
  rec={**case,'selection':selection,'weight':weight,'p':sol.x.tolist(),'nfev':sol.nfev,'cost':float(sol.cost)}
  for fn,d in [('train',tr),('val',va)]:
   for what in ['roll','der']:rec[fn+'_'+what]=float(np.mean(residual(sol.x,case,d,what)**2)**.5)
  results.append(rec);print('FINAL',case['label'],weight,rec['p'],rec['train_roll'],rec['val_roll']);json.dump(results,open('final_fit_results.json','w'),indent=2)
