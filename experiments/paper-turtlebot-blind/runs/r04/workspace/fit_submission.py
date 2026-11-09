"""Reproduce final candidates and diagnostics using training data only."""
import json, pathlib, numpy as np
# Load the recorded fitting functions, without executing their sweep loops.
exec(open('refine.py').read().split('\nR={}\n')[0])

def absolute_fit(ids):
 co,vc=fit('wheelpoly',ids,'lag')
 hh=[];dh=[];r=[];arcX=[];arcY=[]
 for i in ids:
  s=S[i];hc=features(s['u'],s['w'],'wheelpoly')@co;hp=features(s['up'],s['wp'],'wheelpoly')@co
  dh.extend((hp-hc)[1:]);r.extend((s['h']-hc)[1:])
  sel=np.arange(149)%5>=2;arcX.append(np.c_[np.ones(149),s['v']*s['h']][sel]);arcY.extend(s['side'][sel])
 delay=np.dot(dh,r)/np.dot(dh,dh)
 arc=np.linalg.lstsq(np.vstack(arcX),arcY,rcond=None)[0][1]
 # p: forward gain, offset, yaw gain, abs contrast gain, width, bias, midpoint
 p=np.r_[vc[1],vc[0],co[1],co[2],.1,co[0],arc-delay]
 return p,float(arc),float(delay)

A={}
for label,f,w in [('CoupledDeadzone','deadwheel',40),('SmoothAngular','smoothyaw',12),('LinearKinematic','affineyaw',-1)]:
 p,p0,lag,loss=fit2(f,[0,1,2],w);A[label]={'p':p.tolist(),'p0':p0.tolist(),'lag':lag.tolist(),'loss':loss,'family':f,'weight':w}
p,arc,delay=absolute_fit([0,1,2]);A['AbsoluteCoupling']={'p':p.tolist(),'arc':arc,'delay':delay,'family':'absyaw','weight':None}
for label,a in A.items():
 f=a['family'];p=np.array(a['p']);cv=[];train=[];step=[];phase=[]
 for i in range(3):
  ids=[j for j in range(3) if j!=i]
  pc=absolute_fit(ids)[0] if label=='AbsoluteCoupling' else fit2(f,ids,a['weight'])[0]
  ss=sim2(pc,f,i);ee=ss-G[i][:,:3];ee[:,2]=ss[:,2]-U[i];cv.append(np.sqrt(np.mean(ee[1:]**2,axis=0)).tolist())
  ss=sim2(p,f,i);ee=ss-G[i][:,:3];ee[:,2]=ss[:,2]-U[i];train.append(np.sqrt(np.mean(ee[1:]**2,axis=0)).tolist())
  g=G[i];v,h,m=cal(p,g[:-1,3],g[:-1,4],f);pred=np.c_[v*np.cos(g[:-1,2]+m*h),v*np.sin(g[:-1,2]+m*h),h];obs=np.c_[np.diff(g[:,:2],axis=0),np.diff(U[i])];step.append(obs-pred);phase.extend(np.arange(149)%5)
 e=np.vstack(step);phase=np.array(phase)
 a['train_rmse']=train;a['cv_rmse']=cv;a['pooled_train_y']=float(np.sqrt(np.mean(np.array(train)[:,0]**2)));a['pooled_cv_y']=float(np.sqrt(np.mean(np.array(cv)[:,0]**2)));a['one_step_rmse']=np.sqrt(np.mean(e**2,axis=0)).tolist();a['phase0_rmse']=np.sqrt(np.mean(e[phase==0]**2,axis=0)).tolist();a['other_phase_rmse']=np.sqrt(np.mean(e[phase!=0]**2,axis=0)).tolist();a['step_mean']=e.mean(axis=0).tolist()
 print(label,a)
json.dump(A,open('submission_fits.json','w'),indent=2)
