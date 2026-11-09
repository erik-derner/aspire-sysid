import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
from pathlib import Path
D=pd.read_csv('data/train.csv'); TS=.2
TRAJ=[]
for _,g in D.groupby('trajectory'):
 s=g[['x','y','phi']].to_numpy(); s[:,2]=np.unwrap(s[:,2]); TRAJ.append((s,g[['v_f','v_a']].to_numpy()))
# Parameter order: forward scale, angular scale, then listed extra coefficients.
SPECS={
 'euler':dict(names=['gv','gw'],start=[.83,.68],lo=[.2,.2],hi=[1.5,1.5],integration='euler'),
 'arc':dict(names=['gv','gw'],start=[.83,.68],lo=[.2,.2],hi=[1.5,1.5],integration='arc'),
 'bias':dict(names=['gv','gw','bw'],start=[.83,.68,0],lo=[.2,.2,-.15],hi=[1.5,1.5,.15],integration='arc'),
 'phase':dict(names=['gv','gw','bw','q'],start=[.83,.68,0,.5],lo=[.2,.2,-.15,-2],hi=[1.5,1.5,.15,2],integration='phase'),
 'deadzone':dict(names=['gv','gw','dz','bw'],start=[.83,.78,.08,0],lo=[.2,.2,0,-.15],hi=[1.5,1.5,.35,.15],integration='arc'),
 'deadphase':dict(names=['gv','gw','dz','bw','q'],start=[.83,.78,.08,0,.5],lo=[.2,.2,0,-.15,-2],hi=[1.5,1.5,.35,.15,2],integration='phase'),
 'cubic':dict(names=['gv','gw','cw','bw'],start=[.83,.58,.18,0],lo=[.2,.1,-.5,-.15],hi=[1.5,1.5,1,.15],integration='arc'),
 'smooth':dict(names=['gv','gw','sw','width','bw'],start=[.83,.8,.08,.12,0],lo=[.2,.2,0,.025,-.15],hi=[1.5,1.5,.3,.6,.15],integration='arc'),
 'coupled':dict(names=['gv','gw','dz','bw','cv'],start=[.83,.78,.08,0,0],lo=[.2,.2,0,-.15,-1],hi=[1.5,1.5,.35,.15,1],integration='arc'),
 'harmonic':dict(names=['gv','gw','bw','hs','hc'],start=[.83,.68,0,0,0],lo=[.2,.2,-.15,-.1,-.1],hi=[1.5,1.5,.15,.1,.1],integration='phase'),
 'lateral':dict(names=['gv','gw','bw','lat'],start=[.83,.68,0,0],lo=[.2,.2,-.15,-.2],hi=[1.5,1.5,.15,.2],integration='arc'),
}
def step(states,inputs,p,key):
 a=dict(zip(SPECS[key]['names'],p)); vf,va=inputs.T; x,y,ph=states.T
 w=a['gw']*va+a.get('bw',0)
 if 'dz' in a: w=(a['gw']+a.get('cv',0)*vf)*np.sign(va)*np.maximum(np.abs(va)-a['dz'],0)+a.get('bw',0)
 if 'cw' in a: w+=a['cw']*va**3
 if 'sw' in a: w-=a['sw']*np.tanh(va/a['width'])
 if 'hs' in a: w+=a['hs']*np.sin(ph)+a['hc']*np.cos(ph)
 z=TS*w; v=TS*a['gv']*vf; integ=SPECS[key]['integration']
 q=0 if integ=='euler' else a.get('q',.5)
 scale=np.sinc(z/(2*np.pi)) if integ=='arc' else 1
 th=ph+q*z
 vl=TS*a.get('lat',0)*vf
 return np.column_stack([x+scale*(v*np.cos(th)-vl*np.sin(th)),y+scale*(v*np.sin(th)+vl*np.cos(th)),ph+z])
def windows(ids,H=25,stride=1):
 init=[]; inputs=[]; targets=[]
 for i in ids:
  s,u=TRAJ[i]
  for k in range(0,len(s)-H,stride): init.append(s[k]); inputs.append(u[k:k+H]); targets.append(s[k+1:k+H+1])
 return np.array(init),np.array(inputs),np.array(targets)
def residual(p,key,win,weights=(1,1,.3)):
 s,u,t=win; cur=s.copy(); out=[]
 for j in range(u.shape[1]):
  cur=step(cur,u[:,j],p,key); out.append((cur-t[:,j])*weights)
 return np.stack(out,axis=1).ravel()
def score(p,key,ids,H=25):
 r=residual(p,key,windows(ids,H),weights=(1,1,1)).reshape(-1,H,3)
 out={'window_rmse':np.sqrt(np.mean(r*r,axis=(0,1))).tolist()}
 full=[]
 for i in ids:
  s,u=TRAJ[i]; cur=s[0:1].copy(); rr=[]
  for j in range(len(s)-1): cur=step(cur,u[j:j+1],p,key); rr.append(cur[0]-s[j+1])
  rr=np.array(rr);full.append(np.sqrt(np.mean(rr*rr,axis=0)).tolist())
 out['full_rmse']=full; return out
def fit(key,ids,weights=(1,1,.3),start=None):
 spec=SPECS[key];win=windows(ids)
 return least_squares(residual,spec['start'] if start is None else start,args=(key,win,weights),bounds=(spec['lo'],spec['hi']),method='trf',max_nfev=400,ftol=1e-10,xtol=1e-10,gtol=1e-10)
def run():
 results={}
 for key in SPECS:
  f=fit(key,[0,1,2]);p=f.x;cv=[]
  for hold in range(3):
   ff=fit(key,[i for i in range(3) if i!=hold]);sc=score(ff.x,key,[hold]);sc['parameters']=ff.x.tolist();cv.append(sc)
  results[key]={'parameters':p.tolist(),'objective':float(np.dot(f.fun,f.fun)),'nfev':f.nfev,'score':score(p,key,[0,1,2]),'cv':cv}
  print(key,np.round(p,6),'train',np.round(results[key]['score']['window_rmse'],5),'CV x',np.round([r['window_rmse'][0] for r in cv],5),'full x',np.round([r[0] for r in results[key]['score']['full_rmse']],5),flush=True)
 Path('fit_results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':run()
