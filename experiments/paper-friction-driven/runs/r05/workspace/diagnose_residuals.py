import numpy as np,pandas as pd,json
from scipy.signal import savgol_filter
from fit_models import simulate,acceleration
fits=json.load(open('results/fits.json'))
report={}
for split in ['train','val']:
 df=pd.read_csv('data/'+split+'.csv');rows=[];allkin=[];allder=[]
 for tid,d in df.groupby('trajectory',sort=False):
  g=d[['theta','omega','u','domega']].to_numpy();t,w,u,dw=g.T;n=len(g); moving=np.abs(w)>.5
  row={'trajectory':int(tid),'n':n,'driven':bool(np.any(u)),'theta_initial':float(t[0]),'theta_range':[float(t.min()),float(t.max())], 'omega_range':[float(w.min()),float(w.max())], 'rest_fraction':float(np.mean(abs(w)<.05)),'terminal_theta_mean':float(t[-min(50,n):].mean()),'terminal_theta_sd':float(t[-min(50,n):].std()),'terminal_omega_rms':float(np.sqrt(np.mean(w[-min(50,n):]**2))),'u_levels':np.unique(u).tolist()}
  kin=(t[1:]-t[:-1])/.01-(w[1:]+w[:-1])/2
  allkin.extend(kin); row['kinematic_rms']=float(np.sqrt(np.mean(kin**2)))
  # compare acceleration against difference and smoothed differentiations
  row['derivative_consistency']={}
  for name,est in [('central_omega',np.gradient(w,.01)),('savgol_omega11',savgol_filter(w,11,3,deriv=1,delta=.01)),('savgol_theta11',savgol_filter(t,11,3,deriv=2,delta=.01))]:
   row['derivative_consistency'][name]={'rmse':float(np.sqrt(np.mean((est[5:-5]-dw[5:-5])**2))),'corr':float(np.corrcoef(est[5:-5],dw[5:-5])[0,1])}
  row['models']={}
  for kind in [0,1,4,5,9,12]:
   p=np.array(fits[str(kind)]['p']);pred=simulate(g,p,kind); e=pred-t;ar=np.array([acceleration(*z[:3],p,kind) for z in g])-dw
   stat={'rmse':float(np.sqrt(np.mean(e[1:]**2))),'mean':float(e[1:].mean()),'terminal_bias':float(e[-50:].mean()),'acc_rmse_moving':float(np.sqrt(np.mean(ar[moving]**2))) if moving.any() else None}
   for name,mask in [('theta_negative',t<-.2),('theta_positive',t>.2),('omega_negative',w<-.5),('omega_positive',w>.5),('rest',abs(w)<.05)]:
    stat[name]={'n':int(mask.sum()),'angle_bias':float(e[mask].mean()) if mask.any() else None,'acc_bias':float(ar[mask].mean()) if mask.any() else None,'angle_rmse':float(np.sqrt(np.mean(e[mask]**2))) if mask.any() else None}
   row['models'][str(kind)]=stat
  rows.append(row)
 report[split]=rows
 # regression on moving rows distinguishes state-dependent biases and voltage dependence
 t,w,u,dw=df[['theta','omega','u','domega']].to_numpy().T
 mask=(abs(w)>.5)
 X=np.column_stack([u,-w,-np.sin(t),-np.sign(w),np.ones(len(t)),np.cos(t),np.sin(t)*np.cos(t),-abs(w),-np.sign(w)*np.cos(t)])
 beta=np.linalg.lstsq(X[mask],dw[mask],rcond=None)[0];r=X@beta-dw
 report[split+'_moving_regression']={'features':['u','-omega','-sin(theta)','-sign(omega)','1','cos(theta)','sin(theta)*cos(theta)','-Abs(omega)','-sign(omega)*cos(theta)'],'coefficients':beta.tolist(),'n':int(mask.sum()),'rmse':float(np.sqrt(np.mean(r[mask]**2)))}
 # Quantization, spike properties
 report[split+'_derivative_summary']={'kinematic_rmse':float(np.sqrt(np.mean(np.array(allkin)**2))),'domega_percentiles':np.percentile(dw,[0,1,5,50,95,99,100]).tolist(),'theta_step_min':float(np.min(np.diff(np.unique(t)))),'omega_nonzero_min':float(np.min(abs(w[w!=0])))}
json.dump(report,open('results/residual_diagnostics.json','w'),indent=2)
for split in ['train','val']:
 print('\n',split)
 for r in report[split]:
  print(r['trajectory'],r['n'],'drive',r['driven'],'initial',round(r['theta_initial'],3),'range',np.round(r['theta_range'],3),'rest',round(r['rest_fraction'],2),'terminal',round(r['terminal_theta_mean'],4),'+/-',round(r['terminal_theta_sd'],4),'m0 rmse/bias/end',*[round(r['models']['0'][k],4) for k in ['rmse','mean','terminal_bias']], 'm1 neg/pos',*[round(r['models']['1'][k]['angle_bias'],4) if r['models']['1'][k]['angle_bias'] is not None else None for k in ['theta_negative','theta_positive']])
 print('regression',report[split+'_moving_regression']);print('derivative',report[split+'_derivative_summary'])
