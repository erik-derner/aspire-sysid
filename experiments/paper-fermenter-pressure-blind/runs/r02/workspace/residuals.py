import numpy as np,pandas as pd,json
r=next(r for r in json.load(open('poly_results.json')) if r['deg']==3 and r['mode']=='full');c=np.array(r['c']);pw=np.array(r['powers']);print('terms',list(zip(pw.tolist(),c)))
for fn in ['train','val']:
 d=pd.read_csv('data/'+fn+'.csv');z=np.column_stack((d.y-1,d.x1/60,d.x2/20));X=np.prod(z[:,None,:]**pw[None,:,:],axis=2);res=d.dy.values-X@c;d['res']=res
 print(fn,'worst',d.iloc[np.argsort(abs(res))[-15:]].to_string());print('res autocorr',[(lag,np.corrcoef(res[:-lag],res[lag:])[0,1]) for lag in [1,2,3,5,10]])
 for col in ['y','x1','x2']:
  print(col,'bin mean',d.groupby(pd.qcut(d[col],5),observed=True).res.agg(['mean','std']).to_string())
  print('lagcorr',[(lag,round(np.corrcoef(res[2:-2],d[col].values[2+lag:len(d)-2+lag])[0,1],3)) for lag in [-2,-1,0,1,2]])
 print('res vs input difference',[(col,np.corrcoef(res[1:],np.diff(d[col]))[0,1]) for col in ['x1','x2']])
