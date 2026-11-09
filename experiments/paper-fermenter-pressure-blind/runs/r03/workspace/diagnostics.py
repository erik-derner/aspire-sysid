# execute only definitions before results loop
exec(open('fit_explore.py').read().split('results={}')[0])
R=json.load(open('explore_results.json'))
for name in ['restricted','cubic','state_inverse','nonlinear_loss']:
 terms=[sp.sympify(t) for t in R[name]['terms']];fun,sim=build(terms)
 for fit in ['ols','simulation']:
  p=np.array(R[name][fit]);print('\n',name,fit)
  for key,d in [('train',A),('val',B)]:
   yy,_=sim(p,d);r=yy-d.y.to_numpy();rd=np.array([fun(*row,p) for row in d[['y','x1','x2']].to_numpy()])-d.dy.to_numpy();print(key,'y bias,median,max',r.mean(),np.median(r),np.max(np.abs(r)))
   for col in ['x1','x2','y']:
    print(col,'bins (low,high,n,yrmse,ybias,dybias)')
    for lo,hi in zip(np.quantile(d[col],[0,.1,.3,.5,.7,.9]),np.quantile(d[col],[.1,.3,.5,.7,.9,1])):
     idx=(d[col]>=lo)&(d[col]<=hi);print(round(lo,3),round(hi,3),sum(idx),*[round(val,6) for val in [np.sqrt(np.mean(r[idx]**2)),np.mean(r[idx]),np.mean(rd[idx])]])
   idx=np.argsort(np.abs(r))[-10:];print('worst',d.iloc[idx].assign(sim=yy[idx],err=r[idx]).to_string(index=True))
