from joint_fit import *
import time
rows=json.load(open('joint_results.json'))
best={k:min([r for r in rows if r['kind']==k],key=lambda x:x['cost']) for k in range(12)}
results=[]
for kind in [0,1,2,3,5,6,7,10,11]:
 errors=[];folds=[]
 for j in range(len(all_data[1])):
  mask=np.arange(len(all_data[1]))!=j
  fitdata=tuple(x[mask] for x in all_data)
  held=tuple(x[j:j+1] for x in all_data)
  sol=fit(kind,best[kind]['p'],data=fitdata,max_nfev=200)
  sc=score(sol.x,kind,held)
  errors.append(sc['rmse'])
  folds.append({'omitted':j,'p':sol.x.tolist(),'held_rmse':sc['rmse'],'cost':float(sol.cost),'nfev':sol.nfev})
 total=float(np.sqrt(np.average(np.array(errors)**2,weights=all_data[1]-1)))
 row={'kind':kind,'loto_rmse':total,'folds':folds}
 results.append(row)
 print('kind',kind,'LOTO RMSE',total,'folds',errors,flush=True)
 with open('crossvalidation_results.json','w') as f:json.dump(results,f,indent=2)
