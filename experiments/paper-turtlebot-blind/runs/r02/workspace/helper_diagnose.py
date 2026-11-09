import numpy as np,pandas as pd
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); blocks=[g.reset_index(drop=True) for _,g in D.groupby('trajectory')]
wrap=lambda a:np.arctan2(np.sin(a),np.cos(a))
Z=[];DD=[];UU=[];DE=[]
print('traj k u3 u4 dist/u3 yaw/u4')
for ti,g in enumerate(blocks):
 a=g[['y','x1','x2','x3','x4']].values
 for k in range(3,len(a)-1,5):
  d=a[k+1,:3]-a[k,:3];d[2]=wrap(d[2]);print(ti+1,k,*np.round(a[k,3:],5),round(np.linalg.norm(d[:2])/a[k,3],5),round(d[2]/a[k,4],5))
 for k in range(len(a)-1):
  d=a[k+1,:3]-a[k,:3];d[2]=wrap(d[2]);Z.append(a[k]);DD.append(d);UU.append(a[max(k-1,0),3:]);DE.append(k%5)
z=np.array(Z);de=np.array(DD);u=np.array(UU);depth=np.array(DE);mid=z[:,2]+de[:,2]/2;pr=de[:,0]*np.cos(mid)+de[:,1]*np.sin(mid)
# Rational fits may reveal velocity-dependent angular mobility.
for mask,name in [(np.ones(len(z),bool),'all'),(depth>=2,'stable')]:
 v=z[mask,3];w=z[mask,4];yaw=de[mask,2];dist=pr[mask]
 forms={
 'yaw w*(a+b*v)':(lambda p:w*(p[0]+p[1]*v),[.1,.1]),
 'yaw w/(a+b*v)':(lambda p:w/(p[0]+p[1]*v),[7,1]),
 'yaw w/(a+b*v+c*w*w)':(lambda p:w/(p[0]+p[1]*v+p[2]*w*w),[7,1,0]),
 'yaw tan(w)*(a+b*v)':(lambda p:np.tan(w)*(p[0]+p[1]*v),[.1,.1]),
 'yaw w*(a+b*v+c*v*v+d*w*w)':(lambda p:w*(p[0]+p[1]*v+p[2]*v*v+p[3]*w*w),[.1,.1,0,0]),
 'distance v*(a+b*v+c*w*w)':(lambda p:v*(p[0]+p[1]*v+p[2]*w*w),[.16,0,0]),
 'distance v/(a+b*v)':(lambda p:v/(p[0]+p[1]*v),[6,0]),
 }
 for label,(fn,p0) in forms.items():
  target=dist if label.startswith('distance') else yaw
  fit=least_squares(lambda p:fn(p)-target,p0);print(name,label,'N',sum(mask),'p',fit.x,'rmse',np.sqrt(np.mean(fit.fun**2)))
