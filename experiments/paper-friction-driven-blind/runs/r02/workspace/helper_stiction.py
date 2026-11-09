"""Follow-up zero-velocity/stiction and moving-only derivative fits. No candidates."""
import json,numpy as np,pandas as pd
from scipy.optimize import least_squares
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv');res={}
def pred(d,p,kind):
 y=d.y.values;v=d.x1.values;u=d.x2.values
 b,k,c,f,g=p[:5];q=b+k*np.sin(y)+g*u
 if kind=='moving':return q+c*v+f*np.sign(v)
 if kind=='smooth_drive':
  s=np.exp(p[5]);alpha=np.exp(p[6]);return q+c*v-f*np.tanh(v/s+alpha*q/f)
 if kind=='stiction_blend':
  s=np.exp(p[5]);v0=np.exp(p[6]);fs=np.exp(p[7]);w=np.exp(-(v/v0)**2)
  return (1-w)*(q+c*v-f*np.tanh(v/s))+w*np.sign(q)*np.maximum(np.abs(q)-fs,0)
for threshold in [0,.3,1,2]:
 mask=np.abs(tr.x1)>threshold; X=np.column_stack([np.ones(mask.sum()),np.sin(tr.y[mask]),tr.x1[mask],np.sign(tr.x1[mask]),tr.x2[mask]])
 p=np.linalg.lstsq(X,tr.dx1[mask],rcond=None)[0];label='moving_'+str(threshold)
 res[label]={'p':p.tolist(),'nfit':int(mask.sum()),'threshold':threshold,'form':'moving','initial':None}
for kind,p0,lo,hi in [('smooth_drive',[0,-105,-1.5,19,26,-1,0],[-10,-200,-20,1,0,-8,-4],[10,-10,5,100,100,3,4]),('stiction_blend',[0,-105,-1.5,19,26,-1,-1,3],[-10,-200,-20,1,0,-8,-8,0],[10,-10,5,100,100,3,3,5])]:
 opt=least_squares(lambda p:pred(tr,p,kind)-tr.dx1,p0,bounds=(lo,hi),max_nfev=1000)
 res[kind]={'p':opt.x.tolist(),'form':kind,'initial':p0,'bounds':[lo,hi],'success':bool(opt.success)}
for label,m in res.items():
 for tag,d in [('train',tr),('val',va)]:
  e=pred(d,m['p'],m['form'])-d.dx1
  m[tag+'_derivative_rmse']=float(np.sqrt(np.mean(e**2)))
  m[tag+'_moving_rmse']=float(np.sqrt(np.mean(e[np.abs(d.x1)>.3]**2)))
  m[tag+'_stationary_rmse']=float(np.sqrt(np.mean(e[d.x1==0]**2)))
  errors=[];bytraj={};failed=False
  p=m['p'];kind=m['form']
  def rhs(z,u):
   y,v=z;b,k,c,f,g=p[:5];q=b+k*np.sin(y)+g*u
   if kind=='moving':a=q+c*v+f*np.sign(v)
   elif kind=='smooth_drive':a=q+c*v-f*np.tanh(v/np.exp(p[5])+np.exp(p[6])*q/f)
   else:
    w=np.exp(-(v/np.exp(p[6]))**2);a=(1-w)*(q+c*v-f*np.tanh(v/np.exp(p[5])))+w*np.sign(q)*max(abs(q)-np.exp(p[7]),0)
   return np.array([v,a])
  for tid,a in d.groupby('trajectory'):
   z=a[['y','x1']].values[0].copy();yy=[z[0]]
   with np.errstate(all='ignore'):
    for u in a.x2.values[:-1]:
     k1=rhs(z,u);k2=rhs(z+.005*k1,u);k3=rhs(z+.005*k2,u);k4=rhs(z+.01*k3,u);z+=.01*(k1+2*k2+2*k3+k4)/6;yy.append(z[0])
     if not np.all(np.isfinite(z)) or np.max(np.abs(z))>1000:failed=True;break
   if len(yy)==len(a):
    e=np.array(yy)[1:]-a.y.values[1:];errors.extend(e);bytraj[str(tid)]=float(np.sqrt(np.mean(e**2)))
   else:bytraj[str(tid)]=None
  m[tag+'_rollout_rmse']=None if failed else float(np.sqrt(np.mean(np.array(errors)**2)));m[tag+'_rollout_bytraj']=bytraj
 print(label,m)
with open('helper_stiction_results.json','w') as f:json.dump(res,f,indent=2)
