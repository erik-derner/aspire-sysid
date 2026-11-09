import json,numpy as np
from scipy.optimize import least_squares
import fit_extensions as ext
import fit_tabulated as tab
D=ext.D
# Fit maximum atmospheric relaxation rate instead of independent regularizer.
# This makes the 5 s explicit RK4 zero-flow relaxation stable by construction.
specs={
 'MixedResistance':(1,[.00128,.522,3.35,.40,.5,1.45,.990,1.],[0,1,2,3,5,6]),
 'RegularizedOrifice':(0,[.00132,.185,0.,.40,.5,1.,1.,1.],[0,1,3,5]),
 'GeneralizedDischarge':(0,[.00129,.455,2.90,.40,.50,1.40,.990,1.],[0,1,2,3,4,5,6]),
 'CompressibleDischarge':(2,[.00121,.567,5.66,.40,.5,1.66,.990,1.],[0,1,2,3,5,6])}
lo=np.array([.0001,.01,0.,.03,.3,.5,.98,0.]);hi=np.array([.004,1.,30.,.5,.85,3.,1.02,3.])
def convert(t,fam):
 z=t.copy();full=t[1]/(1+t[2]);rate=t[3]
 if fam==1:z[3]=(full/(2*rate))**2
 elif fam==2:z[3]=(full/rate)**2
 else:z[3]=(full/rate)**(1/(1-t[4]))
 return z

def fit(label,fam,start,idx,names,init=None):
 start=np.array(start);idx=np.array(idx)
 def unpack(w):
  z=start.copy();z[idx]=w;return z
 if init is None:
  def df(w):return np.concatenate([(ext.deriv(convert(unpack(w),fam),D[name],fam)[:-1]-D[name][:-1,3])*100 for name in names])
  ini=least_squares(df,start[idx],bounds=(lo[idx],hi[idx]),x_scale='jac',max_nfev=800,ftol=1e-10,xtol=1e-10,gtol=1e-10).x
 else:ini=np.array(init)[idx]
 def sf(w):return np.concatenate([ext.sim(convert(unpack(w),fam),D[name],fam)[1:]-D[name][1:,0] for name in names])
 opt=least_squares(sf,ini,bounds=(lo[idx],hi[idx]),x_scale='jac',max_nfev=1200,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 t=unpack(opt.x);z=convert(t,fam)
 rec={'fam':fam,'start':start.tolist(),'idx':idx.tolist(),'initial':unpack(ini).tolist(),'params':t.tolist(),'rhs_params':z.tolist(),'data':names,'nfev':opt.nfev,'success':bool(opt.success)}
 for name,d in D.items():
  pred=ext.sim(z,d,fam);r=pred-d[:,0];dr=ext.deriv(z,d,fam)-d[:,3]
  rec[name+'_rmse']=float(np.sqrt(np.mean(r[1:]**2)));rec[name+'_derivative_rmse']=float(np.sqrt(np.mean(dr[:-1]**2)))
  np.savez('results/'+label+'_'+('_'.join(names))+'_'+name+'.npz',pred=pred,res=r,dres=dr)
 print(label,names,t,'s',z[3],'RMSE',rec['train_rmse'],rec['val_rmse'],flush=True)
 return rec

def fit_table(names,initial=None):
 # t=[a,rate,n,pa,d1,...,d6]; pressure scale is a tied value.
 start=np.array([.00126,.40,.51,.99,.016,.02,.02,.023,.022,.017])
 low=np.r_[.0002,.03,.3,.98,np.full(6,.000001)];high=np.r_[.004,.5,.85,1.02,np.full(6,.15)]
 def convert_table(t):
  z=t.copy();z[1]=(sum(t[4:])/t[1])**(1/(1-t[2]));return z
 if initial is None:
  def fd(t):return np.concatenate([(tab.deriv(convert_table(t),D[name])[:-1]-D[name][:-1,3])*100 for name in names])
  ini=least_squares(fd,start,bounds=(low,high),x_scale='jac',max_nfev=800,ftol=1e-10,xtol=1e-10,gtol=1e-10).x
 else:ini=np.array(initial)
 def sf(t):return np.concatenate([tab.sim(convert_table(t),D[name])[1:]-D[name][1:,0] for name in names])
 opt=least_squares(sf,ini,bounds=(low,high),x_scale='jac',max_nfev=1200,ftol=1e-11,xtol=1e-11,gtol=1e-11)
 t=opt.x;z=convert_table(t);rec={'start':start.tolist(),'initial':ini.tolist(),'params':t.tolist(),'rhs_params':z.tolist(),'data':names,'nfev':opt.nfev,'success':bool(opt.success)}
 for name,d in D.items():
  pred=tab.sim(z,d);r=pred-d[:,0];dr=tab.deriv(z,d)-d[:,3]
  rec[name+'_rmse']=float(np.sqrt(np.mean(r[1:]**2)));rec[name+'_derivative_rmse']=float(np.sqrt(np.mean(dr[:-1]**2)))
  np.savez('results/TabulatedValve_'+('_'.join(names))+'_'+name+'.npz',pred=pred,res=r,dres=dr)
 print('TabulatedValve',names,t,'s',z[1],'RMSE',rec['train_rmse'],rec['val_rmse'],flush=True)
 return rec
if __name__=='__main__':
 results={}
 for label,spec in specs.items():
  training=fit(label,*spec,['train'])
  both=fit(label,*spec,['train','val'],init=training['params'])
  results[label]={'selection':training,'final':both};json.dump(results,open('results/final.json','w'),indent=2)
 training=fit_table(['train']);both=fit_table(['train','val'],training['params'])
 results['TabulatedValve']={'selection':training,'final':both};json.dump(results,open('results/final.json','w'),indent=2)
