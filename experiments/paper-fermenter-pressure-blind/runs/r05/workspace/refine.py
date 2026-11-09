import numpy as np,pandas as pd,json,time
from scipy.optimize import least_squares
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv')
# Internal numerical variables z=y-1,u=x1/60,v=x2/20.
class PolyModel:
 def __init__(self,p):self.p=np.array(p);self.m=len(p);self.kind='poly'
 def fg(self,z,u,v,c):
  X=np.prod(np.array([z,u,v])**self.p,axis=1);F=X@c
  p=self.p[:,0];active=p>0
  Y=np.prod(np.array([z,u,v])**(self.p[active]-[1,0,0]),axis=1)
  return F,np.dot(c[active]*p[active],Y),X
class StableModel:
 def __init__(self):self.m=9;self.kind='stable'
 def fg(self,z,u,v,c):
  # c0+c1*u+c2*u^2+c3*u^3+c4*v+c5*v^2 - (c6+c7*u)^2*z-c8*z^2
  q=c[6]+c[7]*u
  X=np.array([1,u,u*u,u**3,v,v*v,-2*q*z,-2*q*u*z,-z*z]);
  return np.dot(c[:6],X[:6])-q*q*z-c[8]*z*z,-q*q-2*c[8]*z,X
class RationalModel:
 def __init__(self,p):self.p=np.array(p);self.num=PolyModel(p);self.m=len(p)+1;self.kind='rational'
 def fg(self,z,u,v,c):
  F,Fz,G=self.num.fg(z,u,v,c[:-1]);den=1+c[-1]*z*z
  return F/den,Fz/den-F*2*c[-1]*z/(den*den),np.r_[G/den,-F*z*z/(den*den)]
def rollout(model,c,d,sens=False):
 n=len(d);ys=np.empty(n);ys[0]=d.y.iloc[0]-1
 if sens:js=np.zeros((n,model.m))
 u=d.x1.values/60;v=d.x2.values/20
 for i in range(n-1):
  z=ys[i]
  if sens:
   J=js[i]
   a,az,ap=model.fg(z,u[i],v[i],c);ja=az*J+ap
   b,bz,bp=model.fg(z+2.5*a,u[i],v[i],c);jb=bz*(J+2.5*ja)+bp
   cc,cz,cp=model.fg(z+2.5*b,u[i],v[i],c);jc=cz*(J+2.5*jb)+cp
   e,ez,ep=model.fg(z+5*cc,u[i],v[i],c);je=ez*(J+5*jc)+ep
   js[i+1]=J+5*(ja+2*jb+2*jc+je)/6
  else:
   a=model.fg(z,u[i],v[i],c)[0];b=model.fg(z+2.5*a,u[i],v[i],c)[0];cc=model.fg(z+2.5*b,u[i],v[i],c)[0];e=model.fg(z+5*cc,u[i],v[i],c)[0]
  ys[i+1]=z+5*(a+2*b+2*cc+e)/6
  if not np.isfinite(ys[i+1]) or abs(ys[i+1])>100:
   return (np.full(n,1000),np.zeros((n,model.m))) if sens else np.full(n,1000)
 return (ys+1,js) if sens else ys+1
class Objective:
 def __init__(self,model,ds,scale,anchor=None,reg=0):self.model=model;self.ds=ds;self.scale=scale;self.anchor=anchor;self.reg=reg;self.last=None
 def compute(self,t):
  if self.last is None or not np.array_equal(self.last,t):
   pairs=[rollout(self.model,t*self.scale,d,True) for d in self.ds]
   self.err=np.concatenate([y[1:]-d.y.values[1:] for (y,j),d in zip(pairs,self.ds)])
   self.jacobian=np.vstack([j[1:]*self.scale for y,j in pairs])
   if self.reg>0:
    self.err=np.r_[self.err,np.sqrt(self.reg)*(t-self.anchor/self.scale)];self.jacobian=np.vstack([self.jacobian,np.sqrt(self.reg)*np.eye(len(t))])
   self.last=t.copy()
  return self.err,self.jacobian
 def fun(self,t):return self.compute(t)[0]
 def jac(self,t):return self.compute(t)[1]
def refine(model,c,ds,maxn=80,reg=0,bounds=None):
 scale=np.maximum(abs(c),.01);obj=Objective(model,ds,scale,c,reg)
 bounds=(-np.inf,np.inf) if bounds is None else (np.array(bounds[0])/scale,np.array(bounds[1])/scale)
 opt=least_squares(obj.fun,c/scale,jac=obj.jac,bounds=bounds,x_scale='jac',max_nfev=maxn,ftol=1e-8,xtol=1e-8,gtol=1e-8)
 return opt.x*scale,opt
if __name__=='__main__':
 res=[];polys=json.load(open('poly_results.json')); structs=json.load(open('structured_results.json'))
 specs=[]
 for deg in [2,3]:
  r=next(r for r in polys if r['deg']==deg and r['reg']==0)
  specs.append(('poly'+str(deg),PolyModel(r['powers']),np.array(r['coef']),None))
 for label in ['bilinear','damping2','damping3','mixedforcing']:
  r=next(r for r in structs if r['label']==label);specs.append((label,PolyModel(r['powers']),np.array(r['coef']),None))
 stable=StableModel();start=np.array([.004,-.02,.01,.001,.005,.005,.40,-.15,.00]);
 # derivative nonlinear LS supplies starting values for stable family
 opt=least_squares(lambda c:np.array([stable.fg(y-1,u/60,v/20,c)[0] for y,u,v in tr[['y','x1','x2']].values])-tr.dy.values,start,max_nfev=1000)
 specs.append(('stable',stable,opt.x,(np.r_[np.full(8,-np.inf),0],np.full(9,np.inf))))
 r=next(r for r in polys if r['deg']==2 and r['reg']==0)
 specs.append(('rational2',RationalModel(r['powers']),np.r_[r['coef'],0],(np.r_[np.full(len(r['coef']),-np.inf),0],np.full(len(r['coef'])+1,np.inf))))
 for label,model,start,bounds in specs:
  begin=time.time();c,opt=refine(model,start,[tr],maxn=100,bounds=bounds)
  score=[np.sqrt(np.mean((rollout(model,c,d)[1:]-d.y.values[1:])**2)) for d in [tr,va]]
  der=[np.sqrt(np.mean((np.array([model.fg(y-1,u/60,v/20,c)[0] for y,u,v in d[['y','x1','x2']].values])-d.dy.values)**2)) for d in [tr,va]]
  print(label,'elapsed',time.time()-begin,'eval',opt.nfev,'roll',score,'der',der, 'coef',c,flush=True)
  res.append(dict(label=label,kind=model.kind,powers=model.p.tolist() if hasattr(model,'p') else None,start=start.tolist(),coef=c.tolist(),roll=score,der=der,nfev=opt.nfev))
  json.dump(res,open('refine_results.json','w'),indent=2)
