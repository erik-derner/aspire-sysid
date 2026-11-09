exec(open('fit_extended.py').read().split('\nresults={}')[0])
R=json.load(open('extended_results.json')); report=[]
for f,mode in [('hard_phase','y'),('soft_phase','y'),('periodic','balanced')]:
 p=np.array(R[f][mode]['params']); v,h=inputs2(p,X[:,3],X[:,4],f); theta=X[:,2]+p[5]*h+p[6]; epos=np.c_[v*np.cos(theta),v*np.sin(theta)]
 targets=np.vstack([g[1:,:2]-g[:-1,:2] for g in G]); etheta=Q[:,1]-h
 if f=='periodic': etheta-=p[7]*np.sin(X[:,2])+p[8]*np.cos(X[:,2])
 e=targets-epos
 report.append(f+' '+mode+' one-step position RMSE '+str(np.sqrt(np.mean(e**2,axis=0)))+' angle RMSE '+str(np.sqrt(np.mean(etheta**2))))
 for phaseval in range(5):
  mask=phase==phaseval; report.append('phase '+str(phaseval)+' angle residual mean/std '+str([etheta[mask].mean(),etheta[mask].std()])+' position residual mean '+str(e[mask].mean(axis=0)))
 for j in range(3):
  mask=ids==j+1; rr=etheta[mask]; report.append('trajectory '+str(j+1)+' angle residual mean/lag1 corr '+str([rr.mean(),np.corrcoef(rr[:-1],rr[1:])[0,1]]))
 report.append('angle residual correlations y,x1,sintheta,costheta,u,w: '+str([np.corrcoef(etheta,z)[0,1] for z in [X[:,0],X[:,1],np.sin(X[:,2]),np.cos(X[:,2]),X[:,3],X[:,4]]]))
open('residual_report.txt','w').write('\n'.join(report)); print('\n'.join(report))
