exec(open('fit_extended.py').read().split('\nresults={}')[0])
SPECS2={
 'asymmetric':([.16,0,.19,.001,.1,-.2,0,.19,.1],([0,-.01,0,-.02,0,-3,-.5,0,0],[.4,.01,.5,.02,.4,2,.5,.5,.4])),
 'saturated':([.16,0,.19,.001,.1,-.2,0,.7],([0,-.01,0,-.02,0,-3,-.5,.2],[.4,.01,.5,.02,.3,2,.5,1.5]))}
def inputs2(p,u,w,f):
 v=p[0]*u+p[1]
 if f=='asymmetric': h=p[2]*np.maximum(w-p[4],0)-p[7]*np.maximum(-w-p[8],0)+p[3]
 else: h=p[2]*np.sign(w)*np.minimum(np.maximum(abs(w)-p[4],0),p[7])+p[3]
 return v,h
def sim2(p,g,f):
 v,h=inputs2(p,g[:-1,3],g[:-1,4],f); theta=g[0,2]+np.r_[0,np.cumsum(h)]; m=theta[:-1]+p[5]*h+p[6]
 return np.c_[g[0,0]+np.r_[0,np.cumsum(v*np.cos(m))],g[0,1]+np.r_[0,np.cumsum(v*np.sin(m))],theta]
def fitmulti(f,groups,mask,mode):
 init,bounds=SPECS2[f]; weights=np.array([1,.15,.1]) if mode=='y' else np.array([1,1,.3]); opts=[]
 for width in [.03,.08,.14,.22]:
  start=np.array(init); start[4]=width
  if f=='asymmetric': start[8]=width
  def one(p):
   v,h=inputs2(p,X[mask,3],X[mask,4],f); return np.r_[v-.2*Q[mask,0],.3*(h-Q[mask,1])]
  first=least_squares(one,start,bounds=bounds,max_nfev=100)
  end=least_squares(res2,first.x,args=(groups,f,weights),bounds=bounds,max_nfev=300,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  opts.append((np.sum(end.fun**2),first.x,end.x,width))
 return min(opts,key=lambda z:z[0])
results={}
for f in SPECS2:
 results[f]={}
 for mode in ['y','balanced']:
  cost,initial,p,width=fitmulti(f,G,np.ones(len(X),bool),mode); train=[]; cv=[]; cvp=[]
  for g in G:
   e=sim2(p,g,f)[1:]-g[1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); train.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  for j in range(3):
   _,_,pc,_=fitmulti(f,[g for i,g in enumerate(G) if i!=j],ids!=j+1,mode); cvp.append(pc.tolist()); e=sim2(pc,G[j],f)[1:]-G[j][1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); cv.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  print(f,mode,'p',p,'train',np.array(train).round(4),'CV',np.array(cv).round(4),flush=True)
  results[f][mode]={'initial':initial.tolist(),'params':p.tolist(),'train':train,'cv':cv,'cvp':cvp,'startwidth':width}; json.dump(results,open('piecewise_results.json','w'),indent=2)
