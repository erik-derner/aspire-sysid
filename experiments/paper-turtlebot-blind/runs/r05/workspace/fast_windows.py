from fit_kinematic import *
from validate_windows import windows

def fastres(p,arrays,f,angweight=.25):
 a=np.asarray(arrays);s,w=maps(p,a[:,:-1,3],a[:,:-1,4],f)
 theta=a[:,0:1,2]+np.cumsum(w,axis=1);mid=theta-w/2
 xy=a[:,0:1,:2]+np.cumsum(np.stack([s*np.cos(mid),s*np.sin(mid)],axis=2),axis=1)
 e=np.concatenate([xy-a[:,1:,:2],(np.arctan2(np.sin(theta-a[:,1:,2]),np.cos(theta-a[:,1:,2]))*angweight)[:,:,None]],axis=2)
 return e.ravel()
def ff(f,arrays,H):
 wa=arrays if H==149 else windows(arrays,H);p,b=CONFIG[f];starts=[p]
 if f=='rational':starts += [[.17,0,.20,.0001,.10,.001],[.17,0,.19,.004,.08,0]]
 if f=='smooth':starts += [[.17,0,.19,.02,.03,0],[.17,0,.19,.02,.2,0]]
 sols=[least_squares(fastres,pp,args=(wa,f),bounds=b,max_nfev=200,ftol=1e-8,xtol=1e-8,gtol=1e-8) for pp in starts]
 return min(sols,key=lambda sol:np.dot(sol.fun,sol.fun)).x
if __name__=='__main__':
 result={}
 for f in ['linear','deadzone','rational','smooth','cubic','wheelsoft']:
  for H in [10,25,50,149]:
   p=ff(f,TRAJS,H);cv=[]
   for j in range(3):
    q=ff(f,[a for k,a in enumerate(TRAJS) if k!=j],H);cv.append(score(q,[TRAJS[j]],f))
   q=ff(f,[a[:100] for a in TRAJS],min(H,50));tail=score(q,[a[99:] for a in TRAJS],f)
   key=f+'_'+str(H);result[key]={'f':f,'H':H,'p':p.tolist(),'train':score(p,TRAJS,f),'cv':cv,'cv_rmse':np.sqrt(np.mean(np.array(cv)**2,axis=0)).tolist(),'tail':tail}
   print(key,json.dumps(result[key]),flush=True)
 Path('fast_results.json').write_text(json.dumps(result,indent=2))
