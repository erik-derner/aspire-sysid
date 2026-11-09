import numpy as np,pandas as pd
D=pd.read_csv('diagnostics_bounded_power.csv')
for name in ['train','val']:
 d=pd.read_csv('data/'+name+'.csv'); n=len(d); p=d.p.to_numpy(); dp=d.dp.to_numpy(); v=d.valve.to_numpy(); q=d.flow.to_numpy(); sim=D[name+'_p'].to_numpy()[:n]; e=D[name+'_error'].to_numpy()[:n]; inc=np.diff(p)/5
 print('\nDATA',name,'n',n,'ranges',d.agg(['min','max']).to_dict())
 print('error definition max deviations sim-p',np.max(abs(e-(sim-p))),'RMSE',np.sqrt(np.mean(e[1:]**2)),'mean',np.mean(e[1:]))
 for lag in [-2,-1,0,1,2]:
  # compare dp[k] with forward increment[k+lag]
  k=np.arange(n); ok=(k+lag>=0)&(k+lag<n-1); x=dp[k[ok]]; y=inc[k[ok]+lag]
  print('dp vs increment lag',lag,'N',len(x),'RMSE',np.sqrt(np.mean((x-y)**2)),'corr',np.corrcoef(x,y)[0,1])
 for thresh in [.25,.5,1,2]:
  ix=np.where(q<thresh)[0]; print('lowflow',thresh,'N',len(ix),'p quantiles',np.quantile(p[ix],[0,.25,.5,.75,1]),'valve range', [v[ix].min(),v[ix].max()],'dpmean',dp[ix].mean(),'emean',e[ix].mean())
 ix=np.where(q<.5)[0]; runs=np.split(ix,np.where(np.diff(ix)>1)[0]+1)
 print('lowflow runs start/end/count/pfirst/plast/vmean/qmean',[(int(r[0]),int(r[-1]),len(r),p[r[0]],p[r[-1]],v[r].mean(),q[r].mean()) for r in runs if len(r)>1])
 r=np.diff(e)/5; print('increment residual RMS',np.sqrt(np.mean(r*r)))
 for label,x in [('p',p),('valve',v),('flow',q),('dvalve',np.r_[0,np.diff(v)]/5),('dflow',np.r_[0,np.diff(q)]/5),('dp',dp)]:
  vals=[]
  for lag in range(-5,6):
   k=np.arange(n-1); ok=(k+lag>=0)&(k+lag<n); vals.append((lag,np.corrcoef(r[k[ok]],x[k[ok]+lag])[0,1]))
  print('increment residual corr',label,vals)
 print('error corr p/valve/flow/dp',[(c,np.corrcoef(e,d[c])[0,1]) for c in d.columns])
 print('residual acf',[(lag,np.corrcoef(r[:-lag],r[lag:])[0,1]) for lag in [1,2,3,4,5,10,20]])
 print('error quantiles',np.quantile(e,[0,.01,.1,.5,.9,.99,1]))
 for start in range(0,n,250):
  sl=slice(start,min(start+250,n)); print('block',start,min(start+250,n),'emean',e[sl].mean(),'erms',np.sqrt(np.mean(e[sl]**2)))
