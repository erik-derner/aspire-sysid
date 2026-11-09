import helper_nonlinear as h
import numpy as np,json
orig=h.design
def design(kind,q,y,x,z):
 if kind.startswith('int_'):
  k=kind[4:]
  if k=='exp':w=np.exp(np.clip(q[0]*(y-1),-100,100))
  elif k=='log':w=np.log(np.maximum(y-q[0],1e-12))
  elif k=='sqrt':w=np.sqrt(np.maximum(y-q[0],1e-12))
  elif k=='recip':w=1/(y-q[0])
  elif k=='power':w=np.maximum(y-q[0],1e-12)**q[1]
  return np.array([np.ones_like(y),x,z,w,x*w,z*w,x*z]).T
 if kind=='int_expinput':
  w=np.exp(np.clip(q[2]*(y-1),-100,100));u=np.exp(np.clip(q[0]*x/100,-100,100));v=np.exp(np.clip(q[1]*z/30,-100,100));return np.array([np.ones_like(y),u,v,w,u*w,v*w,u*v]).T
 if kind=='int_recipinput':
  w=1/(y-q[2]);u=np.exp(np.clip(q[0]*x/100,-100,100));v=np.exp(np.clip(q[1]*z/30,-100,100));return np.array([np.ones_like(y),u,v,w,u*w,v*w,u*v]).T
 if kind=='int_sqrtinput':
  w=np.sqrt(np.maximum(y-q[2],1e-12));u=np.exp(np.clip(q[0]*x/100,-100,100));v=np.exp(np.clip(q[1]*z/30,-100,100));return np.array([np.ones_like(y),u,v,w,u*w,v*w,u*v]).T
 if kind=='int_loginput':
  w=np.log(np.maximum(y-q[2],1e-12));u=np.exp(np.clip(q[0]*x/100,-100,100));v=np.exp(np.clip(q[1]*z/30,-100,100));return np.array([np.ones_like(y),u,v,w,u*w,v*w,u*v]).T
 return orig(kind,q,y,x,z)
h.design=design
if __name__=='__main__':
 h.fit('int_exp',[[-5],[-1],[1]],([-20],[20]))
 for k in ['sqrt','log','recip']:h.fit('int_'+k,[[0.8],[0],[0.98]],([-20],[0.99]))
 h.fit('int_power',[[0.9,0.5],[0.5,-1],[0.8,2]],([-20,-5],[0.99,8]))
 h.fit('int_expinput',[[2,1,-2],[7,1,-5]],([0.01,0.01,-20],[20,20,20]))
 for k in ['recip','sqrt','log']:h.fit('int_'+k+'input',[[3,1,0.8],[7,1,0.98]],([0.01,0.01,-20],[20,20,0.99]))
 json.dump(h.results,open('helper_interaction_results.json','w'),indent=2)
