import numpy as np,pandas as pd,json
from identify import rhs,sim,train,val
r=json.load(open('fit_results.json'))
for name in ['linear','power','bounded_power','resistance','isentropic']:
 t=np.array(r[name]['parameters']); k=r[name]['kind']; print('\nMODEL',name)
 for lab,arr in [('train',train),('val',val)]:
  e=sim(arr,t,k)-arr[:,0]; de=np.array([rhs(p,v,q,t,k) for p,v,q,_ in arr])-arr[:,3]
  df=pd.DataFrame(arr,columns=['p','valve','flow','dp']);df['e']=e;df['de']=de
  print(lab,'errors mean/std',e.mean(),e.std(),'deriv rmse',np.sqrt(np.mean(de**2)))
  print('corr',df.corr()[['e','de']].to_string())
  for c in ['p','valve','flow']:
   print(c,df.groupby(pd.cut(df[c],5),observed=True)[['e','de']].mean().to_string())
  print('time blocks',df.groupby(np.arange(len(df))//150)[['e','de']].mean().to_string())
