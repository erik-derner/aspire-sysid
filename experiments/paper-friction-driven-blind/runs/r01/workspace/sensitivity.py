from fit_models import *
from fit_extended import exsim,exmet,exacc
R=json.load(open('fit_results.json'))
print('WIDTH AND WEIGHT SENSITIVITY')
results={}
for name in ['sine_friction','cubic_friction','state_friction']:
 r=R[name];f=r['family'];p=np.array(r['p']);lo=np.array(r['bounds'][0]);hi=np.array(r['bounds'][1])
 for width in [.09,.12,.2,.4]:
  q=p.copy();q[6]=width;active=np.array([i for i in range(len(p)) if i!=6]);init=q.copy()
  def unpack(z):q=init.copy();q[active]=z;return q
  op=least_squares(lambda z:resid(unpack(z),f),init[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=200)
  pp=unpack(op.x);m=metrics(pp,f);print(name,width,pp,m,flush=True)
  results[name+'_w'+str(width)]={'p':pp.tolist(),'initial':init.tolist(),'width':width,'family':f,'metrics':m}
for name in ['sine_friction','cubic_friction','state_friction']:
 r=R[name];f=r['family'];p=np.array(r['p']);lo=np.array(r['bounds'][0]);hi=np.array(r['bounds'][1]);weights=np.ones(M.shape)
 weights[:4]=np.sqrt(2.)
 op=least_squares(lambda z:((sim(z,f,A,L)[:,:,0]-A[:,:,0])*weights)[M],p,bounds=(lo,hi),x_scale='jac',max_nfev=300)
 m=metrics(op.x,f);print('weight',name,op.x,m,flush=True)
 results[name+'_weighted']={'p':op.x.tolist(),'initial':p.tolist(),'family':f,'metrics':m}
json.dump(results,open('sensitivity_results.json','w'),indent=2)
