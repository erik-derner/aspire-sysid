"""Reproduce final joint parameter-estimation step; rerun deliver_models.py to write models."""
import json
import numpy as np
from scipy.optimize import least_squares
from fit_final import fit_one,fsim,A,L,M,Av,Lv,Mv
from fit_quintic import qsim
FR=json.load(open('final_results.json'));QR=json.load(open('quintic_results.json'))
for name,r,f in [('trig_exponential',FR['trig_exponential'],0),('static_blend',FR['static_blend'],3),('quintic',QR,-1)]:
 initial=np.array(r['train_p']);active=np.array(r['active']);lo,hi=np.array(r['bounds'])
 if f>=0:pp,opt=fit_one(initial,f,active,lo,hi,True)
 else:
  def unpack(z):p=initial.copy();p[active]=z;return p
  def fun(z):
   p=unpack(z)
   return np.r_[(qsim(p,A,L)[:,:,0]-A[:,:,0])[M],(qsim(p,Av,Lv)[:,:,0]-Av[:,:,0])[Mv]]
  opt=least_squares(fun,initial[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=350,ftol=1e-10,xtol=1e-10,gtol=1e-10)
  pp=unpack(opt.x)
 print(name,'parameters',pp,'maximum saved-fit deviation',np.max(np.abs(pp-np.array(r['p']))))
 assert np.allclose(pp,np.array(r['p']),rtol=1e-7,atol=1e-7)
