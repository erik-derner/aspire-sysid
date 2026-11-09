import numpy as np,pandas as pd,json
from sklearn.preprocessing import PolynomialFeatures
from scipy.linalg import lstsq
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
def feats(d,degree,mode):
 z=np.column_stack((d.y.values-1,d.x1.values/60,d.x2.values/20));p=PolynomialFeatures(degree);X=p.fit_transform(z);pw=p.powers_
 if mode=='relax':keep=(pw[:,0]<=1)&((pw[:,0]==0)|(pw.sum(axis=1)==1))
 elif mode=='state2':keep=pw[:,0]<=2
 else:keep=np.ones(len(pw),bool)
 return X[:,keep],pw[keep]
def sim(d,c,pw):
 y=np.empty(len(d));y[0]=d.y.iloc[0];x1=d.x1.values/60;x2=d.x2.values/20
 def f(v,a,b):return np.sum(c*(v-1)**pw[:,0]*a**pw[:,1]*b**pw[:,2])
 for i in range(len(d)-1):
  v=y[i];a=x1[i];b=x2[i];k1=f(v,a,b);k2=f(v+2.5*k1,a,b);k3=f(v+2.5*k2,a,b);k4=f(v+5*k3,a,b);y[i+1]=v+5/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(y[i+1]) or abs(y[i+1])>100:return np.full(len(y),np.nan)
 return y
out=[]
for deg in range(1,6):
 for mode in ['full','relax','state2']:
  if deg==1 and mode!='full':continue
  X,pw=feats(tr,deg,mode);XV,_=feats(va,deg,mode);c=lstsq(X,tr.dy.values)[0];pt=X@c;pv=XV@c
  yt=sim(tr,c,pw);yv=sim(va,c,pw)
  r={'deg':deg,'mode':mode,'terms':len(c),'drtr':float(np.mean((pt-tr.dy)**2)**.5),'drva':float(np.mean((pv-va.dy)**2)**.5),'simtr':float(np.mean((yt[1:]-tr.y.values[1:])**2)**.5),'simva':float(np.mean((yv[1:]-va.y.values[1:])**2)**.5),'c':c.tolist(),'powers':pw.tolist()};out.append(r);print({k:v for k,v in r.items() if k not in ['c','powers']})
json.dump(out,open('poly_results.json','w'),indent=2)
