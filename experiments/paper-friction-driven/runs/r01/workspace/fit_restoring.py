from restoring_identify import *
from joint_fit import combine
all_data=combine(train,val)
rows=json.load(open('joint_results.json'))
results=[]
for kind,old in [(12,1),(13,5)]:
 base=min([r for r in rows if r['kind']==old],key=lambda r:r['cost'])['p']
 for q in [0,-.1,.1]:
  start=base+[q];sol=fit(kind,start,data=all_data,max_nfev=400)
  row={'kind':kind,'start':start,'p':sol.x.tolist(),'cost':float(sol.cost),'nfev':sol.nfev,'train':score(sol.x,kind,train),'val_reused':score(sol.x,kind,val)}
  results.append(row); print(kind,sol.cost,sol.x,flush=True)
 best=min([r for r in results if r['kind']==kind],key=lambda r:r['cost'])
 errs=[]
 for j in range(len(all_data[1])):
  mask=np.arange(len(all_data[1]))!=j
  sol=fit(kind,best['p'],data=tuple(x[mask] for x in all_data),max_nfev=200)
  sc=score(sol.x,kind,tuple(x[j:j+1] for x in all_data));errs.append(sc['rmse'])
 best['loto_rmse']=float(np.sqrt(np.average(np.array(errs)**2,weights=all_data[1]-1)))
 print('LOTO',best['loto_rmse'],flush=True)
 with open('restoring_results.json','w') as f:json.dump(results,f,indent=2)
