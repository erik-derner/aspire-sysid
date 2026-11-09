import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
tr=pd.read_csv('data/train.csv'); va=pd.read_csv('data/val.csv')
print('ranges',tr.describe().to_string()); print('groups',tr.groupby('trajectory').agg({'y':['min','max'],'x1':['min','max'],'x2':['min','max']}))
# Models: linear oscillator, sinusoidal restoring, sinusoidal plus smoothed Coulomb, input cubic, quadratic damping, affine offset.
def features(d, family,k=1,s=0.1):
 y,v,u=d['y'].to_numpy(),d['x1'].to_numpy(),d['x2'].to_numpy()
 base=[y if family=='linear' else np.sin(k*y),v,u,np.ones(len(y))]; names=['y' if family=='linear' else 'sin(k*y)','x1','x2','1']
 if 'coulomb' in family:base.append(np.tanh(v/s));names.append('tanh(x1/s)')
 if 'cubic' in family:base.extend([u**3]);names.extend(['x2**3'])
 if 'quad' in family:base.extend([v*np.abs(v)]);names.extend(['x1*Abs(x1)'])
 return np.array(base).T,names
out=[]
for fam in ['linear','sin','sin_coulomb','sin_cubic','sin_coulomb_cubic','sin_coulomb_quad','sin_coulomb_cubic_quad']:
 for k in ([1] if fam=='linear' else [0.1,0.5,1,2,3,5,10]):
  for s in ([.01,.05,.1,.3,1] if 'coulomb' in fam else [.1]):
   A,n=features(tr,fam,k,s);b=np.linalg.lstsq(A,tr.dx1,rcond=None)[0]; rt=np.sqrt(np.mean((A@b-tr.dx1)**2)); Av,_=features(va,fam,k,s);rv=np.sqrt(np.mean((Av@b-va.dx1)**2));out.append(dict(family=fam,k=k,s=s,coef=b.tolist(),names=n,train=rt,val=rv))
print('best derivative',json.dumps(sorted(out,key=lambda x:x['val'])[:12],indent=2));json.dump(out,open('helper_screen.json','w'),indent=2)
