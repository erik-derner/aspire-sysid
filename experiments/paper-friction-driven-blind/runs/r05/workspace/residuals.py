import final_fit as ff,fit_models as f,numpy as np,pandas as pd,json
out={}
for label,fam,fun in ff.configs:
 f.accel=fun;p=np.array(json.load(open('results/final_'+label+'.json'))['p']);out[label]={}
 for split in ['train','val']:
  d=pd.read_csv('data/'+split+'.csv');y=d.y.values;v=d.x1.values;u=d.x2.values;z=d.dx1.values;e=z-fun(y,v,u,p,fam);out[label][split]={'derivative_rmse':float(np.sqrt(np.mean(e*e))),'bins':{}}
  for var,edges in [('y',[-3,-1,-.3,-.1,.1,.3,1,3]),('x1',[-25,-8,-1,-.15,.15,1,8,25])]:
   bins=[]
   for a,b in zip(edges[:-1],edges[1:]):
    m=(d[var]>=a)&(d[var]<b)
    if sum(m):bins.append({'range':[a,b],'n':int(sum(m)),'mean':float(np.mean(e[m])),'rmse':float(np.sqrt(np.mean(e[m]**2)))})
   out[label][split]['bins'][var]=bins
  Y,V,U,M=f.D[split];ys,vs=f.simulate(p,fam,split,True);err=(ys-Y)[M];out[label][split]['rollout_bias']=float(np.mean(err));out[label][split]['rollout_rmse']=float(np.sqrt(np.mean(err**2)))
  out[label][split]['tail_bias']=[float(np.mean((ys[:,j]-Y[:,j])[np.where(M[:,j])[0][-50:]])) for j in range(Y.shape[1])]
print(json.dumps(out,indent=2));json.dump(out,open('results/residuals.json','w'),indent=2)
