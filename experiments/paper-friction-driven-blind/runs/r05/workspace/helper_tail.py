exec(open('helper_explore.py').read().split('results=[]')[0])
print('TAIL DUPLICATION (all allowed splits)')
groups=[(s,int(k),g.reset_index(drop=True)) for s,d in D.items() for k,g in d.groupby('trajectory')]
for s,k,g in groups:
 if len(g)>150:continue
 for ss,kk,h in groups:
  if len(h)<=len(g):continue
  cols=['y','x1','x2','dx1']; dif=np.max(np.abs(g[cols].values-h[cols].values[-len(g):]),axis=0)
  if dif[0]<1e-8:print(s,k,'equals tail',ss,kk,'max errors y x1 x2 dx1',dif)
print('RESIDUAL AUTOCORRELATION sin+tanh on each split within trajectories')
r=json.load(open('helper_explore_results.json'));a=next(a for a in r['fits'] if a['family']=='sin_tanh');b=np.array(list(a['coefficients'].values()))
for s,d in D.items():
 es=[]
 for k,g in d.groupby('trajectory'):
  X,_=matrix(g,'sin_tanh',a['eps']);es.append(g.dx1.values-X@b)
 print(s,{lag:float(np.corrcoef(np.concatenate([e[:-lag] for e in es]),np.concatenate([e[lag:] for e in es]))[0,1]) for lag in [1,2,3,5,10,20]})
print('INPUT ALIGNMENT DIAGNOSTIC sin+coul, centered interior only (not deployable if future inputs needed)')
for delta in [-2,-1,0,1,2]:
 tr=[];va=[]
 for s,d in D.items():
  ps=[]
  for k,g in d.groupby('trajectory'):
   h=g.copy();h['x2']=np.roll(g.x2.values,-delta);ps.append(h.iloc[2:-2])
  if s=='train':tr=pd.concat(ps)
  else:va=pd.concat(ps)
 X,n=matrix(tr,'sin_coul');b=np.linalg.lstsq(X,tr.dx1,rcond=None)[0];Z,_=matrix(va,'sin_coul');print(delta,'samples shift',dict(zip(n,b)),'train rmse',rmse(tr.dx1.values-X@b),'val rmse',rmse(va.dx1.values-Z@b))
print('ACTIVE GLOBAL FIT sin+coul abs(x1)>.3 training; no offset vs offset')
d=D['train'];d=d[abs(d.x1)>.3];X,n=matrix(d,'sin_coul')
for withoffset in [True,False]:
 start=0 if withoffset else 1;b=np.linalg.lstsq(X[:,start:],d.dx1,rcond=None)[0];print(dict(zip(n[start:],b)),len(d),'rows rmse',rmse(d.dx1.values-X[:,start:]@b))
