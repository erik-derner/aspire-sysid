"""Re-estimate all delivered coefficients, then write the model JSON files.
Structure/validation evidence is saved in the companion *_results.json files.
Run the individual fitting and diagnostics scripts to reproduce that evidence.
"""
import json,runpy
from fit_kinematic import trajs
from fit_regularized import fit as fit_rigid
from fit_fourier import fit as fit_fourier
R=json.load(open('regularized_results.json'))
for key,fam in [('deadzone_mid_100','deadzone_mid'),('power_mid_100','power_mid')]:
 p,start=fit_rigid(trajs,fam,100);R[key]['parameters']=p.tolist();R[key]['starting']=start
json.dump(R,open('regularized_results.json','w'),indent=2)
F=json.load(open('fourier_results.json'));p,start=fit_fourier(trajs,100);F['100']['parameters']=p.tolist();F['100']['starting']=start.tolist();json.dump(F,open('fourier_results.json','w'),indent=2)
runpy.run_path('export_models.py',run_name='__main__')
