import numpy as np,pandas as pd,json
from fit_rollout import D,rollout
R=json.load(open('rollout_fits.json'));r=next(r for r in R if r['pl']=='series')
for s,data in D.items():
 sim=rollout(r['t'],data,r['pl'],r['vl']);df=pd.DataFrame(data,columns=['p','valve','flow','dp']);df['sim']=sim;df['res']=sim-df.p
 print(s,'bias',df.res.mean(),'std',df.res.std(),'quantiles',df.res.quantile([0,.01,.5,.99,1]).to_dict())
 for c in ['p','valve','flow']:
  print(c,df.groupby(pd.cut(df[c],8),observed=True).res.agg(['mean','std','count']).to_string())
 df.to_csv('residual_'+s+'.csv',index=False)
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(3,1,figsize=(14,8));ax[0].plot(df.p,label='p');ax[0].plot(sim,label='simulation');ax[0].legend();ax[1].plot(df.res);ax[2].plot(df.valve);ax[2].plot(df.flow);fig.tight_layout();fig.savefig('residual_'+s+'.png');plt.close(fig)
print('Derivative correlation shifts')
d=D['train'];t=r['t'];p,v,q,y=d.T;a,c,m,k,pa,e,n=t;x=1-v/100;cv=(x/(x+k))**m;z=p-pa;h=2*z/(e+np.sqrt(e*e+4*np.abs(z))); pred=a*q-c*cv*h
for delta in [-2,-1,0,1,2]:
 ids=np.arange(2,len(y)-2);print(delta,np.sqrt(np.mean((pred[ids+delta]-y[ids])**2)))
