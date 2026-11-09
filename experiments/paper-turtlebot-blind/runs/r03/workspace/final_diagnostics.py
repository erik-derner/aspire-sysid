exec(open('fit_fourier.py').read().split('\nR={}')[0])
p=np.array(json.load(open('fourier_results.json'))['100']['params']); T=np.vstack([g[1:,:3] for g in G]); pred=[]
for g in G:
 a=g[:-1]; h=p[12]*np.sign(a[:,4])*np.maximum(abs(a[:,4])-p[14],0)+p[13]; F=features(a[:,2],a[:,3],a[:,4]); pred.append(np.c_[a[:,:2]+F@p[:12].reshape(2,6).T,a[:,2]+h])
e=T-np.vstack(pred);e[:,2]=np.arctan2(np.sin(e[:,2]),np.cos(e[:,2])); lines=['FourierRidge observed-state one-step RMSE '+str(np.sqrt(np.mean(e**2,axis=0)))]
for i in range(5):
 mask=phase==i; lines.append('block phase '+str(i)+' residual std '+str(e[mask].std(axis=0)))
for j in range(3):
 mask=ids==j+1; lines.append('trajectory '+str(j+1)+' residual lag1 correlations '+str([np.corrcoef(e[mask,jj][:-1],e[mask,jj][1:])[0,1] for jj in range(3)]))
lines.append('FourierRidge validation pooled y RMSE '+str(np.sqrt(np.mean(np.array(json.load(open('fourier_results.json'))['100']['cv'])**2))))
print('\n'.join(lines));open('final_residual_report.txt','w').write('\n'.join(lines))
