# Import function definitions without running fitting loops.
exec(open('explore_models.py').read().split('results=[]')[0])
R=json.load(open('explore_results.json'));out=[]
for mode in [0,6]:
 r=next(r for r in R if r['mode']==mode);p0=np.array(r['params']);ids=np.array([i for i in r['ids'] if i!=5]);lo=np.array(r['lower']);hi=np.array(r['upper'])
 for width in [.15,.2,.3]:
  p0[5]=width
  def unpack(q):
   p=p0.copy();p[ids]=q;return p
  fit=least_squares(lambda q:(rollout(unpack(q),T,nt,mode)-T[:,0])[mT],p0[ids],bounds=(lo[ids],hi[ids]),max_nfev=160,diff_step=1e-4,ftol=2e-8,xtol=2e-8,gtol=2e-8)
  p=unpack(fit.x);r2=dict(mode=mode,width=width,params=p.tolist(),train_rmse=float(np.sqrt(np.mean(((rollout(p,T,nt,mode)-T[:,0])[mT])**2))),val_rmse=float(np.sqrt(np.mean(((rollout(p,V,nv,mode)-V[:,0])[mV])**2))))
  out.append(r2);print(r2,flush=True)
json.dump(out,open('width_results.json','w'),indent=2)
