exec(open('fit_extended.py').read().split('\nresults={}')[0])
def features(theta,u,w):
 return np.c_[u*np.cos(theta),u*np.sin(theta),np.cos(theta),np.sin(theta),u*w*np.cos(theta),u*w*np.sin(theta)]
def simulate(p,g):
 u=g[:-1,3]; w=g[:-1,4]; h=p[12]*np.sign(w)*np.maximum(abs(w)-p[14],0)+p[13]; theta=g[0,2]+np.r_[0,np.cumsum(h)]; F=features(theta[:-1],u,w)
 return np.c_[g[0,:2]+np.vstack([np.zeros(2),np.cumsum(F@p[:12].reshape(2,6).T,axis=0)]),theta]
def fitf(groups,mask,lam):
 F=features(X[mask,2],X[mask,3],X[mask,4]); target=np.vstack([g[1:,:2]-g[:-1,:2] for g in G])[mask]; coef=np.linalg.lstsq(F,target,rcond=None)[0].T.ravel()
 def angle(p): return p[0]*np.sign(X[mask,4])*np.maximum(abs(X[mask,4])-p[2],0)+p[1]-Q[mask,1]
 hp=least_squares(angle,[.15,0,.08],bounds=([0,-.02,0],[.5,.02,.4])).x
 start=np.r_[coef,hp]
 def res(p):
  rr=[]
  for g in groups:
   e=simulate(p,g)[1:]-g[1:,:3]; e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); rr.append((e*np.array([1,.15,.1])).ravel())
  if lam: rr.append(np.sqrt(lam)*(p[:12]-coef))
  return np.concatenate(rr)
 end=least_squares(res,start,bounds=(np.r_[np.full(12,-2),0,-.02,0],np.r_[np.full(12,2),.5,.02,.4]),max_nfev=400,ftol=1e-9,xtol=1e-9,gtol=1e-9)
 return start,end.x
R={}
for lam in [0,1,10,100]:
 initial,p=fitf(G,np.ones(len(X),bool),lam); train=[]; cv=[]
 for g in G:
  train.append(np.sqrt(np.mean((simulate(p,g)[1:,0]-g[1:,0])**2)))
 for j in range(3):
  _,pc=fitf([g for i,g in enumerate(G) if i!=j],ids!=j+1,lam); cv.append(np.sqrt(np.mean((simulate(pc,G[j])[1:,0]-G[j][1:,0])**2)))
 print('lambda',lam,'p',p,'train',train,'cv',cv,flush=True); R[str(lam)]={'initial':initial.tolist(),'params':p.tolist(),'train':train,'cv':cv}; json.dump(R,open('fourier_results.json','w'),indent=2)
