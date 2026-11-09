"""Reproduce final-stage estimates from the actual recorded initializations.
All training and validation rows are used; each file is one uninterrupted rollout.
Earlier structure/initialization searches are retained in their own scripts.
"""
import json,numpy as np,pandas as pd
from sklearn.cluster import KMeans
from refine import PolyModel,RationalModel,refine,rollout
from final_fit import CosModel
from rbf_fit import RBFModel

def fit_all():
 ds=[pd.read_csv('data/train.csv'),pd.read_csv('data/val.csv')];starts=json.load(open('fit_start_values.json'));out={}
 for label,r in starts.items():
  if label=='poly3':m=PolyModel(r['powers']);bounds=None;reg=0
  elif label=='rational2':m=RationalModel(r['powers']);bounds=r['bounds'];reg=0
  elif label=='cos_power':m=CosModel();m.eps=r['eps'];bounds=r['bounds'];reg=0
  elif label=='gaussian_field':
   tr=ds[0];A=np.c_[(tr.y.values-1)/.3,(tr.x1.values/60-1)*3,(tr.x2.values/20-1)*3]
   centers=KMeans(n_clusters=r['n'],random_state=2026,n_init=10).fit(A).cluster_centers_;m=RBFModel(centers,r['width']);reg=r['reg']
   bounds=(np.full(m.m,-np.inf),np.r_[np.inf,-.001,np.full(m.m-2,np.inf)])
  c,opt=refine(m,np.array(r['start']),ds,bounds=bounds,reg=reg,maxn=120)
  out[label]={'coef':c.tolist(),'roll':[float(np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2))) for d in ds],'nfev':opt.nfev}
  if label=='gaussian_field':out[label]['centers']=m.centers.tolist()
  print(label,out[label]['roll'],flush=True)
 json.dump(out,open('reproduced_results.json','w'),indent=2)
 return out
if __name__=='__main__':fit_all()
