import numpy as np,pandas as pd,json
fits=json.load(open('results/fits.json'))
for label in ['linear_power','orifice_power','power_satpower']:
 print('\nMODEL',label)
 for name in ['train','val']:
  d=pd.read_csv('data/'+name+'.csv'); r=np.load('results/'+label+'_'+name+'.npz');d['res']=r['res'];d['dres']=r['dres'];d['time']=np.arange(len(d))*5
  print(name,'mean',d.res.mean(),'range',d.res.min(),d.res.max(),'corr',d[['p','flow','valve','res','dres']].corr()['res'].to_dict())
  for col in ['p','valve','flow','time']:
   print(col,d.groupby(pd.qcut(d[col],5,duplicates='drop'),observed=True)[['res','dres']].agg(['mean','std']).to_string())
  print('worst',d.iloc[np.argsort(np.abs(d.res))[-10:]][['time','p','valve','flow','res','dres']].to_string(index=False))
