import numpy as np,pandas as pd,json
from scipy.optimize import least_squares, minimize_scalar
T=pd.read_csv('data/train.csv'); V=pd.read_csv('data/val.csv')
# All input/output columns have unspecified units; time unit seconds.
y,x1,x2,dy=(T[c].to_numpy() for c in ['y','x1','x2','dy'])
results=[]
def design(kind,q,y,x,z):
    if kind=='exp': g=np.exp(np.clip(q[0]*(y-1),-100,100)); return np.array([np.ones_like(y),x,z,g]).T
    if kind=='exp_inter': g=np.exp(np.clip(q[0]*(y-1),-100,100)); return np.array([np.ones_like(y),x,z,x*z,g]).T
    if kind=='exp_y': g=np.exp(np.clip(q[0]*(y-1),-100,100)); return np.array([np.ones_like(y),x,z,y,g]).T
    if kind=='log': g=np.log(y-q[0]); return np.array([np.ones_like(y),x,z,g]).T
    if kind=='sqrt': g=np.sqrt(y-q[0]);return np.array([np.ones_like(y),x,z,g]).T
    if kind=='power':g=(y-q[0])**q[1]; return np.array([np.ones_like(y),x,z,g]).T
    if kind=='rational':g=1/(y-q[0]);return np.array([np.ones_like(y),x,z,g]).T
    if kind=='rational_inter':g=1/(y-q[0]);return np.array([np.ones_like(y),x,z,x*z,g]).T
    if kind=='rational_y':g=1/(y-q[0]);return np.array([np.ones_like(y),x,z,y,g]).T
    if kind=='rational_input':den=y-q[0];return np.array([np.ones_like(y),x/den,z/den,1/den]).T
    if kind=='rational_input2':den=y-q[0];return np.array([np.ones_like(y),x/den,z/den,y,1/den]).T
    if kind=='rational_common':den=1+q[0]*(y-1)+q[1]*(y-1)**2;return np.array([np.ones_like(y),x,z,y,y*y]).T/den[:,None]
    if kind=='exp_common':g=np.exp(np.clip(q[0]*(y-1),-100,100));return np.array([np.ones_like(y),x,z,y,y*y]).T/g[:,None]
    if kind=='input_log':return np.array([np.ones_like(y),np.log(x+q[0]),np.log(z+q[1]),y,y*y]).T
    if kind=='input_sqrt':return np.array([np.ones_like(y),np.sqrt(x+q[0]),np.sqrt(z+q[1]),y,y*y]).T
    if kind=='input_exp':return np.array([np.ones_like(y),np.exp(q[0]*x/100),np.exp(q[1]*z/30),y,y*y]).T
    if kind=='input_rat':return np.array([np.ones_like(y),x/(x+q[0]),z/(z+q[1]),y,y*y]).T
    raise Exception(kind)
def simulate(kind,q,c,df):
    a=df[['y','x1','x2']].to_numpy(); yp=np.empty(len(a));yp[0]=a[0,0]
    def f(v,x,z):return float((design(kind,q,np.array([v]),np.array([x]),np.array([z]))@c)[0])
    with np.errstate(all='ignore'):
      for i in range(len(a)-1):
        u,w=a[i,1:];v=yp[i]; k1=f(v,u,w);k2=f(v+2.5*k1,u,w);k3=f(v+2.5*k2,u,w);k4=f(v+5*k3,u,w);yp[i+1]=v+5*(k1+2*k2+2*k3+k4)/6
        if not np.isfinite(yp[i+1]) or abs(yp[i+1])>100:return np.inf
    return float(np.sqrt(np.mean((yp[1:]-a[1:,0])**2)))
def fit(kind,initial,bounds):
 def res(q):
  A=design(kind,q,y,x1,x2);c=np.linalg.lstsq(A,dy,rcond=None)[0];return A@c-dy
 best=None
 for start in initial:
  opt=least_squares(res,start,bounds=bounds,max_nfev=400,ftol=1e-11,xtol=1e-11,gtol=1e-11)
  if best is None or np.linalg.norm(opt.fun)<np.linalg.norm(best.fun):best=opt
 q=best.x;A=design(kind,q,y,x1,x2);c=np.linalg.lstsq(A,dy,rcond=None)[0]
 Av=design(kind,q,*[V[t].to_numpy() for t in ['y','x1','x2']])
 r={'kind':kind,'q':q.tolist(),'c':c.tolist(),'deriv_train':float(np.sqrt(np.mean((A@c-dy)**2))),'deriv_val':float(np.sqrt(np.mean((Av@c-V.dy.to_numpy())**2))),'rk_train':simulate(kind,q,c,T),'rk_val':simulate(kind,q,c,V)}
 results.append(r);print(json.dumps(r),flush=True)
if __name__=='__main__':
 for kind in ['exp','exp_inter','exp_y','exp_common']:fit(kind,[[-5],[-1],[1],[4],[10]],([-20],[20]))
 for kind in ['log','sqrt','rational','rational_inter','rational_y','rational_input','rational_input2']:fit(kind,[[-4],[0],[0.8],[0.98]],([-100],[0.99]))
 fit('power',[[0,2],[0.9,0.5],[0.98,0.1],[0.8,-1]],([-20,-5],[0.99,8]))
 fit('rational_common',[[0,0],[1,1],[-1,1]],([-1.5,0],[20,20]))
 for kind in ['input_log','input_sqrt','input_rat']:fit(kind,[[1,1],[10,10],[100,100]],([0.001,0.001],[10000,10000]))
 fit('input_exp',[[-1,-1],[1,1],[4,4]],([-20,-20],[20,20]))
 json.dump(results,open('helper_nonlinear_results.json','w'),indent=2)
