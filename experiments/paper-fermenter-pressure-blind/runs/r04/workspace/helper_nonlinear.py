import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
A=pd.read_csv('data/train.csv');V=pd.read_csv('data/val.csv');
def unpack(d):return d.y.to_numpy(),d.x1.to_numpy()/70,d.x2.to_numpy()/20
Y,U,W=unpack(A);t=A.dy.to_numpy();yv,uv,wv=unpack(V);tv=V.dy.to_numpy()
results=[]
def fit_linear(name,feat,descr):
 F=feat(Y,U,W);c=np.linalg.lstsq(F,t,rcond=None)[0]; pred=F@c;pv=feat(yv,uv,wv)@c
 record(name,c,[],pred,pv,descr)
def record(name,c,p,pred,pv,descr):
 r=t-pred;rv=tv-pv
 item=dict(name=name,coefficients=list(c),nonlinear_parameters=list(p),description=descr,train_rmse=float(np.sqrt(np.mean(r*r))),val_rmse=float(np.sqrt(np.mean(rv*rv))),train_bias=float(np.mean(r)),val_bias=float(np.mean(rv)),val_corr={col:float(np.corrcoef(rv,V[col])[0,1]) for col in ['y','x1','x2']})
 results.append(item);print(json.dumps(item),flush=True)
 return item
fit_linear('linear',lambda y,u,w:np.array([np.ones_like(y),y,u,w]).T,'c0+c1*y+c2*x1/70+c3*x2/20')
fit_linear('tank_offset',lambda y,u,w:np.array([np.ones_like(y),np.sqrt(np.maximum(y-0.99,0)),u,w,u*w]).T,'c0+c1*sqrt(max(y-.99,0))+c2*u+c3*w+c4*u*w')
fit_linear('input_products',lambda y,u,w:np.array([np.ones_like(y),y,u,w,u*w,u*np.sqrt(w),u*w*w]).T,'linear state with input products')

def vp(name,feature,p0,bounds,descr):
 def get(p,y,u,w,target=None):
  F=feature(p,y,u,w)
  c=np.linalg.lstsq(F,t if target is None else target,rcond=None)[0]
  return F,c
 def res(p):
  F,c=get(p,Y,U,W);return (F@c-t)/.006
 best=None
 starts=[p0]
 for pp in starts:
  opt=least_squares(res,pp,bounds=bounds,max_nfev=1800,ftol=1e-11,xtol=1e-11,gtol=1e-11)
  if best is None or np.sum(opt.fun**2)<np.sum(best.fun**2):best=opt
 F,c=get(best.x,Y,U,W);pv=feature(best.x,yv,uv,wv)@c
 record(name,c,best.x,F@c,pv,descr)
 return best.x,c,feature
# Positive shifts guarantee real powers at observed states; offsets fitted at/below observed min.
vp('power_additive',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],u**p[2],w**p[3]]).T,[.98,.5,1,1],([-5,.05,.05,.05],[.9922,5,5,5]),'c0+c1*(y-p0)**p1+c2*u**p2+c3*w**p3')
vp('power_input_product',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],u**p[2]*w**p[3],w**p[4]]).T,[.98,.5,1,1,1],([-5,.05,.05,.05,.05],[.9922,5,5,5,5]),'c0+c1*(y-p0)**p1+c2*u**p2*w**p3+c3*w**p4')
vp('power_extended',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],u**p[2],w**p[3],u**p[2]*w**p[3]]).T,[.98,.5,1,1],([-5,.05,.05,.05],[.9922,5,5,5]),'c0+c1*(y-p0)**p1+c2*u**p2+c3*w**p3+c4*u**p2*w**p3')
vp('rational_linear',lambda p,y,u,w:np.array([np.ones_like(y),y,u,w,u*w]).T/(1+p[0]*y[:,None]+p[1]*u[:,None]+p[2]*w[:,None]),[0,0,0],([0,0,0],[20,20,20]),'(c0+c1*y+c2*u+c3*w+c4*u*w)/(1+p0*y+p1*u+p2*w)')
vp('power_denominator',lambda p,y,u,w:np.array([np.ones_like(y),y,u,w,u*w]).T/(y[:,None]-p[0])**p[1],[.5,1],([-5,-3],[.9922,3]),'(c0+c1*y+c2*u+c3*w+c4*u*w)/(y-p0)**p1')
vp('tank_valve',lambda p,y,u,w:np.array([np.ones_like(y),u**p[0],w**p[1]*np.maximum(y-p[2],1e-12)**p[3]]).T,[1,1,.98,.5],([.05,.05,-5,.05],[5,5,.9922,5]),'c0+c1*u**p0+c2*w**p1*(y-p2)**p3')
vp('tank_twoflows',lambda p,y,u,w:np.array([np.ones_like(y),u**p[0]*(y-p[2])**p[3],w**p[1]*(y-p[2])**p[4]]).T,[1,1,.98,.5,.5],([.05,.05,-5,-3,-3],[5,5,.9922,5,5]),'c0+c1*u**p0*(y-p2)**p3+c2*w**p1*(y-p2)**p4')
vp('sigmoid_inputs',lambda p,y,u,w:np.array([np.ones_like(y),y,np.tanh(p[0]*(u-p[1])),np.tanh(p[2]*(w-p[3]))]).T,[2,.7,2,.8],([.01,-2,.01,-2],[20,3,20,3]),'c0+c1*y+c2*tanh(p0*(u-p1))+c3*tanh(p2*(w-p3))')
# residual dependence of most competitive model by binned state/input
best=sorted(results,key=lambda r:r['val_rmse']);json.dump(best,open('helper_nonlinear_results.json','w'),indent=2)
print('sorted',[(i['name'],i['train_rmse'],i['val_rmse']) for i in best])
# Exact derivative alignment check
print('derivative_forward_consistency',np.sqrt(np.mean(((A.y.to_numpy()[1:]-A.y.to_numpy()[:-1])/5-A.dy.to_numpy()[:-1])**2)))
