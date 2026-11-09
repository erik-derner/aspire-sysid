exec(open('helper_nonlinear.py').read().split('# Positive shifts')[0])
fits={}
def do(name,f,p,b,desc):
 out=vp(name,f,p,b,desc);fits[name]=out
 return out
base=do('power_product_unbounded',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],u**p[2]*w**p[3],w**p[4]]).T,[.9848,.334,5,.554,.918],([-2,.02,.05,-2,.05],[.9922,5,20,5,5]),'c0+c1*(y-p0)**p1+c2*u**p2*w**p3+c3*w**p4')
do('exp_product',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],np.exp(p[2]*(u-1))*w**p[3],w**p[4]]).T,[.98,.4,6,.5,1],([-2,.02,.05,-2,.05],[.9922,5,20,5,5]),'c0+c1*(y-p0)**p1+c2*exp(p2*(u-1))*w**p3+c3*w**p4')
do('exp_extended',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],np.exp(p[2]*(u-1)),w**p[3],np.exp(p[2]*(u-1))*w**p[3]]).T,[.98,.4,6,.7],([-2,.02,.05,.05],[.9922,5,20,5]),'c0+c1*(y-p0)**p1+c2*exp(p2*(u-1))+c3*w**p3+c4*exp(p2*(u-1))*w**p3')
do('exp_additive',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],np.exp(p[2]*(u-1)),w**p[3]]).T,[.99,.2,6,.6],([-2,.02,.05,.05],[.9922,5,20,5]),'c0+c1*(y-p0)**p1+c2*exp(p2*(u-1))+c3*w**p3')
do('power_equilibrium_relaxation',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],u**p[2]*w**p[3],w**p[4]]).T/(y[:,None]-p[0])**p[5],[.98,.6,6,.5,1,.1],([-2,.02,.05,-2,.05,-3],[.9922,5,20,5,5,3]),'(c0+c1*(y-p0)**p1+c2*u**p2*w**p3+c3*w**p4)/(y-p0)**p5')
do('exp_equilibrium_relaxation',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],np.exp(p[2]*(u-1))*w**p[3],w**p[4]]).T/(y[:,None]-p[0])**p[5],[.98,.6,6,.5,1,.1],([-2,.02,.05,-2,.05,-3],[.9922,5,20,5,5,3]),'(c0+c1*(y-p0)**p1+c2*exp(p2*(u-1))*w**p3+c3*w**p4)/(y-p0)**p5')
do('power_product_state_cross',lambda p,y,u,w:np.array([np.ones_like(y),(y-p[0])**p[1],u**p[2]*w**p[3],w**p[4],u**p[2]*w**p[3]*(y-p[0])**p[1],w**p[4]*(y-p[0])**p[1]]).T,[.9848,.334,5,.554,.918],([-2,.02,.05,-2,.05],[.9922,5,20,5,5]),'c0+c1*z+c2*v+c3*h+c4*v*z+c5*h*z; z=(y-p0)**p1,v=u**p2*w**p3,h=w**p4')
# Smooth floor suppresses strong unconstrained power derivatives near baseline.
do('exp_logstate',lambda p,y,u,w:np.array([np.ones_like(y),np.log(y-p[0]),np.exp(p[1]*(u-1))*w**p[2],w**p[3]]).T,[.96,6,.5,1],([-2,.05,-2,.05],[.9922,20,5,5]),'c0+c1*log(y-p0)+c2*exp(p1*(u-1))*w**p2+c3*w**p3')
json.dump(sorted(results,key=lambda r:r['val_rmse']),open('helper_refine_results.json','w'),indent=2)
for name,(p,c,f) in fits.items():
 for tag,d in [('train',A),('val',V)]:
  y,u,w=unpack(d);r=d.dy-f(p,y,u,w)@c
  bins={}
  for col in ['y','x1','x2']:
   groups=pd.qcut(d[col],5,duplicates='drop');bins[col]=pd.DataFrame({'r':r,'g':groups},).groupby('g',observed=True)['r'].agg(['mean','std','size']).to_string()
  print('RESIDUAL',name,tag,json.dumps(bins),flush=True)
