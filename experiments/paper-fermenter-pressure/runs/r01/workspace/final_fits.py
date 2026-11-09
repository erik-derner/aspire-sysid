import json,numpy as np
import advanced as A,resistance as R,compressible as G

def find(path,predicate):return next(r for r in json.load(open(path)) if predicate(r))

def run():
 out={}
 for label,k,d,i in [('ValvePower',2,2,0),('MixedOutlet',1,1,0)]:
  prev=find('advanced_results.json',lambda z:z['kind']==k and z['drive']==d and z['inlet']==i)
  z=A.fit(k,d,i,['train','val'],prev['params']);z['train_only']=prev;z['module']='advanced';out[label]=z
 for label,k,l,r in [('SeriesPipe',0,0,0.),('ParallelPaths',1,3,None)]:
  prev=find('resistance_results.json',lambda z:z['kind']==k and z['law']==l and z['fixed_ratio']==r)
  z=R.fit(k,l,['train','val'],prev['params'],fixed_ratio=r);z['train_only']=prev;z['module']='resistance';out[label]=z
 z=find('compressible_results.json',lambda z:z['kind']==1);z['module']='compressible';out['Compressible']=z
 for label,z in out.items():
  t=np.array(z['params']);mod={'advanced':A,'resistance':R,'compressible':G}[z['module']]
  z['diagnostics']={}
  for s,d in A.D.items():
   if mod is A:y=mod.sim(d,t,z['kind'],z['drive'],z['inlet'])
   elif mod is R:y=mod.sim(d,t,z['kind'],z['law'])
   else:y=mod.sim(d,t,z['kind'])
   e=y-d[:,0];z['diagnostics'][s]={'bias':float(e[1:].mean()),'max_abs_error':float(abs(e[1:]).max()),'lag_one_correlation':float(np.corrcoef(e[1:-1],e[2:])[0,1]),'chunk_rmse':[float(np.sqrt(np.mean(x*x))) for x in np.array_split(e[1:],6)]}
  print(label,z['rmse'],np.round(t,6),z['diagnostics'],flush=True)
 json.dump(out,open('final_results.json','w'),indent=2)
if __name__=='__main__':run()
