from fast_windows import *
oldmaps=maps
CONFIG['exponential']=([.17,0,.17,.02,.07,0],([.05,-.01,.04,.0005,0,-.02],[.30,.01,.40,.2,.3,.02]))
CONFIG['phase']=([.17,0,.17,.07,0,.5],([.05,-.01,.04,0,-.02,-2],[.30,.01,.35,.3,.02,2]))
def emaps(p,v,u,f):
 if f=='exponential':return p[0]*v+p[1],p[2]*(1-np.exp(-v/p[3]))*np.sign(u)*np.maximum(abs(u)-p[4],0)+p[5]
 if f=='phase':return oldmaps(p[:5],v,u,'deadzone')
 return oldmaps(p,v,u,f)
def er(p,arrays,f):
 a=np.asarray(arrays);s,w=emaps(p,a[:,:-1,3],a[:,:-1,4],f);theta=a[:,0:1,2]+np.cumsum(w,axis=1);q=p[-1] if f=='phase' else .5;mid=theta+(q-1)*w
 xy=a[:,0:1,:2]+np.cumsum(np.stack([s*np.cos(mid),s*np.sin(mid)],axis=2),axis=1)
 e=np.concatenate([xy-a[:,1:,:2],(np.arctan2(np.sin(theta-a[:,1:,2]),np.cos(theta-a[:,1:,2]))*.25)[:,:,None]],axis=2);return e.ravel()
def ef(f,arrays,H):
 wa=arrays if H==149 else windows(arrays,H);p,b=CONFIG[f];sol=least_squares(er,p,args=(wa,f),bounds=b,max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-9);return sol.x
def esim(p,a,f):
 s,w=emaps(p,a[:-1,3],a[:-1,4],f);theta=a[0,2]+np.r_[0,np.cumsum(w)];q=p[-1] if f=='phase' else .5;mid=theta[:-1]+q*w;xy=a[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.column_stack([s*np.cos(mid),s*np.sin(mid)]),axis=0)]);return np.column_stack([xy,theta])
def escore(p,arrays,f):
 E=np.vstack([esim(p,a,f)[1:,:2]-a[1:,:2] for a in arrays]);return np.sqrt(np.mean(E**2,axis=0)).tolist()
if __name__=='__main__':
 result={}
 for f in ['exponential','phase']:
  for H in [10,25,149]:
   p=ef(f,TRAJS,H);cv=[]
   for j in range(3):
    q=ef(f,[a for k,a in enumerate(TRAJS) if k!=j],H);cv.append(escore(q,[TRAJS[j]],f))
   q=ef(f,[a[:100] for a in TRAJS],min(H,50));tail=escore(q,[a[99:] for a in TRAJS],f)
   key=f+'_'+str(H);result[key]={'f':f,'H':H,'p':p.tolist(),'train':escore(p,TRAJS,f),'cv':cv,'cv_rmse':np.sqrt(np.mean(np.array(cv)**2,axis=0)).tolist(),'tail':tail};print(key,json.dumps(result[key]),flush=True)
 Path('extra_results.json').write_text(json.dumps(result,indent=2))
