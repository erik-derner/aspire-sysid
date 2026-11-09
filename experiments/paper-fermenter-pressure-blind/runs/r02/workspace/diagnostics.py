import json,numpy as np,pandas as pd
from final_fit import residual
from final_spline import r as spline_res
cases=json.load(open('final_fit_results.json'))+[json.load(open('final_spline_results.json'))]
out=[]
for case in cases:
 if case['label']=='PowerEquilibrium':continue
 p=np.array(case['p']);rec={'label':case['label']}
 for fn in ['train','val']:
  d=pd.read_csv('data/'+fn+'.csv');rd=residual(p,case,d,'der') if case['kind']!='spline' else spline_res(p,d,'der');ry=residual(p,case,d,'roll') if case['kind']!='spline' else spline_res(p,d,'roll');yh=np.r_[d.y.iloc[0],d.y.values[1:]+ry]
  rec[fn]={'der_mean':float(np.mean(rd)),'der_rmse':float(np.mean(rd*rd)**.5),'roll_rmse':float(np.mean(ry*ry)**.5),'der_autocorr':{str(l):float(np.corrcoef(rd[:-l],rd[l:])[0,1]) for l in [1,2,5,10]},'input_change_corr':{c:float(np.corrcoef(rd[1:],np.diff(d[c]))[0,1]) for c in ['x1','x2']},'simulation_range':[float(yh.min()),float(yh.max())]}
 out.append(rec)
print(json.dumps(out,indent=2));json.dump(out,open('diagnostics_results.json','w'),indent=2)
