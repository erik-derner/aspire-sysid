import pandas as pd,numpy as np
from scipy.optimize import least_squares
a=pd.read_csv('helper_transitions.csv');s=a[a.phase>=2].copy();
def evaluate(label,fun,q0,units):
 r=least_squares(lambda q:fun(q,s)-s.r,q0,max_nfev=3000);e=fun(r.x,s)-s.r;print(label,'parameters',r.x,units,'RMSE',np.sqrt(np.mean(e**2)))
 for tr in [1,2,3]:
  z=s[s.tr==tr];rr=least_squares(lambda q:fun(q,z)-z.r,r.x,max_nfev=3000);print('tr',tr,'parameters',rr.x,'RMSE',np.sqrt(np.mean(rr.fun**2)))
evaluate('angular sign intercept',lambda q,z:q[0]*z.w+q[1]*np.sign(z.w)+q[2],[.7,-.05,0],'gain,-rad/s,rad/s')
evaluate('angular deadzone',lambda q,z:q[0]*np.sign(z.w)*np.maximum(abs(z.w)-abs(q[1]),0)+q[2],[.8,.1,0],'gain,rad/s,rad/s')
evaluate('angular deadzone+speed',lambda q,z:(q[0]+q[1]*z.u)*np.sign(z.w)*np.maximum(abs(z.w)-abs(q[2]),0)+q[3],[.8,0,.1,0],'gain,s/m,rad/s,rad/s')
print('per-tr steady forward');
for tr in [1,2,3]:
 z=s[s.tr==tr];X=np.c_[np.ones(len(z)),z.u];q=np.linalg.lstsq(X,z.f,rcond=None)[0]; print(tr,q,'rmse',np.sqrt(np.mean((X@q-z.f)**2)))
# Estimate wheel-coordinate static friction map together from forward and angular velocity. Half track b>0; wheel speeds c = u +/- b*w; map g(c)=gain*sign(c)*max(abs(c)-dead,0).
def wheel(q,z):
 b,g,d=q;L=z.u-b*z.w;R=z.u+b*z.w;ll=g*np.sign(L)*np.maximum(abs(L)-d,0);rr=g*np.sign(R)*np.maximum(abs(R)-d,0);return (rr+ll)/2,(rr-ll)/(2*b)
def resid(q,z):
 f,w=wheel(q,z); return np.r_[(f-z.f)/.01,(w-z.r)/.08]
r=least_squares(lambda q:resid(q,s),[.15,.85,.015],bounds=([.05,.1,0],[.3,1.5,.15]),max_nfev=10000);f,w=wheel(r.x,s);print('wheel deadzone halftrack,gain,threshold',r.x,'forward/angular RMSE',np.sqrt(np.mean((f-s.f)**2)),np.sqrt(np.mean((w-s.r)**2)))
for tar,c in [('f','u'),('r','w')]:
 X=np.c_[np.ones(len(s)),s[c]];q=np.linalg.lstsq(X,s[tar],rcond=None)[0];e=s[tar]-X@q
 print(tar,'residual correlations',[(v,np.corrcoef(e,s[v])[0,1]) for v in ['u','w','k','phi']]); print('trajectory residual means',e.groupby(s.tr).mean().to_dict());
# wheel-specific gains no deadzone, revealing systematic angular attenuation vs translation
print('\nSTEADY ANGULAR residual table mean commands/response (blocks)'); blocks=s.groupby(['tr',(s.k//5).rename('block')]).mean(numeric_only=True).reset_index();print(blocks[['tr','block','u','w','f','r']].to_string(index=False))
