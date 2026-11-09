"""Reproduce all submitted coefficients directly from data/train.csv.
The exploration and CV scripts are retained separately as the run record.
"""
import runpy,json,numpy as np
runpy.run_path('fit_explore.py')
exec(open('fit_extended.py').read().split('\nresults={}')[0])
for label,name,mode in [('Deadzone','hard_phase','y'),('Rational','soft_phase','y'),('Periodic','periodic','balanced')]:
 first,p=fit2(name,G,np.ones(len(X),bool),mode)
 expected=np.array([r['value'] for r in json.load(open('models/'+label+'.json'))['parameters']])
 print(label,'coefficients:',p,'maximum difference',np.max(abs(p-expected)))
exec(open('fit_fourier.py').read().split('\nR={}')[0])
first,p=fitf(G,np.ones(len(X),bool),100)
expected=np.array([r['value'] for r in json.load(open('models/FourierRidge.json'))['parameters']])
print('FourierRidge coefficients:',p,'maximum difference',np.max(abs(p-expected)))
