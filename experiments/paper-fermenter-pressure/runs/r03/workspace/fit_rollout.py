import numpy as np,pandas as pd,math,json,time
from scipy.optimize import least_squares
D={s:pd.read_csv('data/'+s+'.csv').to_numpy() for s in ['train','val']}
# columns p valve flow dp
DER=json.load(open('derivative_fits.json'))

def rollout(t, data, pl,vl):
 a,c,m,k,pa,e,n=t
 p=data[0,0];out=np.empty(len(data));out[0]=p
 def f(pp,cv,qq):
  z=pp-pa
  if pl=='linear':h=z
  elif pl=='sqrt':h=z/(z*z+e*e)**.25
  elif pl=='compress':h=z*math.sqrt(max(pp+pa,.01))/(z*z+e*e)**.25
  elif pl=='series':h=2*z/(e+math.sqrt(e*e+4*abs(z)))
  elif pl=='choked':
   # smoothed pressure ratio, sonic limiting beyond critical ratio
   pu=max(pp,pa);pd=max(min(pp,pa),.01);rr=max(pd/pu,(2/2.4)**(1.4/.4));ss=max(rr**(2/1.4)-rr**(2.4/1.4),0)
   h=math.copysign(pu*math.sqrt(7*ss),z)*abs(z)/(z*z+e*e)**.5
  else:h=z*(z*z+e*e)**((n-1)/2)
  return a*qq-c*cv*h
 try:
  for i in range(len(data)-1):
   xx=max(0.,min(1.,1-data[i,1]/100));qq=data[i,2]
   if vl=='power':cv=xx**m
   elif vl=='exponential':cv=math.expm1(k*xx)/math.expm1(k)
   elif vl=='saturated':cv=(xx/(xx+k))**m
   elif vl=='rational':cv=xx**m/math.sqrt(xx**(2*m)+k**(2*m))
   else:
    def sig(z):return 1/(1+math.exp(-z))
    cv=(sig(k*(xx-m))-sig(-k*m))/(sig(k*(1-m))-sig(-k*m))
   k1=f(p,cv,qq);k2=f(p+2.5*k1,cv,qq);k3=f(p+2.5*k2,cv,qq);k4=f(p+5*k3,cv,qq)
   p+=5*(k1+2*k2+2*k3+k4)/6
   if not math.isfinite(p) or abs(p)>20:out[i+1:]=20;return out
   out[i+1]=p
 except (OverflowError,ValueError,ZeroDivisionError):out[i+1:]=20
 return out

def run():
 results=[]
 for pl,vl in [('linear','saturated'),('sqrt','saturated'),('compress','saturated'),('power','saturated'),('series','saturated'),('choked','saturated'),('power','rational'),('power','logistic'),('compress','rational')]:
  if pl in ['series','choked']:dr=next(z for z in DER if z['pl']=='compress' and z['vl']=='saturated')
  elif vl=='rational':dr=next(z for z in DER if z['pl']==pl and z['vl']=='saturated')
  else:dr=next(z for z in DER if z['pl']==pl and z['vl']==vl)
  t0=np.array(dr['t']);t0[4]=.99
  if pl=='series':t0[1]=.15;t0[5]=.15
  if pl=='choked':t0[1]=.06;t0[5]=.02
  if vl=='rational':t0[2]=1.7;t0[3]=.35
  active=[0,1,2,3,4]+([] if pl=='linear' else [5])+([6] if pl=='power' else [])
  lo=np.array([.0001,.0001,.2,.003,.97,.001,.3]);hi=np.array([.005,3,15,3,1.02,.6,1.3])
  if vl=='logistic':hi[2]=.9;hi[3]=30
  def unpack(x):t=t0.copy();t[active]=x;return t
  ts=time.time()
  r=least_squares(lambda x:(rollout(unpack(x),D['train'],pl,vl)[1:]-D['train'][1:,0]),t0[active],bounds=(lo[active],hi[active]),max_nfev=240,x_scale='jac',ftol=2e-8,xtol=2e-8,diff_step=1e-4)
  t=unpack(r.x);metrics={s:float(np.sqrt(np.mean((rollout(t,data,pl,vl)[1:]-data[1:,0])**2))) for s,data in D.items()}
  result=dict(pl=pl,vl=vl,t=t.tolist(),start=t0.tolist(),active=active,lo=lo.tolist(),hi=hi.tolist(),metrics=metrics,nfev=r.nfev,cost=r.cost,message=r.message)
  results.append(result);print(pl,vl,metrics,'t',t,'nfev',r.nfev,'sec',time.time()-ts,flush=True)
  json.dump(results,open('rollout_fits.json','w'),indent=2)
if __name__=='__main__':run()
