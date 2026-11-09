import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
exec(open('fit_rollout.py').read().split('forms=')[0])
def force(y,v,u,p,form):
 b,k,c,f,g,s,h,j=p[:8]
 F=b+k*np.sin(y)+c*v+g*u
 ff=f+h*np.sin(y)+j*(np.cos(y)-1)
 if form.endswith('harm'): F+=p[8]*(np.cos(y)-1)+p[9]*np.sin(2*y)
 if form.endswith('damp'): F+=p[8]*y*v+p[9]*y*y*v
 if form.endswith('freq'):F=b+k*np.sin(p[8]*y)+c*v+g*u
 if form.startswith('proj'):return F-np.clip(F+v/s,-np.maximum(ff,1),np.maximum(ff,1))
 return F-ff*np.tanh(v/s)
forms={'tanhstate':[2,-110,-1.7,20,28,.15,-7,-6],
'projstate':[2,-110,-1.7,20,28,.012,-7,-6],
'tanhstateharm':[2,-110,-1.7,20,28,.15,-7,-6,0,0],
'projstateharm':[2,-110,-1.7,20,28,.012,-7,-6,0,0],
'tanhstatedamp':[2,-110,-1.7,20,28,.15,-7,-6,0,0],
'tanhstatefreq':[2,-110,-1.7,20,28,.15,-7,-6,1]}
results={}
for form,p0 in forms.items():
 lo=[-20,-200,-10,8,0,.007 if form.startswith('proj') else .09,-7,-15];hi=[20,-20,0,50,60,.3 if form.startswith('proj') else 3,7,0]
 if form.endswith('harm'):lo+=[-30,-30];hi+=[30,30]
 if form.endswith('damp'):lo+=[-1,-2];hi+=[1,0]
 if form.endswith('freq'):lo+=[.7];hi+=[1.3]
 t=time.time();opt=least_squares(lambda p:rollout(p,form,TR),p0,bounds=(lo,hi),x_scale='jac',max_nfev=150,ftol=1e-9,diff_step=1e-4)
 out={'p':opt.x.tolist(),'initial':p0,'bounds':[lo,hi],'nfev':opt.nfev,'success':bool(opt.success),'train':metrics(opt.x,form,TR),'val':metrics(opt.x,form,VA),'seconds':time.time()-t}
 results[form]=out;print(form,out,flush=True);json.dump(results,open('statefriction_results.json','w'),indent=2)
