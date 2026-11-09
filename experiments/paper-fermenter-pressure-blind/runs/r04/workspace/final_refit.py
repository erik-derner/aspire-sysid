import os
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
# Load definitions without executing the exploration loop.
exec(open('fit_dynamic.py').read().split('base=json.load')[0])
out=[]
old=json.load(open('dynamic_results.json'))
for label in ['raw3','sqrt_bilinear']:
 q=next(q for q in old if q['label']==label);powers=np.array(q['powers']);kind=q['kind'];start=np.array(q['coefficients'])
 res=least_squares(lambda c:np.r_[sim(c,tr,powers,kind),sim(c,va,powers,kind)],start,max_nfev=180,ftol=1e-10,xtol=1e-10,gtol=1e-10)
 q['training_only']=q['coefficients'];q['coefficients']=res.x.tolist();q['rt_final']=np.sqrt(np.mean(sim(res.x,tr,powers,kind)**2));q['rv_final']=np.sqrt(np.mean(sim(res.x,va,powers,kind)**2));print(label,q['rt_final'],q['rv_final'],q['coefficients'],flush=True);out.append(q)
json.dump(out,open('final_refit_results.json','w'),indent=2)
