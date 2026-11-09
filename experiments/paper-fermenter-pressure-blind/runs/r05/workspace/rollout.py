import numpy as np,pandas as pd,json
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
for a,j in [(tr,725),(va,727)]:print(a.iloc[j-3:j+5].to_string())
def rk4(f,d):
 y=np.empty(len(d));y[0]=d.y.iloc[0];u=d[['x1','x2']].values
 for i in range(len(y)-1):
  a,b=u[i]; z=y[i];k1=f(z,a,b);k2=f(z+2.5*k1,a,b);k3=f(z+2.5*k2,a,b);k4=f(z+5*k3,a,b)
  y[i+1]=z+5*(k1+2*k2+2*k3+k4)/6
  if not np.isfinite(y[i+1]) or abs(y[i+1])>100:return np.full(len(y),1000.)
 return y
if __name__=='__main__':
 R=json.load(open('poly_results.json'))
 for r in R:
  if r['deg']>4:continue
  p=np.array(r['powers']);c=np.array(r['coef'])
  def f(y,u,v):return np.prod(np.array([y-1,u/60,v/20])**p,axis=1)@c
  scores=[]
  for d in [tr,va]:
   yp=rk4(f,d); scores.append(np.sqrt(np.mean((yp[1:]-d.y.values[1:])**2)))
  print(r['deg'],r['reg'],'roll',scores)
