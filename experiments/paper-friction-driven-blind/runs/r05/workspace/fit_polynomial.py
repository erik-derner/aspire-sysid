import fit_models as f,numpy as np,json
from scipy.optimize import least_squares

def accel(y,v,u,p,fam):
 b,a,d,k,F,w,c,h,fp,fq,q=p
 rest=y+c*y**3+(c*c/4+q*q)*y**5
 drive=b+a*u-k*rest+h*y*y
 fr=(F+fp*y+fq*y*y)*np.tanh(v/w)
 return drive-d*v-fr
f.accel=accel
p=np.array([3,28,1.6,112,20,.15,-.17,-2,-5,4,.04]);lo=np.array([-20,5,.2,50,10,.12,-.3,-10,-10,0,.001]);hi=np.array([20,60,5,180,35,3,-.05,10,10,10,.2])
if __name__=='__main__':
 r=least_squares(lambda p:f.simulate(p,'polynomial','train'),p,bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=180,ftol=1e-7,xtol=1e-7,gtol=1e-6)
 z={'family':'polynomial','p':r.x.tolist(),'start':p.tolist(),'bounds':[lo.tolist(),hi.tolist()],'train_rmse':float(np.sqrt(np.mean(r.fun*r.fun))),'val_rmse':float(np.sqrt(np.mean(f.simulate(r.x,'polynomial','val')**2))),'nfev':r.nfev,'status':r.message}
 print(json.dumps(z));json.dump(z,open('results/polynomial.json','w'),indent=2)
