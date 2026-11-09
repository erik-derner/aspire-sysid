import numpy as np,pandas as pd,json,time
from sklearn.cluster import KMeans
from scipy.optimize import least_squares
from refine import rollout,refine
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
class RBFModel:
 def __init__(self,centers,width):self.centers=np.array(centers);self.width=width;self.m=4+len(centers);self.kind='rbf'
 def fg(self,z,u,v,c):
  a=np.array([z/.3,(u-1)*3,(v-1)*3]);diff=a-self.centers
  B=np.exp(-np.sum(diff*diff,axis=1)/(2*self.width*self.width))
  X=np.r_[1,z,u,v,B];fx=c[1]+np.dot(c[4:]*B,-diff[:,0]/(.3*self.width*self.width))
  return X@c,fx,X
if __name__=='__main__':
 A=np.c_[(tr.y.values-1)/.3,(tr.x1.values/60-1)*3,(tr.x2.values/20-1)*3];out=[]
 for n in [8,16,24,40]:
  centers=KMeans(n_clusters=n,random_state=2026,n_init=10).fit(A).cluster_centers_
  for width in [.7,1.2,2]:
   m=RBFModel(centers,width);X=np.array([m.fg(y-1,u/60,v/20,np.zeros(m.m))[2] for y,u,v in tr[['y','x1','x2']].values]);V=np.array([m.fg(y-1,u/60,v/20,np.zeros(m.m))[2] for y,u,v in va[['y','x1','x2']].values])
   for reg in [.0001,.01,1]:
    c=np.linalg.lstsq(np.vstack([X,np.sqrt(reg)*np.eye(m.m)]),np.r_[tr.dy,np.zeros(m.m)],rcond=None)[0]
    if c[1]>=0:continue
    der=[np.sqrt(np.mean((X@c-tr.dy.values)**2)),np.sqrt(np.mean((V@c-va.dy.values)**2))]
    roll=[np.sqrt(np.mean((rollout(m,c,d)[1:]-d.y.values[1:])**2)) for d in [tr,va]]
    print(n,width,reg,'der',der,'roll',roll,flush=True)
    out.append(dict(n=n,width=width,reg=reg,centers=centers.tolist(),coef=c.tolist(),der=der,roll=roll))
 json.dump(out,open('rbf_screen_results.json','w'),indent=2)
