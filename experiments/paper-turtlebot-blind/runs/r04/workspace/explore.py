import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
D=pd.read_csv('data/train.csv'); G=[g[['y','x1','x2','x3','x4']].to_numpy() for _,g in D.groupby('trajectory')]
U=[np.unwrap(g[:,2]) for g in G]
FAMILIES=['linear','yawquad','yawcubic','deadzone','smooth','wheel','interaction']
INIT={'linear':[.167,0,.135,0,.5], 'yawquad':[.167,0,.12,.02,0,.5], 'yawcubic':[.167,0,.13,.01,0,.5], 'deadzone':[.167,0,.15,.04,0,.5], 'smooth':[.167,0,.15,.005,.1,0,.5], 'wheel':[.18,.015,.08,.91,0,.5], 'interaction':[.167,0,.13,.1,0,.5]}
def calc(p,u,w,fam):
 if fam=='linear': a,b,g,c,mid=p;v=a*u+b;h=g*w+c
 if fam=='yawquad': a,b,g,q,c,mid=p;v=a*u+b;h=g*w+q*w*abs(w)+c
 if fam=='yawcubic': a,b,g,q,c,mid=p;v=a*u+b;h=g*w+q*w**3+c
 if fam=='deadzone': a,b,g,d,c,mid=p;v=a*u+b;h=g*np.sign(w)*np.maximum(abs(w)-d,0)+c
 if fam=='smooth': a,b,g,d,s,c,mid=p;v=a*u+b;h=g*w-d*np.tanh(w/s)+c
 if fam=='wheel': a,d,l,g,c,mid=p;L=u-l*w;R=u+l*w;L=np.sign(L)*np.maximum(abs(L)-d,0);R=np.sign(R)*np.maximum(abs(R)-d,0);v=a*(L+R)/2;h=g*(R-L)+c
 if fam=='interaction': a,b,g,q,c,mid=p;v=a*u+b;h=(g+q*u)*w+c
 return v,h,mid
def simulate(p,g,fam):
 v,h,mid=calc(p,g[:-1,3],g[:-1,4],fam); th=g[0,2]+np.r_[0,np.cumsum(h)]; pos=g[0,:2]+np.vstack([np.zeros(2),np.cumsum(np.c_[v*np.cos(th[:-1]+mid*h),v*np.sin(th[:-1]+mid*h)],axis=0)]);return np.c_[pos,th]
def bounds(fam):
 n=len(INIT[fam]);lo=np.full(n,-np.inf);hi=np.full(n,np.inf);lo[0]=.03;hi[0]=.35;lo[-1]=-1;hi[-1]=1
 if fam in ['deadzone','wheel']:lo[1 if fam=='wheel' else 3]=0;hi[1 if fam=='wheel' else 3]=.15
 if fam=='smooth':lo[3:5]=[0,.01];hi[3:5]=[.1,.5]
 if fam=='wheel':lo[2:4]=[.01,.05];hi[2:4]=[.3,3]
 return lo,hi
def residual(p,fam,ids,mode='joint'):
 rr=[]
 for i in ids:
  sim=simulate(p,G[i],fam); r=sim-G[i][:,:3];r[:,2]=sim[:,2]-U[i]
  if mode=='joint':r[:,2]*=.2
  if mode=='position':r=r[:,:2]
  if mode=='output':r=r[:,:1]
  rr.extend(r[1:].ravel())
 return np.asarray(rr)
def fit(fam,ids,mode='joint'):
 return least_squares(residual,INIT[fam],args=(fam,ids,mode),bounds=bounds(fam),max_nfev=800,ftol=1e-11,xtol=1e-11,gtol=1e-11).x
reports={}
for fam in FAMILIES:
 p=fit(fam,[0,1,2]);r=[]
 for i in range(3):
  sim=simulate(p,G[i],fam);e=sim-G[i][:,:3];e[:,2]=sim[:,2]-U[i];r.append(np.sqrt(np.mean(e[1:]**2,axis=0)).tolist())
 cv=[]
 for i in range(3):
  pc=fit(fam,[j for j in range(3) if j!=i]);s=simulate(pc,G[i],fam);e=s-G[i][:,:3];e[:,2]=s[:,2]-U[i];cv.append({'p':pc.tolist(),'rmse':np.sqrt(np.mean(e[1:]**2,axis=0)).tolist()})
 reports[fam]={'p':p.tolist(),'train_rmse':r,'cv':cv};print(fam,'p',p,'train',np.round(r,4),'cv',np.round([c['rmse'] for c in cv],4),flush=True)
# empirical polynomial baselines trained on all and heldouts
for deg in [1,2,3]:
 pf=PolynomialFeatures(deg);records=[]
 for heldout in [-1,0,1,2]:
  ids=[i for i in range(3) if i!=heldout];X=np.vstack([G[i][:-1] for i in ids]);Y=np.vstack([G[i][1:,:3]-G[i][:-1,:3] for i in ids]);Y[:,2]=np.concatenate([np.diff(U[i]) for i in ids]);P=pf.fit_transform(X);sc=np.maximum(np.linalg.norm(P,axis=0),1e-10);coef=np.linalg.lstsq(P/sc,Y,rcond=1e-6)[0]/sc[:,None];err=[]
  for i in ([heldout] if heldout!=-1 else ids):
   s=G[i][0,:3].copy();path=[s.copy()]
   for inp in G[i][:-1,3:]:
    if abs(s).max()>1e4:break
    s=s+(pf.transform(np.r_[s,inp][None,:])@coef)[0];s[2]=np.arctan2(np.sin(s[2]),np.cos(s[2]));path.append(s.copy())
   if len(path)==len(G[i]):err.append(float(np.sqrt(np.mean((np.asarray(path)[1:,0]-G[i][1:,0])**2))))
   else:err.append('diverged')
  records.append(err)
 print('polynomial',deg,records,flush=True)
json.dump(reports,open('explore_results.json','w'),indent=2)
