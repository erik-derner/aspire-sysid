import numpy as np,pandas as pd,json
from scipy.linalg import lstsq
from scipy.optimize import least_squares
from numba import njit
# Features codes: 0 constant; 1 z; 2 a; 3 b; 4 z*a; 5 z*b; 6 z*z; 7 a*a; 8 b*b;
# 10 a hinge square,11 b hinge square,12 z hinge square,13 z*a hinge,14 z*b hinge.
@njit
def feature(v,a,b,code,k):
 z=v-1
 if code==0:return 1.
 if code==1:return z
 if code==2:return a
 if code==3:return b
 if code==4:return z*a
 if code==5:return z*b
 if code==6:return z*z
 if code==7:return a*a
 if code==8:return b*b
 if code==10:return max(a-k,0)**2
 if code==11:return max(b-k,0)**2
 if code==12:return max(z-k,0)**2
 if code==13:return z*max(a-k,0)
 if code==14:return z*max(b-k,0)
 return 0.
@njit
def design(d,codes,knots):
 X=np.empty((len(d),len(codes)))
 for i in range(len(d)):
  for j in range(len(codes)):X[i,j]=feature(d[i,0],d[i,1]/60,d[i,2]/20,codes[j],knots[j])
 return X
@njit
def sim(p,codes,knots,y,a,b):
 v=y[0];r=np.empty(len(y)-1)
 for i in range(len(r)):
  ks=np.empty(4)
  for s in range(4):
   vv=v
   if s==1:vv+=2.5*ks[0]
   if s==2:vv+=2.5*ks[1]
   if s==3:vv+=5*ks[2]
   ks[s]=0.
   for j in range(len(p)):ks[s]+=p[j]*feature(vv,a[i],b[i],codes[j],knots[j])
  v+=5/6*(ks[0]+2*ks[1]+2*ks[2]+ks[3])
  if not np.isfinite(v) or abs(v)>100:
   for j in range(i,len(r)):r[j]=1000
   return r
  r[i]=v-y[i+1]
 return r
if __name__=='__main__':
 ds={n:pd.read_csv('data/'+n+'.csv') for n in ['train','val']};tr=ds['train'];records=[]
 for nk in [1,2,3]:
  qs=np.linspace(0,1,nk+2)[1:-1];codes=list(range(9));knots=[0.]*9
  for code,col,scale,offset in [(10,'x1',60,0),(11,'x2',20,0),(12,'y',1,1),(13,'x1',60,0),(14,'x2',20,0)]:
   for k in np.quantile(tr[col]/scale-offset,qs):codes.append(code);knots.append(k)
  codes=np.array(codes);knots=np.array(knots);X=design(tr.values,codes,knots);c=lstsq(X,tr.dy)[0]
  for count in range(len(c),8,-1):
   if count in [len(c),20,15,12,10,9]:
    out={'nk':nk,'count':count,'codes':codes.tolist(),'knots':knots.tolist(),'p':c.tolist()}
    for fn,d in ds.items():
     out[fn+'_der']=float(np.mean((design(d.values,codes,knots)@c-d.dy)**2)**.5);out[fn+'_roll']=float(np.mean(sim(c,codes,knots,d.y.values,d.x1.values/60,d.x2.values/20)**2)**.5)
    records.append(out);print({k:v for k,v in out.items() if k not in ['codes','knots','p']});json.dump(records,open('spline_results.json','w'),indent=2)
   best=None
   for j in range(len(c)):
    keep=np.arange(len(c))!=j;cc=lstsq(X[:,keep],tr.dy)[0];loss=np.sum((X[:,keep]@cc-tr.dy)**2)
    if best is None or loss<best[0]:best=(loss,keep,cc)
   _,keep,c=best;codes=codes[keep];knots=knots[keep];X=X[:,keep]
