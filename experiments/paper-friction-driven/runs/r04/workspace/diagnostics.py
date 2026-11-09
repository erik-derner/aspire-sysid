import numpy as np,pandas as pd,json
from fit_models import accel,pack,simulate
D=pd.read_csv('data/train.csv');V=pd.read_csv('data/val.csv');R=json.load(open('fit_results.json'))
for name in ['smooth','projection','stribeck','harmonic','asymmetric']:
 p=np.array(R[name]['p']);fam=R[name]['family'];pr=np.array([accel(t,w,u,p,fam) for t,w,u in D[['theta','omega','u']].to_numpy()]);r=D.domega.to_numpy()-pr;m=abs(D.omega.to_numpy())>.8
 print('\n',name,'derivative_RMSE_moving',np.sqrt(np.mean(r[m]**2)))
 for k,g in D.groupby('trajectory',sort=False):
  ix=g.index.to_numpy();q=ix[abs(g.omega.to_numpy())>.8]
  print(k,'mean accel residual',np.mean(r[q]) if len(q) else 0,'RMSE',np.sqrt(np.mean(r[q]**2)) if len(q) else 0)
 for fn,d in [('train',D),('val',V)]:
  dat=pack(d);out=simulate(p,fam,*dat[:3]);print(fn,'end errors',[round(out[j,n-1]-dat[3][j,n-1],4) for j,n in enumerate(dat[2])])
# expanded library on moving samples excluding initial encoder derivative transients
D['row']=D.groupby('trajectory').cumcount();d=D[(abs(D.omega)>.8)&(D.row>=5)]
t,w,u=d[['theta','omega','u']].to_numpy().T;y=d.domega.to_numpy()
names=['u','-w','-sin(t)','-sign(w)','-sin(t)**2','-sin(2*t)','-sign(w)*sin(t)','-sign(w)*cos(t)','1','u**3','-w*abs(w)']
Xs=[u,-w,-np.sin(t),-np.sign(w),-np.sin(t)**2,-np.sin(2*t),-np.sign(w)*np.sin(t),-np.sign(w)*np.cos(t),np.ones(len(t)),u**3,-w*abs(w)]
for select in [[0,1,2,3],[0,1,2,3,4],[0,1,2,3,6,7],[0,1,2,3,4,5,6,7,8,9,10]]:
 X=np.column_stack([Xs[i] for i in select]);p=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@p
 print('Library',list(zip([names[i] for i in select],p)),'RMSE',np.sqrt(np.mean(r*r)))
