import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
B=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in pd.read_csv('data/train.csv').groupby('trajectory')]
def sim(p,b):
 v=p[0]*b[:-1,3];w=b[:-1,4];z=p[1]*(w-p[3]*np.tanh(w/p[3]))+p[2];th=b[0,2]+np.r_[0,np.cumsum(z)];mid=th[:-1]+z/2;xy=b[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[v*np.cos(mid),v*np.sin(mid)],axis=0)]);return np.c_[xy,th]
def fit(blocks,weight):
 def r(p):return np.concatenate([((sim(p,b)[1:]-np.c_[b[1:,:2],np.unwrap(b[:,2])[1:]])*np.array([1,1,weight])).ravel() for b in blocks])
 return least_squares(r,[.1667,.2,.002,.1],bounds=([0,0,-.05,.001],[1,1,.05,1]),max_nfev=1500,ftol=1e-11,xtol=1e-11,gtol=1e-11).x
R={}
for w in [.3,1,3]:
 p=fit(B,w);cv=[np.sqrt(np.mean((sim(fit([b for j,b in enumerate(B) if i!=j],w),B[i])[1:,0]-B[i][1:,0])**2)) for i in range(3)];tr=[np.sqrt(np.mean((sim(p,b)[1:,0]-b[1:,0])**2)) for b in B];q=fit([b[:90] for b in B],w);future=[np.sqrt(np.mean((sim(q,b[89:])[1:,0]-b[90:,0])**2)) for b in B];print(w,p,tr,cv,'rms',np.sqrt(np.mean(np.array(cv)**2)),'future',future);R[str(w)]={'p':p.tolist(),'train':tr,'cv':cv,'forecast':future}
json.dump(R,open('monotone_results.json','w'),indent=2)
