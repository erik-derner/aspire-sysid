import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
D=pd.read_csv('data/train.csv');B=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in D.groupby('trajectory')]
# p: speed offset, speed gain, yaw terms
START={'linear':[0,.1667,.15,0], 'bilinear':[0,.1667,.15,0,0], 'cubic':[0,.1667,.15,0,0,0], 'deadzone':[0,.1667,.16,0,.02,.2], 'saturating':[0,.1667,.18,0,1], 'speedquad':[0,.1667,.15,0,0,0]}
def yaw(p,b,f):
 u=b[:-1,3];w=b[:-1,4]
 z=p[2]*w+p[3]
 if f in ['bilinear','cubic']:z=z+p[4]*u*w
 if f=='cubic':z=z+p[5]*w**3
 if f=='deadzone':z=z-p[4]*np.tanh(w/p[5])
 if f=='saturating':z=p[2]*np.tanh(p[4]*w)+p[3]
 return z
def sim(p,b,f):
 z=yaw(p,b,f);th=b[0,2]+np.r_[0,np.cumsum(z)];mid=th[:-1]+z/2;v=p[0]+p[1]*b[:-1,3]
 if f=='speedquad':v=v+p[4]*b[:-1,3]**2+p[5]*b[:-1,3]*b[:-1,4]**2
 xy=b[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[v*np.cos(mid),v*np.sin(mid)],axis=0)])
 return np.c_[xy,th]
def residual(p,blocks,f):
 return np.concatenate([(sim(p,b,f)[1:]-np.c_[b[1:,:2],np.unwrap(b[:,2])[1:]]).ravel() for b in blocks])
def fit(blocks,f):
 p0=np.array(START[f]);lo=np.full(len(p0),-np.inf);hi=-lo
 if f=='deadzone':lo[4:]=[0,.02];hi[4:]=[.2,2]
 if f=='saturating':lo[2]=.01;hi[2]=2;lo[4]=.05;hi[4]=10
 return least_squares(residual,p0,args=(blocks,f),bounds=(lo,hi),max_nfev=1000,ftol=1e-11,xtol=1e-11,gtol=1e-11).x
def rmse(s,b):return np.sqrt(np.mean((s[1:,0]-b[1:,0])**2))
R={}
for f in START:
 p=fit(B,f);cv=[];pars=[]
 for i in range(3):
  q=fit([b for j,b in enumerate(B) if i!=j],f);cv.append(rmse(sim(q,B[i],f),B[i]));pars.append(q.tolist())
 train=[rmse(sim(p,b,f),b) for b in B]
 R[f]={'p':p.tolist(),'train':train,'cv':cv,'cvpars':pars};print(f,'p',p,'train',train,'cv',cv,'cvmean',np.sqrt(np.mean(np.array(cv)**2)))
# Generic polynomial discrete maps
for degree in [1,2,3]:
 poly=PolynomialFeatures(degree);X=np.vstack([b[:-1] for b in B]);Y=np.vstack([b[1:,:3] for b in B]);Phi=poly.fit_transform(X)
 def polyfit(blocks):
  x=np.vstack([b[:-1] for b in blocks]);dy=np.vstack([b[1:,:3]-b[:-1,:3] for b in blocks]);dy[:,2]=np.arctan2(np.sin(dy[:,2]),np.cos(dy[:,2]));return np.linalg.lstsq(poly.transform(x),dy,rcond=None)[0]
 def polysim(c,b):
  s=np.zeros((len(b),3));s[0]=b[0,:3]
  for k in range(len(b)-1):
   a=np.r_[s[k],b[k,3:]];s[k+1]=s[k]+poly.transform(a[None,:])[0]@c;s[k+1,2]=np.arctan2(np.sin(s[k+1,2]),np.cos(s[k+1,2]))
   if np.max(np.abs(s[k+1]))>1e3:return np.full_like(s,np.nan)
  return s
 c=polyfit(B);train=[rmse(polysim(c,b),b) for b in B];cv=[rmse(polysim(polyfit([b for j,b in enumerate(B) if i!=j]),B[i]),B[i]) for i in range(3)];print('polynomial',degree,'train',train,'cv',cv)
 R['poly'+str(degree)]={'train':train,'cv':cv}
json.dump(R,open('experiment_results.json','w'),indent=2)
if __name__=='__main__':
 for f in START:
  p=np.array(R[f]['p']);res=[]
  for b in B:
   z=yaw(p,b,f);obs=np.diff(np.unwrap(b[:,2]));pos=np.diff(b[:,:2],axis=0);mid=b[:-1,2]+z/2;v=p[0]+p[1]*b[:-1,3];pred=np.c_[v*np.cos(mid),v*np.sin(mid)];res.append(np.c_[pos-pred,obs-z])
  e=np.vstack(res);print('residual',f,'mean',e.mean(0),'rms',np.sqrt(np.mean(e**2,axis=0)),'lag1',[np.corrcoef(e[:-1,j],e[1:,j])[0,1] for j in range(3)])
