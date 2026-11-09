import numpy as np,pandas as pd,json
from refine import PolyModel,RationalModel,rollout
from final_fit import CosModel
from rbf_fit import RBFModel
tr=pd.read_csv('data/train.csv');va=pd.read_csv('data/val.csv');out={}
for r in json.load(open('final_fit_results.json')):
 if r['label'] not in ['poly3','rational2','cos_power']:continue
 m=PolyModel(r['powers']) if r['kind']=='poly' else RationalModel(r['powers']) if r['kind']=='rational' else CosModel();c=np.array(r['coef']);out[r['label']]={}
 for f,d in [('train',tr),('val',va)]:
  yp=rollout(m,c,d);e=yp-d.y.values;fp=np.array([m.fg(y-1,u/60,v/20,c)[0] for y,u,v in d[['y','x1','x2']].values]);er=fp-d.dy.values;fz=np.array([m.fg(y-1,u/60,v/20,c)[1] for y,u,v in d[['y','x1','x2']].values])
  out[r['label']][f]=dict(roll_rmse=float(np.sqrt(np.mean(e[1:]**2))),roll_bias=float(np.mean(e[1:])),dy_bias=float(np.mean(er)),dy_rmse=float(np.sqrt(np.mean(er**2))),dy_autocorr=[float(np.corrcoef(er[:-i],er[i:])[0,1]) for i in [1,2,5,10]],dy_correlations=[float(np.corrcoef(er,d[k])[0,1]) for k in ['y','x1','x2']],dy_slope_corr=[float(np.corrcoef(er[1:],np.diff(d[k]))[0,1]) for k in ['x1','x2']],state_range=[float(yp.min()),float(yp.max())],feedback_quantiles=np.quantile(fz,[0,.1,.5,.9,1]).tolist(),state_block_rmse=[float(np.sqrt(np.mean(e[i:i+200]**2))) for i in range(0,len(e),200)])
 print(r['label'],json.dumps(out[r['label']],indent=2))
r=json.load(open('rbf_final_results.json'));m=RBFModel(r['centers'],r['width']);c=np.array(r['coef']);out['gaussian_field']={}
for f,d in [('train',tr),('val',va)]:
 yp=rollout(m,c,d);er=np.array([m.fg(y-1,u/60,v/20,c)[0] for y,u,v in d[['y','x1','x2']].values])-d.dy.values
 out['gaussian_field'][f]=dict(roll_rmse=float(np.sqrt(np.mean((yp[1:]-d.y.values[1:])**2))),dy_rmse=float(np.sqrt(np.mean(er**2))),state_range=[float(yp.min()),float(yp.max())],dy_autocorr=[float(np.corrcoef(er[:-i],er[i:])[0,1]) for i in [1,2,5,10]])
print('gaussian_field',out['gaussian_field'])
json.dump(out,open('diagnostics_results.json','w'),indent=2)
