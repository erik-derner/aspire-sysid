import pandas as pd,numpy as np,json
from scipy.optimize import least_squares
B=pd.read_csv('helper_blocks.csv');R=pd.read_csv('helper_transitions.csv');out={}
for tr,g in B.groupby('tr'):
 f=g.vf.values;a=g.va.values
 out[str(tr)]={}
 for label,q in [('all',np.ones(len(g),bool)),('early',g.block.values<15),('late',g.block.values>=15)]:
  cf=np.linalg.lstsq(np.c_[f[q],np.ones(q.sum())],g.steady_f.values[q],rcond=None)[0]
  ca=np.linalg.lstsq(np.c_[a[q],np.sign(a[q]),f[q]*a[q],np.ones(q.sum())],g.steady_a.values[q],rcond=None)[0]
  out[str(tr)][label]={'count':int(q.sum()),'forward_gain_bias':cf.tolist(),'angular_gain_sign_coupling_bias':ca.tolist()}
# held-out validation of deadzone maps
for v in ['f','a']:
 pred=np.empty(len(B));y=B['steady_'+v].values
 for tr in [1,2,3]:
  q=B.tr.values!=tr;f=B.vf.values;a=B.va.values
  if v=='a':
   fn=lambda c:c[0]*np.sign(a)*np.maximum(abs(a)-c[1],0)+c[2]*f*a+c[3];s=[.7,.09,.45,0]
  else:
   fn=lambda c:c[0]*np.maximum(f-c[1],0)+c[2]+c[3]*abs(a);s=[.84,.01,.006,0]
  c=least_squares(lambda c:(fn(c)-y)[q],s).x;pred[~q]=fn(c)[~q]
 out['deadzone_cv_'+v]=float(np.sqrt(np.mean((pred-y)**2)))
# noise / late stability evidence
for v in ['f','a']:
 late=R[(R.block<29)&R.phase.isin([3,4])].pivot(index=['tr','block'],columns='phase',values=v)
 out['late_phase_difference_'+v]={'rms':float(np.sqrt(np.mean((late[4]-late[3])**2))),'mean':float((late[4]-late[3]).mean())}
# fitted physical maps residual autocorrelation
for v in ['f','a']:
 f=B.vf.values;a=B.va.values
 X=np.c_[f,np.ones(len(f)),abs(a),f*abs(a),a] if v=='f' else np.c_[a,np.sign(a),a*abs(a),f*a,np.ones(len(f))]
 res=B['steady_'+v].values-X@np.linalg.lstsq(X,B['steady_'+v].values,rcond=None)[0]
 r0=[];r1=[]
 for tr in [1,2,3]:
  r=res[B.tr.values==tr];r0.extend(r[:-1]);r1.extend(r[1:])
 out['residual_lag1_'+v]=float(np.corrcoef(r0,r1)[0,1])
print(json.dumps(out,indent=2));open('helper_residual_report.json','w').write(json.dumps(out,indent=2))
