import numpy as np,pandas as pd,json
from fit_models import accel,pack,simulate
from crossvalidate import combined
R=json.load(open('cv_results.json'));D=combined();D['row']=D.groupby('trajectory').cumcount()
for name in ['angle_asym','angle_smooth']:
 p=np.array(R[name]['p']);fam=R[name]['family'];pred=np.array([accel(t,w,u,p,fam) for t,w,u in D[['theta','omega','u']].to_numpy()]);r=D.domega.to_numpy()-pred;m=(abs(D.omega.to_numpy())>.8)&(D.row.to_numpy()>=5)
 t,w,u=D[['theta','omega','u']].to_numpy().T
 print(name,'moving derivative RMSE',np.sqrt(np.mean(r[m]**2)),'mean',r[m].mean())
 xs={'u':u,'u3':u**3,'wabsw':w*abs(w),'wcos':w*np.cos(t),'wsin':w*np.sin(t),'sintheta':np.sin(t),'sin2theta':np.sin(2*t),'wexp':w*np.exp(-(w/2)**2),'signexp':np.sign(w)*np.exp(-(w/2)**2),'signexp5':np.sign(w)*np.exp(-(w/5)**2)}
 print('corr',[(key,round(np.corrcoef(r[m],v[m])[0,1],3)) for key,v in xs.items()])
 for key,z,bins in [('w',w,[-25,-10,-5,-2,-.8,.8,2,5,10,25]),('u',u,[-5,-3,-2,-1,0,1,2,3,5]),('theta',t,[-3,-2,-1,-.5,0,.5,1,2,3])]:
  print('bins',key,[(lo,hi,int(sum(m&(z>=lo)&(z<hi))),round(float(np.mean(r[m&(z>=lo)&(z<hi)])),2)) for lo,hi in zip(bins[:-1],bins[1:]) if sum(m&(z>=lo)&(z<hi))])
 dat=pack(D);out=simulate(p,fam,*dat[:3]);print('angle end errors',[(j+1,round(out[j,n-1]-dat[3][j,n-1],4)) for j,n in enumerate(dat[2])])
