import json,numpy as np
# Preserve actual final-stage starting values, not the fitted endpoint.
R=json.load(open('final_fit_results.json'));starts={}
for label in ['poly3','rational2']:
 r=next(r for r in R if r['label']==label);starts[label]={k:r[k] for k in ['start','powers','bounds','start_source']}
r=next(r for r in json.load(open('robust_cos_results.json')) if r['eps']==.05)
starts['cos_power']={k:r[k] for k in ['start','bounds','eps']}
r=json.load(open('rbf_final_results.json'));starts['gaussian_field']={'start':r['traincoef'],'width':r['width'],'n':len(r['centers']),'reg':.01}
json.dump(starts,open('fit_start_values.json','w'),indent=2)
