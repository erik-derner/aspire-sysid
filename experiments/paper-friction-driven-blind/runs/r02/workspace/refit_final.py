import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
exec(open('fit_rollout.py').read().split('forms=')[0])
orig_train=train.copy();vv=val.copy();vv.trajectory+=100;ALL=pack(pd.concat([train,vv],ignore_index=True))
def force(y,v,u,p,form):
 b,k,c,f,g,s=p[:6]
 if form=='polynomial':return b+k*y+c*v+g*u+p[6]*y**3+p[7]*y**5-f*np.tanh(v/s)
 if form=='statepoly':
  F=b+k*y+c*v+g*u+p[8]*y**3+p[9]*y**5
  ff=f+p[6]*np.sin(y)+p[7]*(np.cos(y)-1)
  return F-ff*np.tanh(v/s)
 if form=='simple':return b+k*np.sin(y)+c*v+g*u-f*np.tanh(v/s)
 F=b+k*np.sin(y)+c*v+g*u+p[8]*(np.cos(y)-1)+p[9]*np.sin(2*y)
 ff=f+p[6]*np.sin(y)+p[7]*(np.cos(y)-1)
 if form=='inputcubic':F+=p[10]*u*np.abs(u)
 if form=='inputdead':F+=p[10]*np.tanh(u/p[11])
 if form=='projection':return F-np.clip(F+v/s,-ff,ff)
 return F-ff*np.tanh(v/s)
R=json.load(open('rollout_results.json'));S=json.load(open('statefriction_results.json'))
forms={'harmonic':S['tanhstateharm']['p'],'projection':S['projstateharm']['p'],'polynomial':R['quintic']['p'],'statepoly':S['tanhstateharm']['p'][:8]+[19,-.7],'simple':R['pendulum']['p'],'inputcubic':S['tanhstateharm']['p']+[0],'inputdead':S['tanhstateharm']['p']+[0,.5]}
results={}
for form,p0 in forms.items():
 lo=[-20,-200,-10,16,0,.007 if form=='projection' else .09];hi=[20,-20,0,50,60,.3 if form=='projection' else 3]
 if form=='polynomial':lo+=[0,-5];hi+=[30,0]
 if form not in ['simple','polynomial']:
  lo+=[-15,-20];hi+=[15,0]
  if form=='statepoly':lo+=[0,-5];hi+=[30,0]
  else:lo+=[-30,-30];hi+=[30,30]
 if form=='inputcubic':lo+=[-5];hi+=[5]
 if form=='inputdead':lo+=[-15,.1];hi+=[15,3]
 t=time.time();opt=least_squares(lambda p:rollout(p,form,ALL),p0,bounds=(lo,hi),x_scale='jac',max_nfev=100,ftol=1e-8,diff_step=1e-4)
 out={'p':opt.x.tolist(),'initial':p0,'bounds':[lo,hi],'nfev':opt.nfev,'success':bool(opt.success),'train':metrics(opt.x,form,TR),'val':metrics(opt.x,form,VA),'seconds':time.time()-t}
 results[form]=out;print(form,out,flush=True);json.dump(results,open('final_results.json','w'),indent=2)
