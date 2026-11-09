import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from numba import njit
from fit_polys import rollout,design,score
@njit
def ff(y,a,b,p,model):
 k,g,y0,c,n,m=p[:6];z=y-y0
 if model==0:return -k*(1-g*a)*np.sign(z)*abs(z)**m+c*max(b,0)**n
 if model==1:return -k*(1-g*a)*np.arcsinh(m*z)/m+c*max(b,0)**n
 if model==2:return -k*max(1-g*a,.001)**m*z+c*max(b,0)**n
 if model==3:return -k*(1-g*a)*z+c*max(b,0)**n*np.exp(m*a)
 if model==4:return -k*(1-g*a)*z+c*max(b,0)**n*(1+m*a)
 if model==5:return -k*(1-g*a)*np.sign(z)*abs(z)**m+c*max(b,0)**n+p[6]*a**3
 if model==6:return -k*(1-g*a)*(np.exp(m*z)-1)/m+c*max(b,0)**n
 if model==7:return -k*(1-g*a)*(1-np.exp(-m*z))/m+c*max(b,0)**n
 if model==8:return -k*max(1-g*a-p[6]*b,.001)**m*z+c*max(b,0)**n
 if model==9:return -k*(1-g*a)*z+c*max(b,0)**n+m*a*(a-1)
 return 0.
@njit
def sim(p,model,yy,a,b):
 v=yy[0];r=np.empty(len(yy)-1)
 for i in range(len(r)):
  k1=ff(v,a[i],b[i],p,model);k2=ff(v+2.5*k1,a[i],b[i],p,model);k3=ff(v+2.5*k2,a[i],b[i],p,model);k4=ff(v+5*k3,a[i],b[i],p,model)
  v+=5/6*(k1+2*k2+2*k3+k4)
  if not np.isfinite(v) or abs(v)>100:
   for j in range(i,len(r)):r[j]=1000
   return r
  r[i]=v-yy[i+1]
 return r
@njit
def dr(p,model,y,a,b,t):
 r=np.empty(len(y))
 for i in range(len(y)):r[i]=ff(y[i],a[i],b[i],p,model)-t[i]
 return r
names=['signed_power','asinh_feedback','power_rate','exp_cross_source','linear_cross_source','signed_power_cubic','exp_feedback','saturating_exp_feedback','two_input_power_rate','quad_source']
if __name__=='__main__':
 ds={n:pd.read_csv('data/'+n+'.csv') for n in ['train','val']};tr=ds['train'];recs=[]
 for model,name in enumerate(names):
  start=np.array([.18,.66,.99,.012,1.7, .8 if model in [0,2,5,8] else .2]+([.001] if model==5 else ([.05] if model==8 else [])))
  lo=np.array([.0001,-3,.7,0,.2,.2 if model in [0,2,5,8] else -3]+([-1.] if model in [5,8] else []))
  hi=np.array([2,3,1.3,.5,8,3]+([1.] if model in [5,8] else []))
  args=(model,tr.y.values,tr.x1.values/60,tr.x2.values/20)
  sol=least_squares(lambda p:dr(p,*args,tr.dy.values),start,bounds=(lo,hi),max_nfev=1200,x_scale='jac',ftol=1e-10,gtol=1e-10,xtol=1e-10)
  for stage in ['der','roll']:
   if stage=='der':p=sol.x;init=start.tolist()
   else:
    init=p.tolist();sol=least_squares(lambda p:sim(p,*args),p,bounds=(lo,hi),max_nfev=600,x_scale='jac',ftol=1e-10,gtol=1e-10,xtol=1e-10);p=sol.x
   r={'name':name,'model':model,'stage':stage,'p':p.tolist(),'start':init,'bounds':[lo.tolist(),hi.tolist()]}
   for fn,d in ds.items():
    aa=(model,d.y.values,d.x1.values/60,d.x2.values/20);r[fn+'_der']=np.mean(dr(p,*aa,d.dy.values)**2)**.5;r[fn+'_roll']=np.mean(sim(p,*aa)**2)**.5
   recs.append(r);print({k:v for k,v in r.items() if k not in ['start','bounds']});json.dump(recs,open('extended_results.json','w'),indent=2)
