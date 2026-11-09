from extended_identify import *
import json,time
init=json.load(open('initial_results.json'))
records=[]
for kind in [0,1,5,7,8,9,10,11]:
 starts=[]
 if kind<=7:
  starts.append(init[kind]['p'])
  for v in [.16,.3,.7,1.5]:
   p=init[kind]['p'].copy();p[4]=v;starts.append(p)
 elif kind==8:
  starts=[[28,110,1.8,20,v] for v in [.15,.3,.7,1.5]]
 else:
  starts=[[28,110,1.8,20,v]+([0] if kind!=9 else []) for v in [30,60,100,180]]
 best=None
 for p0 in starts:
  sol=fit(kind,p0,max_nfev=300)
  row={'kind':kind,'start':p0,'p':sol.x.tolist(),'cost':float(sol.cost),'nfev':sol.nfev,'success':bool(sol.success),'train':score(sol.x,kind,train),'val':score(sol.x,kind,val)}
  records.append(row)
  print(kind, 'cost',sol.cost,'val',row['val']['rmse'],'p',sol.x,flush=True)
 with open('multistart_results.json','w') as f:json.dump(records,f,indent=2)
