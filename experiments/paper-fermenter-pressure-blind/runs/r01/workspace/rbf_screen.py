import numpy as np,pandas as pd,json
from sklearn.cluster import KMeans
A=pd.read_csv('data/train.csv');B=pd.read_csv('data/val.csv');scale=np.array([.4,30.,10.]);off=np.array([1.,60.,18.]);Z=(A[['y','x1','x2']].to_numpy()-off)/scale;W=(B[['y','x1','x2']].to_numpy()-off)/scale
results=[]
def features(z,cent,w):return np.c_[np.ones(len(z)),z,np.exp(-np.sum((z[:,None,:]-cent[None,:,:])**2,axis=2)/(2*w*w))]
def sim(c,cent,w,d):
 y=np.empty(len(d));y[0]=d.y.iloc[0];u=(d.x1.to_numpy()-off[1])/scale[1];v=(d.x2.to_numpy()-off[2])/scale[2]
 # per-input factors precomputed
 G=np.exp(-((u[:,None]-cent[None,:,1])**2+(v[:,None]-cent[None,:,2])**2)/(2*w*w))
 def f(s,k):
  z=(s-off[0])/scale[0];return c[0]+c[1]*z+c[2]*u[k]+c[3]*v[k]+np.dot(c[4:]*G[k],np.exp(-(z-cent[:,0])**2/(2*w*w)))
 for k in range(len(d)-1):
  s=y[k];a=f(s,k);b=f(s+2.5*a,k);e=f(s+2.5*b,k);h=f(s+5*e,k);y[k+1]=s+5/6*(a+2*b+2*e+h)
  if not np.isfinite(y[k+1]) or abs(y[k+1])>100:return np.full(len(d),1e3)
 return y
for n in [12,24,40,64]:
 cent=KMeans(n_clusters=n,random_state=42,n_init=10).fit(Z).cluster_centers_
 for w in [.7,1.,1.5,2.]:
  X=features(Z,cent,w);V=features(W,cent,w)
  for alpha in [1e-5,.001,.1,1.]:
   # base linear slope penalty slightly smaller than RBF coefficients
   reg=np.diag(np.r_[np.ones(4)*.01,np.ones(n)])
   c=np.linalg.solve(X.T@X+alpha*reg,X.T@A.dy.to_numpy());tr=sim(c,cent,w,A);va=sim(c,cent,w,B)
   out=dict(n=n,w=w,alpha=alpha,c=c.tolist(),cent=cent.tolist(),train_d=np.sqrt(np.mean((X@c-A.dy)**2)),val_d=np.sqrt(np.mean((V@c-B.dy)**2)),train_y=np.sqrt(np.mean((tr[1:]-A.y.to_numpy()[1:])**2)),val_y=np.sqrt(np.mean((va[1:]-B.y.to_numpy()[1:])**2)))
   results.append(out);print(n,w,alpha,out['train_d'],out['val_d'],out['train_y'],out['val_y'],flush=True)
json.dump(results,open('rbf_results.json','w'),indent=2)
