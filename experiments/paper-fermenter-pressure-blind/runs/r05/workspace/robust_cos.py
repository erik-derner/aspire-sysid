import numpy as np,pandas as pd,json
from final_fit import CosModel
from refine import rollout,refine
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
if __name__=='__main__':
 r=next(r for r in json.load(open('final_fit_results.json')) if r['label']=='cos_power');start=np.array(r['coef']);out=[]
 for eps in [.02,.05]:
  m=CosModel();m.eps=eps
  bounds=(np.array([-np.inf,0,0,0,.8,.4,.1,.1]),np.array([np.inf,np.inf,.03,.1,1.05,1,4,5]))
  c,opt=refine(m,start,[tr,va],bounds=bounds,maxn=100)
  score=[float(np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2))) for d in [tr,va]]
  worst=5*(c[2]+c[3])*eps**(c[5]-1)
  print('COS SMOOTH',eps,'roll',score,'slope_times_step_bound',worst,'coef',c,flush=True)
  out.append(dict(label='cos_power',eps=eps,start=start.tolist(),coef=c.tolist(),roll=score,step_slope_bound=float(worst),nfev=opt.nfev,bounds=[bounds[0].tolist(),bounds[1].tolist()]))
 json.dump(out,open('robust_cos_results.json','w'),indent=2)
