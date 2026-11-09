from fit_final import *
from fit_quintic import qsim
FR=json.load(open('final_results.json'));QR=json.load(open('quintic_results.json'))
B=np.zeros((16,450,4));B[:13,:A.shape[1]]=A;B[13:,:Av.shape[1]]=Av;LL=np.r_[L,Lv]
folds=[[13,14,15],[0,2,4,7,10],[1,5,8,11],[3,6,9,12]]
results={}
for name in ['trig_exponential','static_blend','quintic']:
 r=QR if name=='quintic' else FR[name];p=np.array(r['p']);active=np.array(r['active']);lo,hi=np.array(r['bounds']);f=0 if name=='trig_exponential' else 3
 each=[]
 for fold in folds:
  train=np.array([i for i in range(16) if i not in fold]);hold=np.array(fold);Bt=B[train];Lt=LL[train];Bh=B[hold];Lh=LL[hold];mask=np.zeros(Bt.shape[:2],bool)
  for j,ll in enumerate(Lt):mask[j,1:ll]=True
  def unpack(z):pp=p.copy();pp[active]=z;return pp
  def simulator(pp,bb,ll):return qsim(pp,bb,ll) if name=='quintic' else fsim(pp,f,bb,ll)
  op=least_squares(lambda z:(simulator(unpack(z),Bt,Lt)[:,:,0]-Bt[:,:,0])[mask],p[active],bounds=(lo[active],hi[active]),x_scale='jac',max_nfev=250,ftol=1e-9,xtol=1e-9,gtol=1e-9)
  pp=unpack(op.x);pred=simulator(pp,Bh,Lh);errors=np.concatenate([pred[j,1:ll,0]-Bh[j,1:ll,0] for j,ll in enumerate(Lh)])
  vals=[float(np.sqrt(np.mean((pred[j,1:ll,0]-Bh[j,1:ll,0])**2))) for j,ll in enumerate(Lh)]
  each.append({'held_trajectory_indices':fold,'rmse':float(np.sqrt(np.mean(errors**2))),'per_trajectory':vals,'n':len(errors),'p':pp.tolist(),'nfev':op.nfev})
  print(name,fold,each[-1],flush=True)
 total=float(np.sqrt(sum(e['rmse']**2*e['n'] for e in each)/sum(e['n'] for e in each)))
 results[name]={'folds':each,'pooled_rmse':total};print('POOLED',name,total,flush=True)
json.dump(results,open('cv_results.json','w'),indent=2)
