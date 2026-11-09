from joint_fit import *
rows=json.load(open('joint_results.json'))
report=[]
for kind in [0,2,5,10,11]:
 row=min([r for r in rows if r['kind']==kind],key=lambda r:r['cost']);p=np.array(row['p'])
 report.append('Family '+str(kind)+'; parameters '+str(p.tolist()))
 for file,data in [('train',train),('val_reused',val)]:
  frame=pd.read_csv('data/'+('val' if file=='val_reused' else 'train')+'.csv')
  predicted=np.array([accel(t,w,u,p,kind) for t,w,u in frame[['theta','omega','u']].values]); r=frame.domega.values-predicted
  yy,ww=simulate(p,kind,data[0],data[1],data[2]);mask=np.zeros_like(yy,dtype=bool)
  for i,l in enumerate(data[1]):mask[i,1:l]=True
  th_r=(yy-data[3])[mask]
  report.append(file+' acceleration residual domega-pred: moving RMSE '+str(np.sqrt(np.mean(r[np.abs(frame.omega.values)>.5]**2)))+' rad/s^2; moving mean '+str(np.mean(r[np.abs(frame.omega.values)>.5]))+' rad/s^2')
  for name,sel in [('rest',(np.abs(frame.omega.values)<1e-9)&(np.abs(frame.domega.values)<1e-8)),('slow',(np.abs(frame.omega.values)<=.5))]:
   report.append(name+' rows '+str(sel.sum())+'; acceleration RMSE '+str(np.sqrt(np.mean(r[sel]**2)))+' rad/s^2; max predicted acceleration '+str(np.max(np.abs(predicted[sel])))+' rad/s^2')
  report.append(file+' angle residual simulated-minus-measured RMSE '+str(np.sqrt(np.mean(th_r**2)))+' rad; mean '+str(np.mean(th_r))+' rad')
  for col in ['theta','omega','u']:
   values=frame[col].values;sel=np.abs(frame.omega.values)>.5
   cor=np.corrcoef(r[sel],values[sel])[0,1];report.append('moving residual correlation with '+col+': '+str(cor))
  sel=np.abs(frame.omega.values)>.5
  for feature,z in [('sin_squared',np.sin(frame.theta.values)**2),('cos_omega',np.cos(frame.theta.values)*frame.omega.values),('cos_sign',np.cos(frame.theta.values)*np.sign(frame.omega.values)),('u_cubed',frame.u.values**3)]:
   report.append('moving residual correlation with '+feature+': '+str(np.corrcoef(r[sel],z[sel])[0,1]))
  for i,l in enumerate(data[1]):
   report.append(file+' trajectory '+str(i+1)+' theta RMSE '+str(np.sqrt(np.mean((yy[i,1:l]-data[3][i,1:l])**2)))+' rad; final theta error '+str(yy[i,l-1]-data[3][i,l-1])+' rad; final simulated omega '+str(ww[i,l-1])+' rad/s')
open('residual_diagnostics.txt','w').write('\n'.join(report))
print('\n'.join(report[:38]))
