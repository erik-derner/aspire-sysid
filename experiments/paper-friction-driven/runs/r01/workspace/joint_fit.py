from extended_identify import *
import json

def combine(a,b):
 m=max(a[2].shape[1],b[2].shape[1])
 return (np.vstack([a[0],b[0]]),np.r_[a[1],b[1]],*[np.vstack([np.pad(a[k],((0,0),(0,m-a[k].shape[1]))),np.pad(b[k],((0,0),(0,m-b[k].shape[1])))]) for k in range(2,5)])
all_data=combine(train,val)
if __name__=='__main__':
 runs=json.load(open('multistart_results.json'))+json.load(open('initial_results.json'))
 results=[]
 for kind in range(12):
  old=[r for r in runs if r['kind']==kind]
  old=sorted(old,key=lambda r:r['cost'])
  starts=[r['p'] for r in old[:2]]
  if len(starts)==1:
   p=starts[0].copy();p[4]=.6;starts.append(p)
  for p0 in starts:
   sol=fit(kind,p0,data=all_data,max_nfev=400)
   out={'kind':kind,'start':p0,'p':sol.x.tolist(),'nfev':sol.nfev,'success':bool(sol.success),'cost':float(sol.cost),'train':score(sol.x,kind,train),'val_reused':score(sol.x,kind,val)}
   results.append(out)
   print('KIND',kind,'cost',sol.cost,'train',out['train']['rmse'],'reused val',out['val_reused']['rmse'],'p',sol.x,flush=True)
  with open('joint_results.json','w') as f:json.dump(results,f,indent=2)
