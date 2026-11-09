import numpy as np,json
from scipy.optimize import least_squares
from fit_models import train,val
from fit_combined import res,score
from fit_karnopp import res as kres,score as kscore
# Official training trajectories 8 and 11 reproduce tails of validation trajectories 1 and 2.
data=[g for i,g in enumerate(train) if i not in [7,10]]
C=json.load(open('results/combined.json'));K=json.load(open('results/karnopp.json'));out={}
for kind,label in [(0,'projection'),(1,'blend')]:
 r=C['train'+str(kind)];p0=r['start'];lo=r['lower'];hi=r['upper']
 fit=least_squares(res,p0,args=(kind,data),bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=500,ftol=1e-9,xtol=1e-9,gtol=1e-8)
 out[label]={'p':fit.x.tolist(),'start':p0,'train_subset_rmse':score(fit.x,kind,data),'val_rmse':score(fit.x,kind,val),'nfev':fit.nfev}
 print(label,out[label],flush=True)
# Repeat the velocity-band grid, genuinely selecting it on independent parent recordings.
grid=[]
for r in K['grid']:
 p0=r['start'];lo=r['lower'];hi=r['upper']
 fit=least_squares(kres,p0,args=(data,),bounds=(lo,hi),diff_step=1e-4,x_scale='jac',max_nfev=300,ftol=1e-8,xtol=1e-8,gtol=1e-8)
 q={'p':fit.x.tolist(),'start':p0,'lower':lo,'upper':hi,'train_subset_rmse':kscore(fit.x,data),'val_rmse':kscore(fit.x,val),'nfev':fit.nfev};grid.append(q);print('karnopp',q,flush=True)
out['karnopp_grid']=grid;out['karnopp_selected']=min(grid,key=lambda q:q['val_rmse'])
json.dump(out,open('results/independent_selection.json','w'),indent=2)
