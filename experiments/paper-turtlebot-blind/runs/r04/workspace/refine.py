import numpy as np,json
from scipy.optimize import least_squares
exec(open('reduced_explore.py').read().split('R={}')[0])
FAMS=['affineyaw','absyaw','deadwheel','smoothwheel','smoothyaw']
# v gain, v offset, angular gain, angular nonlinear coeff, width, angular bias, midpoint (some families special)
INITS={'affineyaw':[.169,0,.137,0,-.25], 'absyaw':[.169,0,.078,-.32,.1,-.00066,-.25], 'deadwheel':[.18,.015,.08,.91,0,-.25], 'smoothwheel':[.18,.001,.08,.91,.01,0,-.25], 'smoothyaw':[.169,0,.16,.014,.08,-.0003,-.25]}
def cal(p,u,w,f):
 if f=='affineyaw':a,b,c,d,m=p;v=a*u+b;h=c*w+d
 if f=='absyaw':a,b,c,d,l,e,m=p;v=a*u+b;h=c*w+d*(abs(u-l*w)-abs(u+l*w))+e
 if f=='deadwheel':a,d,l,c,e,m=p;L=u-l*w;R=u+l*w;L=np.sign(L)*np.maximum(abs(L)-d,0);R=np.sign(R)*np.maximum(abs(R)-d,0);v=a*(L+R)/2;h=c*(R-L)+e
 if f=='smoothwheel':a,d,l,c,s,e,m=p;L=u-l*w;R=u+l*w;L=L-d*np.tanh(L/s);R=R-d*np.tanh(R/s);v=a*(L+R)/2;h=c*(R-L)+e
 if f=='smoothyaw':a,b,c,d,s,e,m=p;v=a*u+b;h=c*w-d*np.tanh(w/s)+e
 return v,h,m
def bnds(f):
 if f=='affineyaw':return ([.05,-.01,0,-.01,-1],[.35,.01,.3,.01,1])
 if f=='absyaw':return ([.05,-.01,0,-2,.015,-.01,-1],[.35,.01,.3,2,.4,.01,1])
 if f=='deadwheel':return ([.05,0,.015,.05,-.01,-1],[.35,.1,.4,3,.01,1])
 if f=='smoothwheel':return ([.05,0,.015,.05,.001,-.01,-1],[.35,.1,.4,3,.15,.01,1])
 if f=='smoothyaw':return ([.05,-.01,0,0,.01,-.01,-1],[.35,.01,.3,.1,.5,.01,1])
def sim2(p,f,i):
 g=G[i];v,h,m=cal(p,g[:-1,3],g[:-1,4],f);th=g[0,2]+np.r_[0,np.cumsum(h)];pos=g[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[v*np.cos(th[:-1]+m*h),v*np.sin(th[:-1]+m*h)],axis=0)]);return np.c_[pos,th]
# fit lagged nonlinear map: v=current/previous blended, h same with distinct blend fractions
# used solely to obtain accurate static-map starting values and regularization reference
# 7/5 static params + 2 lag mixture parameters

def refit(f,ids):
 def rr(z):
  p=z[:-2];av,ah=z[-2:];r=[]
  for i in ids:
   s=S[i];v,h,_=cal(p,s['u'],s['w'],f);vp,hp,_=cal(p,s['up'],s['wp'],f);r.extend(((1-av)*v+av*vp-s['v'])[1:]/.003);r.extend(((1-ah)*h+ah*hp-s['h'])[1:]/.02)
  return np.asarray(r)
 lo,hi=bnds(f);lo=np.r_[lo,[0,0]];hi=np.r_[hi,[1,1]]
 z=np.r_[INITS[f],[.28,.7]]
 fit=least_squares(rr,z,bounds=(lo,hi),max_nfev=1200,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 p=fit.x[:-2];p[-1]=.45-fit.x[-1];return p,fit.x[-2:],np.mean(rr(fit.x)**2)
def fit2(f,ids,weight):
 p0,lag,loss=refit(f,ids)
 def rr(p):
  r=[]
  for i in ids:
   g=G[i];ss=sim2(p,f,i);err=ss-g[:,:3];err[:,2]=ss[:,2]-U[i];err[:,2]*=.2;r.extend(err[1:].ravel())
   if weight>0:
    v,h,_=cal(p,g[:-1,3],g[:-1,4],f);v0,h0,_=cal(p0,g[:-1,3],g[:-1,4],f);r.extend(weight*(v-v0)*10);r.extend(weight*(h-h0));
  if weight>0:r.append(weight*.02*(p[-1]-p0[-1]))
  return np.array(r)
 if weight<0:return p0,p0,lag,loss
 fit=least_squares(rr,p0,bounds=bnds(f),max_nfev=1000,ftol=1e-10,xtol=1e-10,gtol=1e-10);return fit.x,p0,lag,loss
R={}
for f in FAMS:
 for weight in [-1,0,2,8]:
  p,p0,lag,loss=fit2(f,[0,1,2],weight);train=[];cv=[];cvp=[]
  for i in range(3):
   ss=sim2(p,f,i);e=ss-G[i][:,:3];e[:,2]=ss[:,2]-U[i];train.append(np.sqrt(np.mean(e[1:]**2,axis=0)).tolist())
   pp,_,_,_=fit2(f,[j for j in range(3) if j!=i],weight);ss=sim2(pp,f,i);e=ss-G[i][:,:3];e[:,2]=ss[:,2]-U[i];cv.append(np.sqrt(np.mean(e[1:]**2,axis=0)).tolist());cvp.append(pp.tolist())
  key=f+'_'+str(weight);R[key]={'p':p.tolist(),'p0':p0.tolist(),'lag':lag.tolist(),'lag_loss':float(loss),'train':train,'cv':cv,'cvp':cvp};print(key,'p',np.round(p,6),'train',np.round(np.array(train)[:,0],4),'cv',np.round(np.array(cv)[:,0],4),'pooled',round(np.sqrt(np.mean(np.array(cv)[:,0]**2)),4),flush=True)
json.dump(R,open('refine_results.json','w'),indent=2)
