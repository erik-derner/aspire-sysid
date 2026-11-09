import json,math,numpy as np
R=json.load(open('pooled_fits.json'))
for r in R:
 if r['kind']!='base':continue
 a,c,m,k,pa,e,n=r['t'];cv=(1/(1+k))**m
 def f(p):
  z=p-pa;pl=r['name']
  if pl=='series':h=2*z/(e+math.sqrt(e*e+4*abs(z)))
  elif pl=='power':h=z*(z*z+e*e)**((n-1)/2)
  elif pl=='sqrt':h=z/(z*z+e*e)**.25
  elif pl=='linear':h=z
  elif pl=='compress':h=z*math.sqrt(max(p+pa,.01))/(z*z+e*e)**.25
  else:
   pu=max(p,pa);pd=max(min(p,pa),.01);rr=max(pd/pu,(2/2.4)**(1.4/.4));ss=max(rr**(2/1.4)-rr**(2.4/1.4),0);h=math.copysign(pu*math.sqrt(7*ss),z)*abs(z)/math.sqrt(z*z+e*e)
  return -c*cv*h
 grid=np.r_[np.linspace(pa-.1,pa+.3,10000),np.linspace(pa+.3,3,2000)];deriv=np.array([(f(p+1e-6)-f(p-1e-6))/2e-6 for p in grid]);print(r['name'],'most negative slope',deriv.min(),'RK4 local dt*slope',-5*deriv.min())
