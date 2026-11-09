import identify as I
import numpy as np,json
from scipy.optimize import least_squares
from pathlib import Path
original=I.step
I.SPECS['wheels']=dict(names=['gv','gw','ell','dz','bw'],start=[.9,.8,.12,.012,0],lo=[.2,.2,.04,0,-.15],hi=[1.5,1.5,.3,.06,.15],integration='arc')
def newstep(states,inputs,p,key):
 if key!='wheels':return original(states,inputs,p,key)
 gv,gw,ell,dz,bw=p;vf,va=inputs.T;x,y,ph=states.T
 def dzfun(z):return np.sign(z)*np.maximum(np.abs(z)-dz,0)
 right=dzfun(vf+ell*va);left=dzfun(vf-ell*va)
 v=I.TS*gv*(right+left)/2;z=I.TS*(gw*(right-left)/(2*ell)+bw)
 scale=np.sinc(z/(2*np.pi));th=ph+z/2
 return np.column_stack([x+v*scale*np.cos(th),y+v*scale*np.sin(th),ph+z])
I.step=newstep
def run():
 out={}
 for key in ['euler','bias','phase','deadphase','wheels']:
  for mode,weights in [('balanced',(1,1,.3)),('xhead',(1,0,.15)),('xonly',(1,0,0))]:
   f=I.fit(key,[0,1,2],weights=weights);cv=[]
   for h in range(3):
    ff=I.fit(key,[i for i in range(3) if i!=h],weights=weights);s=I.score(ff.x,key,[h]);s['parameters']=ff.x.tolist();cv.append(s)
   out[key+'_'+mode]={'parameters':f.x.tolist(),'score':I.score(f.x,key,[0,1,2]),'cv':cv,'weights':weights}
   print(key,mode,np.round(f.x,5),'train',np.round(out[key+'_'+mode]['score']['window_rmse'],5),'CVx',np.round([s['window_rmse'][0] for s in cv],5),flush=True)
 Path('investigate_results.json').write_text(json.dumps(out,indent=2))

if __name__=="__main__":run()
