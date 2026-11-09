exec(open('fit_models.py').read().split('results={}')[0])
# Independent extended families, parameters displacement gain, offset, turn gain, turn bias, width, direction factor, angle bias, optional speed slope.
SPECS2={
 'hard_phase':([.16,0,.19,.001,.1,-.4,0],([0,-.01,0,-.02,0,-3,-.5],[.4,.01,.5,.02,.4,2,.5])),
 'soft_phase':([.16,0,.19,.001,.1,-.4,0],([0,-.01,0,-.02,.001,-3,-.5],[.4,.01,.5,.02,.7,2,.5])),
 'tanh_phase':([.16,0,.19,.001,.1,-.4,0,1],([0,-.01,0,-.02,0,-3,-.5,.01],[.4,.01,.5,.02,.4,2,.5,10])),
 'periodic':([.16,0,.19,.001,.1,-.4,0,0,0],([0,-.01,0,-.02,0,-3,-.5,-.01,-.01],[.4,.01,.5,.02,.4,2,.5,.01,.01])),
 'radial':([.16,0,.19,.001,.1,-.4,0,0],([0,-.01,0,-.02,0,-3,-.5,-.1],[.4,.01,.5,.02,.4,2,.5,.1]))}
def inputs2(p,u,w,f):
 v=p[0]*u+p[1]
 if f=='tanh_phase': v=p[0]*np.tanh(p[7]*u)/p[7]+p[1]
 if f=='soft_phase': h=p[2]*w**3/(w**2+p[4]**2)+p[3]
 else: h=p[2]*np.sign(w)*np.maximum(abs(w)-p[4],0)+p[3]
 return v,h
def sim2(p,g,f):
 u=g[:-1,3]; w=g[:-1,4]; v,h=inputs2(p,u,w,f)
 if f in ['hard_phase','soft_phase','tanh_phase']:
  theta=g[0,2]+np.r_[0,np.cumsum(h)]; m=theta[:-1]+p[5]*h+p[6];
  return np.c_[g[0,0]+np.r_[0,np.cumsum(v*np.cos(m))],g[0,1]+np.r_[0,np.cumsum(v*np.sin(m))],theta]
 pred=[g[0,:3]]
 for i in range(len(u)):
  a=pred[-1]; hh=h[i]; vv=v[i]
  if f=='periodic': hh+=p[7]*np.sin(a[2])+p[8]*np.cos(a[2])
  if f=='radial': vv+=p[7]*u[i]*np.tanh(np.sqrt(a[0]**2+a[1]**2))
  m=a[2]+p[5]*hh+p[6]; pred.append(a+np.array([vv*np.cos(m),vv*np.sin(m),hh]))
 return np.array(pred)
def res2(p,groups,f,weights):
 rr=[]
 for g in groups:
  e=sim2(p,g,f)[1:]-g[1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); rr.append((e*weights).ravel())
 return np.concatenate(rr)
def fit2(f,groups,mask,mode):
 init,bounds=SPECS2[f]
 def one(p):
  v,h=inputs2(p,X[mask,3],X[mask,4],f); return np.r_[v-.2*Q[mask,0],.3*(h-Q[mask,1])]
 first=least_squares(one,init,bounds=bounds,max_nfev=100)
 weights={'balanced':np.array([1,1,.3]),'y':np.array([1,.15,.1])}[mode]
 end=least_squares(res2,first.x,args=(groups,f,weights),bounds=bounds,max_nfev=200,ftol=1e-9,xtol=1e-9,gtol=1e-9)
 return first.x,end.x
results={}
for f in SPECS2:
 results[f]={}
 for mode in ['balanced','y']:
  initial,p=fit2(f,G,np.ones(len(X),bool),mode); train=[]; cv=[]; cvp=[]
  for g in G:
   e=sim2(p,g,f)[1:]-g[1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); train.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  for j in range(3):
   _,pc=fit2(f,[g for i,g in enumerate(G) if i!=j],ids!=j+1,mode); cvp.append(pc.tolist()); e=sim2(pc,G[j],f)[1:]-G[j][1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); cv.append(np.sqrt(np.mean(e**2,axis=0)).tolist())
  print(f,mode,'p',p,'train',np.array(train).round(4),'CV',np.array(cv).round(4),flush=True)
  results[f][mode]={'initial':initial.tolist(),'params':p.tolist(),'train':train,'cv':cv,'cvp':cvp}
  json.dump(results,open('extended_results.json','w'),indent=2)
