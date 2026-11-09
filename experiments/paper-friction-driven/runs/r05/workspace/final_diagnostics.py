import numpy as np,pandas as pd,json
from fit_models import train,val
from fit_combined import acc,sim
from fit_karnopp import acc as ka,sim as ks
C=json.load(open('results/combined.json'));K=json.load(open('results/karnopp.json'));out={}
for label,kind,p in [('blend',1,C['all1']['p']),('projection',0,C['all0']['p']),('karnopp',2,K['final'])]:
 p=np.array(p);records=[]
 for split,data in [('train',train),('val',val)]:
  for i,g in enumerate(data):
   theta=g[:,0];w=g[:,1];pred=ks(g,p) if kind==2 else sim(g,p,kind)
   ar=np.array([(ka(*z[:3],p) if kind==2 else acc(*z[:3],p,kind))-z[3] for z in g])
   rec={'split':split,'trajectory':i+1,'angle_rmse':float(np.sqrt(np.mean((pred[1:]-theta[1:])**2))),'terminal_bias':float(np.mean(pred[-50:]-theta[-50:]))}
   for key,m in [('moving',abs(w)>1),('negative_angle',theta<-.5),('positive_angle',theta>.5),('rest',abs(w)<.05)]:
    rec[key]={'n':int(m.sum()),'acceleration_mean_residual':float(np.mean(ar[m])) if m.any() else None,'acceleration_rmse':float(np.sqrt(np.mean(ar[m]**2))) if m.any() else None}
   records.append(rec)
 # sampled physical checks plus analytical statement is supplied in model docs
 rng=np.random.default_rng(572);t=rng.uniform(-np.pi,np.pi,100000);w=rng.uniform(-23,23,100000);u=rng.uniform(-10,10,100000)
 af=ka if kind==2 else None
 vals0=np.array([(ka(x,0.,0.,p) if kind==2 else acc(x,0.,0.,p,kind))*x for x in t]);der=np.array([((ka(x,y,z+1e-5,p)-ka(x,y,z-1e-5,p)) if kind==2 else (acc(x,y,z+1e-5,p,kind)-acc(x,y,z-1e-5,p,kind)))/2e-5 for x,y,z in zip(t,w,u)])
 out[label]={'records':records,'R2_max_product':float(vals0.max()),'R3_min_finite_difference':float(der.min())}
 print(label,'R2',vals0.max(),'R3',der.min(),'train rms',np.sqrt(np.mean(np.concatenate([(ks(g,p) if kind==2 else sim(g,p,kind))[1:]-g[1:,0] for g in train])**2)),'val rms',np.sqrt(np.mean(np.concatenate([(ks(g,p) if kind==2 else sim(g,p,kind))[1:]-g[1:,0] for g in val])**2)))
 print('terminal biases:',[(r['split'],r['trajectory'],round(r['terminal_bias'],4)) for r in records])
json.dump(out,open('results/final_diagnostics.json','w'),indent=2)
