import json,time
exec(open('refit_final.py').read().split('R=json.load')[0])
r=json.load(open('final_results.json'))['harmonic'];p0=r['p'];lo,hi=r['bounds'];t=time.time()
opt=least_squares(lambda p:rollout(p,'harmonic',ALL),p0,bounds=(lo,hi),x_scale='jac',max_nfev=70,ftol=1e-9,diff_step=1e-6)
out={'p':opt.x.tolist(),'initial':p0,'bounds':[lo,hi],'nfev':opt.nfev,'success':bool(opt.success),'train':metrics(opt.x,'harmonic',TR),'val':metrics(opt.x,'harmonic',VA),'seconds':time.time()-t}
json.dump(out,open('refined_harmonic_results.json','w'),indent=2);print(out)
