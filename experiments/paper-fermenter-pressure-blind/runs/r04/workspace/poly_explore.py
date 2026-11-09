import numpy as np,pandas as pd,json
from sklearn.preprocessing import PolynomialFeatures
from scipy.linalg import lstsq
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
def inputs(d,kind):
 y=d.y.values
 if kind=='raw': z=(y-1.3)/.3
 elif kind=='sqrt': z=np.sqrt(np.maximum(y-.99,0))
 elif kind=='log': z=np.log(np.maximum(y-.98,.001))
 return np.array([z,d.x1.values/70,d.x2.values/20]).T
def rollout(d,p,co,kind):
 yy=np.zeros(len(d)); yy[0]=d.y.iloc[0];
 def f(y,u,v):
  z=(y-1.3)/.3 if kind=='raw' else np.sqrt(max(y-.99,0)) if kind=='sqrt' else np.log(max(y-.98,.001))
  return sum(c*z**i*u**j*v**k for c,(i,j,k) in zip(co,p.powers_))
 for k in range(len(d)-1):
  u=d.x1.iloc[k]/70;v=d.x2.iloc[k]/20;y=yy[k];a=f(y,u,v);b=f(y+2.5*a,u,v);c=f(y+2.5*b,u,v);e=f(y+5*c,u,v);yy[k+1]=y+5/6*(a+2*b+2*c+e)
  if not np.isfinite(yy[k+1]) or abs(yy[k+1])>100:return 999,yy
 return np.sqrt(np.mean((yy[1:]-d.y.values[1:])**2)),yy
out=[]
for kind in ['raw','sqrt','log']:
 for deg in range(1,6):
  p=PolynomialFeatures(deg); X=p.fit_transform(inputs(tr,kind));V=p.transform(inputs(va,kind));co=lstsq(X,tr.dy.values)[0]
  a=np.sqrt(np.mean((X@co-tr.dy.values)**2));b=np.sqrt(np.mean((V@co-va.dy.values)**2));rt,_=rollout(tr,p,co,kind);rv,yp=rollout(va,p,co,kind)
  print(kind,deg,'deriv',a,b,'roll',rt,rv,flush=True);out.append(dict(kind=kind,degree=deg,coefficients=co.tolist(),powers=p.powers_.tolist(),tr=a,va=b,rt=rt,rv=rv))
json.dump(out,open('poly_results.json','w'),indent=2)
