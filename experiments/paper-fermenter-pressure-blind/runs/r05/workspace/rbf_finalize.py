import json,numpy as np,pandas as pd
from rbf_fit import RBFModel
from refine import refine,rollout
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
if __name__=='__main__':
 rs=json.load(open('rbf_screen_results.json'));r=min(rs,key=lambda r:r['roll'][1]);m=RBFModel(r['centers'],r['width']);start=np.array(r['coef'])
 bounds=(np.full(m.m,-np.inf),np.r_[np.inf,-.001,np.full(m.m-2,np.inf)])
 c,opt=refine(m,start,[tr],bounds=bounds,maxn=100,reg=.01)
 roll=[float(np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2))) for d in [tr,va]]
 print('RBF TRAIN',opt.nfev,roll,flush=True)
 traincoef=c.copy()
 c,opt=refine(m,c,[tr,va],bounds=bounds,maxn=120,reg=.01)
 roll=[float(np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2))) for d in [tr,va]]
 print('RBF FINAL',opt.nfev,roll,c,flush=True)
 json.dump(dict(label='gaussian_field',centers=r['centers'],width=r['width'],reg=r['reg'],der_start=start.tolist(),traincoef=traincoef.tolist(),train_roll=roll,coef=c.tolist(),roll=roll,nfev=opt.nfev),open('rbf_final_results.json','w'),indent=2)
