import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
# Reuse only definitions, not the fitting loop.
exec(open('fit_rollout.py').read().split('forms=')[0])
oldforce=force

def force(y,v,u,p,form):
 if not form.startswith('proj'):return oldforce(y,v,u,p,form)
 b,k,c,f,g,t=p[:6]
 F=b+k*np.sin(y)+c*v+g*u
 if form=='projharm':F+=p[6]*(np.cos(y)-1)+p[7]*np.sin(2*y)
 if form=='projduff':F=b+k*y+c*v+g*u+p[6]*y**3
 if form=='projquint':F=b+k*y+c*v+g*u+p[6]*y**3+p[7]*y**5
 if form=='projpos':F+=p[6]*y*y*v
 if form=='projfreq':F=b+k*np.sin(p[6]*y)+c*v+g*u
 if form=='projinput':F+=p[6]*u*np.abs(u)
 if form=='projasym':
  return F-np.clip(F+v/t,-f+p[6],f+p[6])
 return F-np.clip(F+v/t,-f,f)

forms={'proj':[1.98,-110.5,-1.73,20.46,28.1,.012],
'projharm':[3.15,-105.59,-1.53,21.37,27.28,.012,4.11,-5.97],
'projduff':[1.57,-111.44,-1.73,20.59,28.55,.012,15.26],
'projquint':[1.29,-114.48,-1.68,20.67,27.93,.012,19.58,-.69],
'projpos':[1.69,-111.71,-1.44,20.88,28.3,.012,-.38],
'projfreq':[1.98,-110.5,-1.73,20.46,28.1,.012,1],
'projinput':[1.98,-110.5,-1.73,20.46,28.1,.012,0],
'projasym':[1.98,-110.5,-1.73,20.46,28.1,.012,0]}
results={}
for form,p0 in forms.items():
 lo=[-20,-200,-15,5,0,.007];hi=[20,-20,0,50,60,.3]
 if form=='projharm':lo+=[-40,-40];hi+=[40,40]
 if form=='projduff':lo+=[0];hi+=[30]
 if form=='projquint':lo+=[0,-5];hi+=[30,0]
 if form=='projpos':lo+=[-2];hi+=[0]
 if form=='projfreq':lo+=[.7];hi+=[1.3]
 if form=='projinput':lo+=[-5];hi+=[5]
 if form=='projasym':lo+=[-10];hi+=[10]
 t=time.time();opt=least_squares(lambda p:rollout(p,form,TR),p0,bounds=(lo,hi),x_scale='jac',max_nfev=120,ftol=1e-9,diff_step=1e-4)
 out={'p':opt.x.tolist(),'initial':p0,'bounds':[lo,hi],'nfev':opt.nfev,'success':bool(opt.success),'train':metrics(opt.x,form,TR),'val':metrics(opt.x,form,VA),'seconds':time.time()-t}
 results[form]=out;print(form,out,flush=True);json.dump(results,open('projection_results.json','w'),indent=2)
