import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
train=pd.read_csv('data/train.csv');val=pd.read_csv('data/val.csv')
def pack(d):
 gs=list(d.groupby('trajectory',sort=False));n=max(len(g) for _,g in gs);m=len(gs)
 Y=np.zeros((n,m));V=Y.copy();U=Y.copy();mask=np.zeros((n,m),bool)
 for j,(k,g) in enumerate(gs):
  l=len(g);Y[:l,j]=g.y;V[:l,j]=g.x1;U[:l,j]=g.x2;mask[1:l,j]=True
 return Y,V,U,mask,[int(k) for k,g in gs]
TR=pack(train);VA=pack(val)
def force(y,v,u,p,form):
 b,k,c,f,g,s=p[:6]
 restoring=k*np.sin(y) if form not in ['duffing','quintic','linear'] else k*y
 F=b+restoring+c*v+g*u
 if form=='duffing':F+=p[6]*y**3
 if form=='quintic':F+=p[6]*y**3+p[7]*y**5
 if form=='linear':return F
 friction=f*np.tanh(v/s)
 if form=='harmonic':F+=p[6]*(np.cos(y)-1)+p[7]*np.sin(2*y)
 if form=='drag':F+=p[6]*v*np.abs(v)
 if form=='asym':friction+=p[6]*np.tanh(v/s)**2;F+=p[7]*v*np.tanh(v/s)
 if form=='stribeck':friction+=p[6]*np.exp(-(v/p[7])**2)*np.tanh(v/s)
 if form=='positiondamp':F+=p[6]*y*y*v
 if form=='stiction':
  # activation by speed; static branch removes forces below breakaway magnitude.
  w=np.exp(-(v/p[6])**2)
  drive=b+restoring+g*u
  stat=np.sign(drive)*np.maximum(np.abs(drive)-p[7],0)+c*v
  return (1-w)*(F-friction)+w*stat
 return F-friction

def rollout(p,form,D,full=False):
 Y,V,U,mask,ids=D;y=Y[0].copy();v=V[0].copy();py=np.zeros_like(Y);pv=np.zeros_like(Y);py[0]=y;pv[0]=v
 with np.errstate(over='ignore',invalid='ignore'):
  for i in range(len(Y)-1):
   u=U[i];a1=force(y,v,u,p,form);y2=y+.005*v;v2=v+.005*a1;a2=force(y2,v2,u,p,form);y3=y+.005*v2;v3=v+.005*a2;a3=force(y3,v3,u,p,form);y4=y+.01*v3;v4=v+.01*a3;a4=force(y4,v4,u,p,form)
   y+=.01*(v+2*v2+2*v3+v4)/6;v+=.01*(a1+2*a2+2*a3+a4)/6
   py[i+1]=y;pv[i+1]=v
   if not np.all(np.isfinite(y)) or np.max(np.abs(y))>1000:return np.ones(np.sum(mask))*1e3
 if full:return py,pv
 return (py-Y)[mask]

def metrics(p,form,D):
 e=rollout(p,form,D);Y,V,U,M,ids=D
 py,pv=rollout(p,form,D,True)
 return {'rmse':float(np.sqrt(np.mean(e*e))),'bytraj':{str(k):float(np.sqrt(np.mean((py[:,j]-Y[:,j])[M[:,j]]**2))) for j,k in enumerate(ids)}}
forms={'pendulum':[1.75,-105.58,-1.54,19.27,26.4,.327],
'duffing':[1.65,-102,-1.87,18,26.5,.327,13.0],
'quintic':[1.65,-105,-1.87,18,26.5,.327,17.5,-.87],
'harmonic':[1.75,-105.58,-1.54,19.27,26.4,.327,0,0],
'drag':[1.75,-105.58,-1.54,19.27,26.4,.327,0],
'asym':[1.75,-105.58,-1.54,19.27,26.4,.327,0,0],
'positiondamp':[1.75,-105.58,-1.54,19.27,26.4,.327,0],
'stribeck':[1.75,-105.58,-1.54,19.27,26.4,.327,0,1.0],
'stiction':[1.75,-105.58,-1.54,19.27,26.4,.327,.3,20],
'linear':[1.44,-66.52,-3.86,0,24.84,1]}
results={}
for form,p0 in forms.items():
 lo=[-20,-200,-15,0,0,.09];hi=[20,-20,0,50,60,3]
 if form=='duffing':lo+=[0];hi+=[30]
 if form=='quintic':lo+=[0,-5];hi+=[30,0]
 if form=='harmonic':lo+=[-40,-40];hi+=[40,40]
 if form in ['drag','positiondamp']:lo+=[-2];hi+=[1]
 if form=='asym':lo+=[-15,-3];hi+=[15,3]
 if form=='stribeck':lo+=[-20,.1];hi+=[20,8]
 if form=='stiction':lo+=[.05,5];hi+=[2,50]
 if form=='linear':lo=[-20,-200,-15,-1,0,.09];hi=[20,-20,0,1,60,3]
 t=time.time();opt=least_squares(lambda p:rollout(p,form,TR),p0,bounds=(lo,hi),x_scale='jac',max_nfev=120,ftol=1e-8,diff_step=1e-4)
 out={'p':opt.x.tolist(),'initial':p0,'bounds':[lo,hi],'nfev':opt.nfev,'success':bool(opt.success),'train':metrics(opt.x,form,TR),'val':metrics(opt.x,form,VA),'seconds':time.time()-t}
 results[form]=out
 print(form,out,flush=True)
 json.dump(results,open('rollout_results.json','w'),indent=2)
if __name__=='__main__':pass
