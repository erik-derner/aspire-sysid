import json
rows=json.load(open('joint_results.json'))
labels={5:'HarmonicStiction',11:'ProjectedAngleFriction',2:'StribeckStiction',0:'SmoothCoulomb',3:'AngleDamping',6:'MotorSaturation'}
cv={r['kind']:r['loto_rmse'] for r in json.load(open('crossvalidation_results.json'))}
config=[]
for k,label in labels.items():
 row=min([r for r in rows if r['kind']==k],key=lambda x:x['cost']).copy()
 row['label']=label;row['loto_rmse']=cv[k]
 config.append(row)
json.dump(config,open('candidate_config.json','w'),indent=2)
