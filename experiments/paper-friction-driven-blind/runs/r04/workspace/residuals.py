import json,numpy as np,pandas as pd
from fit_rollout import load,sim
R=json.load(open('rollout_results.json'))
for name in ['tanh','offset','cubic','scaled','stribeck']:
 r=R[name];print('\n',name)
 for fn in ['train','val']:
  frames=[]
  for i,a in enumerate(load('data/'+fn+'.csv')):
   pred=sim(a,np.array(r['p']),r['kind']);e=pred[:,0]-a[:,0]
   print(fn,i+1,'RMSE',round(np.sqrt(np.mean(e[1:]**2)),4),'end',round(e[-1],4),'mean',round(e.mean(),4))
   frames.append(pd.DataFrame({'y':a[:,0],'v':a[:,1],'u':a[:,2],'res':e,'accres':np.array([0.]*len(a))}))
  d=pd.concat(frames)
  for c in ['v','y','u']:
   print(c,d.groupby(pd.cut(d[c],6),observed=True)['res'].agg(['mean','std','count']).round(3).to_string())
