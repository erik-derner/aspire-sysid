from fit_models import *
R=json.load(open('fit_results.json'))
for name in ['sine','sine_friction','state_friction','cubic_friction']:
 r=R[name];p=np.array(r['p']);f=r['family'];print('\nMODEL',name)
 for file,d,B,ll,mask in [('train',D,A,L,M),('val',V,Av,Lv,Mv)]:
  pred=np.array([acc(yy,vv,uu,p,f) for yy,vv,uu in d[['y','x1','x2']].values]); e=d.dx1.values-pred
  print(file,'derivative rmse',np.sqrt(np.mean(e*e)), 'mean',e.mean())
  for col,bins in [('x1',[-30,-8,-3,-.3,0,.3,3,8,30]),('y',[-3,-1,-.3,0,.3,1,3]),('x2',[-6,-2,-.01,.01,2,6])]:
   xx=d[col].values
   print(col,[(lo,hi,int(np.sum((xx>=lo)&(xx<hi))),round(np.mean(e[(xx>=lo)&(xx<hi)]),3)) for lo,hi in zip(bins[:-1],bins[1:]) if np.sum((xx>=lo)&(xx<hi))])
  pred=sim(p,f,B,ll)
  for j,l in enumerate(ll):
   err=pred[j,:l,0]-B[j,:l,0]
   print('traj',j+1,'mean',round(err.mean(),4),'final',round(err[-1],4),'max',round(np.max(abs(err)),4),'measured final',B[j,l-1,:2])
