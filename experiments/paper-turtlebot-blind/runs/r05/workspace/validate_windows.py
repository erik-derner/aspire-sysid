from fit_kinematic import *
from pathlib import Path

def windows(arrays,H):
 return [a[i:i+H+1] for a in arrays for i in range(0,len(a)-1, max(1,H//3)) if len(a[i:i+H+1])>=H+1]
def fit_window(f,arrays,H):
 wa=arrays if H==149 else windows(arrays,H)
 p,b=CONFIG[f]
 starts=[p]
 if f=='rational':starts += [[.17,0,.20,.0001,.10,.001],[.17,0,.19,.004,.08,0]]
 if f=='smooth':starts += [[.17,0,.19,.02,.03,0],[.17,0,.19,.02,.2,0]]
 sols=[least_squares(residual,pp,args=(wa,f),bounds=b,max_nfev=350,ftol=1e-9,xtol=1e-9,gtol=1e-9) for pp in starts]
 return min(sols,key=lambda sol:np.dot(sol.fun,sol.fun)).x
if __name__=='__main__':
 result={}
 for f in ['linear','deadzone','rational','smooth','cubic','wheelsoft']:
  for H in [1,5,10,25,50,149]:
   p=fit_window(f,TRAJS,H);cv=[]
   for j in range(3):
    q=fit_window(f,[a for k,a in enumerate(TRAJS) if k!=j],H);cv.append(score(q,[TRAJS[j]],f))
   key=f+'_'+str(H);result[key]={'f':f,'H':H,'p':p.tolist(),'train':score(p,TRAJS,f),'cv':cv,'cv_rmse':np.sqrt(np.mean(np.array(cv)**2,axis=0)).tolist()}
   print(key,json.dumps(result[key]),flush=True)
 Path('window_results.json').write_text(json.dumps(result,indent=2))
