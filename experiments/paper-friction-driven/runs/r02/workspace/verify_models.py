import json,math,numpy as np,pandas as pd
import fit_projection as projection,fit_stiction as stick,fit_twoscale as twoscale
r=json.load(open('refit_results.json'));rng=np.random.default_rng(0)
ns={x:getattr(math,x) for x in ['sin','cos','tanh','exp']};ns.update({'Min':min,'Max':max,'pi':math.pi})
report={}
for label,mod,f in [('TwoScaleStick',twoscale,26),('ProjectionStick',projection,31),('PeriodicContact',stick,23)]:
 model=json.load(open('models/'+label+'.json'));p=np.array(r[label]['p']);env=dict(ns,**{q['name']:q['value'] for q in model['parameters']});text=model['expressions']['domega'];code=compile(text,label,'eval')
 err=0.;slope=1e99;r2=0.
 for i in range(1000):
  t=rng.uniform(-math.pi,math.pi);w=rng.uniform(-23,23);u=rng.uniform(-10,10);ee=dict(env,theta=t,omega=w,u=u);val=eval(code,{'__builtins__':{}},ee)
  if mod is twoscale:
   q=np.array([p[0],p[1],p[2],p[3],p[4],0.,p[5]]);reference=stick.acc(t,w,u,q,25)
  else:reference=mod.acc(t,w,u,p,f)
  err=max(err,abs(val-reference))
  ee['u']=u+1e-5;vp=eval(code,{'__builtins__':{}},ee);ee['u']=u-1e-5;vm=eval(code,{'__builtins__':{}},ee);slope=min(slope,(vp-vm)/2e-5)
  ee.update(omega=0,u=0);r2=max(r2,eval(code,{'__builtins__':{}},ee)*t)
 endpoints=[]
 for file in ['data/train.csv','data/val.csv']:
  for _,g in pd.read_csv(file).groupby('trajectory'):
   if max(abs(g.u))==0 and abs(g.iloc[-1].omega)<1e-5:endpoints.append(float(g.iloc[-1].theta))
 drift=[]
 for th in endpoints:
  rows=np.zeros((2001,3));rows[0,0]=th;pred=mod.sim(p,f,rows,np.array([len(rows)]));drift.append(float(pred[-1]-th))
 report[label]={'max_expression_acceleration_difference':err,'min_sampled_input_slope':slope,'max_sampled_R2_product':r2,'stationary_initial_angles':endpoints,'20s_angle_drift':drift}
 assert err<1e-10 and slope>=-1e-8 and r2==0 and max(abs(x) for x in drift)==0
print(json.dumps(report,indent=2));json.dump(report,open('verification_results.json','w'),indent=2)
