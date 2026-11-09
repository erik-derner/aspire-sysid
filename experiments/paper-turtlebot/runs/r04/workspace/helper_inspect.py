import numpy as np,pandas as pd,json
from scipy.optimize import least_squares
D=pd.read_csv('data/train.csv'); ts=.2
rows=[]
for tr,g in D.groupby('trajectory'):
 g=g.reset_index(drop=True); p=np.unwrap(g.phi.values); dx=np.diff(g.x);dy=np.diff(g.y); dp=np.diff(p); mid=p[:-1]+dp/2
 forward=(dx*np.cos(mid)+dy*np.sin(mid))/ts; lateral=(-dx*np.sin(mid)+dy*np.cos(mid))/ts
 for k in range(len(g)-1):
  rows.append(dict(tr=int(tr),k=k,phase=k%5,block=k//5,vf=g.v_f[k],va=g.v_a[k],f=forward[k],lat=lateral[k],a=dp[k]/ts,delta=dp[k],direction=np.arctan2(dy[k],dx[k])-mid[k],prevf=g.v_f[max(0,k-k%5-1)],preva=g.v_a[max(0,k-k%5-1)]))
R=pd.DataFrame(rows);R.to_csv('helper_transitions.csv',index=False)
# last two transitions of complete 5-transition blocks: phases 3,4, exclude terminal truncated block
B=R[R.block<29].groupby(['tr','block']).agg(vf=('vf','first'),va=('va','first'),prevf=('prevf','first'),preva=('preva','first'))
for ph,name in [([3,4],'steady'),([0],'first'),([1],'second'),([2],'third')]:
 z=R[(R.block<29)&R.phase.isin(ph)].groupby(['tr','block'])[['f','a','lat']].mean();B=B.join(z.add_prefix(name+'_'))
B=B.reset_index();B.to_csv('helper_blocks.csv',index=False)
report={'ranges':D[['v_f','v_a','x','y','phi']].agg(['min','max']).to_dict(),'phase_summary':R.groupby('phase')[['f','a','lat']].agg(['mean','std']).to_json()}
f=B.vf.values;a=B.va.values; yf=B.steady_f.values;ya=B.steady_a.values
features={'linear':np.c_[f,a,np.ones(len(f))],'forward_linear':np.c_[f,np.ones(len(f))],'angular_linear':np.c_[a,np.ones(len(f))],'poly2':np.c_[np.ones(len(f)),f,a,f*f,f*a,a*a],'poly3':np.c_[np.ones(len(f)),f,a,f*f,f*a,a*a,f**3,f*f*a,f*a*a,a**3],'physical_f':np.c_[f,np.ones(len(f)),abs(a),f*abs(a),a],'physical_a':np.c_[a,np.sign(a),a*abs(a),f*a,np.ones(len(f))]}
fits={}
for name,X in features.items():
 for out,y in [('f',yf),('a',ya)]:
  c=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@c;pred=np.empty(len(y))
  for tr in [1,2,3]:
   train=B.tr.values!=tr;pred[~train]=X[~train]@np.linalg.lstsq(X[train],y[train],rcond=None)[0]
  fits[name+'_'+out]={'coef':c.tolist(),'rmse':float(np.sqrt(np.mean(r*r))),'leave_trajectory_out_rmse':float(np.sqrt(np.mean((pred-y)**2))),'r2':float(1-np.sum(r*r)/np.sum((y-y.mean())**2))}
report['fits']=fits
# dead-zone: separate forward base nonlinearity and coupled turning dead-zone
for out,y in [('f',yf),('a',ya)]:
 if out=='f':
  fun=lambda c: c[0]*np.maximum(f-c[1],0)+c[2]+c[3]*abs(a)
  start=[.85,.015,0,0]
 else:
  fun=lambda c: c[0]*np.sign(a)*np.maximum(abs(a)-c[1],0)+c[2]*f*a+c[3]
  start=[.85,.1,0,0]
 res=least_squares(lambda c:fun(c)-y,start);report['deadzone_'+out]={'coef':res.x.tolist(),'rmse':float(np.sqrt(np.mean(res.fun**2)))}
# transient regression target velocity on current and previous steady observations
for out in ['f','a']:
 steady=B['steady_'+out].values; previous=[]
 for i,row in B.iterrows():
  q=B[(B.tr==row.tr)&(B.block==row.block-1)];previous.append(0 if len(q)==0 else q['steady_'+out].iloc[0])
 previous=np.array(previous)
 for phase in ['first','second','third']:
  y=B[phase+'_'+out].values;X=np.c_[steady,previous,np.ones(len(steady))];c=np.linalg.lstsq(X,y,rcond=None)[0]
  report['transient_'+phase+'_'+out]={'coef_current_previous_intercept':c.tolist(),'rmse':float(np.sqrt(np.mean((X@c-y)**2))),'rmse_against_steady':float(np.sqrt(np.mean((steady-y)**2)))}
# steady residual trajectory means and correlations using physical maps
for out in ['f','a']:
 X=features['physical_'+out]; y=B['steady_'+out].values;c=np.linalg.lstsq(X,y,rcond=None)[0];r=y-X@c;B['res_'+out]=r
 report['residual_'+out]={'trajectory_means':B.groupby('tr')['res_'+out].mean().to_dict(),'correlations':{key:float(np.corrcoef(r,B[key])[0,1]) for key in ['vf','va','prevf','preva','block']}}
report['steady_lateral']={'rms':float(np.sqrt(np.mean(B.steady_lat**2))),'mean':float(B.steady_lat.mean()),'max_abs':float(abs(B.steady_lat).max())}
report['transition_lateral_rms']=float(np.sqrt(np.mean(R.lat**2)))
# directional integration fraction inferred robustly for nonzero speeds/turn
q=R[(R.f>.02)&(abs(R.delta)>.02)].copy();ang=(q.direction+np.pi)%(2*np.pi)-np.pi
report['heading_fraction']={'offset_relative_mid_slope':float(np.dot(q.delta,ang)/np.dot(q.delta,q.delta)),'angular_offset_rms':float(np.sqrt(np.mean(ang**2))),'count':len(q)}
open('helper_report.json','w').write(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
