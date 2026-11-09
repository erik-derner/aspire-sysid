import helper_nonlinear as h
import numpy as np,json
from scipy.optimize import least_squares
orig=h.design
# q input exponential rates on unscaled variables then offset or exponent

def design(kind,q,y,x,z):
 if kind.startswith('adv_'):
  k=kind[4:];u=np.exp(np.clip(q[0]*x/100,-100,100));v=np.exp(np.clip(q[1]*z/30,-100,100))
  if k=='exp':w=np.exp(np.clip(q[2]*(y-1),-100,100))
  elif k=='sqrt':w=np.sqrt(np.maximum(y-q[2],1e-12))
  elif k=='log':w=np.log(np.maximum(y-q[2],1e-12))
  elif k=='recip':w=1/(y-q[2])
  elif k=='power':w=np.maximum(y-q[2],1e-12)**q[3]
  elif k=='exp_y':w=np.exp(np.clip(q[2]*(y-1),-100,100));return np.array([np.ones_like(y),u,v,y,w]).T
  elif k=='cross':w=np.exp(np.clip(q[2]*(y-1),-100,100));return np.array([np.ones_like(y),u,v,u*v,w]).T
  elif k=='multiply':w=np.exp(np.clip(q[2]*(y-1),-100,100));return np.array([np.ones_like(y),u,v,u*w,v*w,w]).T
  else:raise Exception(k)
  return np.array([np.ones_like(y),u,v,w]).T
 if kind.startswith('cvx_'):
  k=kind[4:]
  if k=='rat':u=1/(q[0]-x);v=1/(q[1]-z)
  elif k=='log':u=-np.log(q[0]-x);v=-np.log(q[1]-z)
  elif k=='sqrt':u=-np.sqrt(q[0]-x);v=-np.sqrt(q[1]-z)
  w=1/(y-q[2]);return np.array([np.ones_like(y),u,v,w]).T
 if kind=='exp_polystate':
  u=np.exp(np.clip(q[0]*x/100,-100,100));v=np.exp(np.clip(q[1]*z/30,-100,100));return np.array([np.ones_like(y),u,v,y,y*y,y**3]).T
 return orig(kind,q,y,x,z)
h.design=design
if __name__=='__main__':
 for k in ['exp','exp_y','cross','multiply']:h.fit('adv_'+k,[[8,1,-5],[5,2,-1],[8,1,2]],([0.01,0.01,-20],[20,20,20]))
 for k in ['sqrt','log','recip']:h.fit('adv_'+k,[[8,1,0.8],[5,2,0.5],[8,1,0.98]],([0.01,0.01,-20],[20,20,0.99]))
 h.fit('adv_power',[[8,1,0.8,0.5],[8,1,0.8,-1]],([0.01,0.01,-20,-5],[20,20,0.99,8]))
 for k in ['rat','log','sqrt']:h.fit('cvx_'+k,[[110,40,0.8],[150,60,0.5],[100,35,0.98]],([95,31,0],[10000,10000,0.99]))
 h.fit('exp_polystate',[[8,1],[4,2]],([0.01,0.01],[20,20]))
 json.dump(h.results,open('helper_advanced_results.json','w'),indent=2)
