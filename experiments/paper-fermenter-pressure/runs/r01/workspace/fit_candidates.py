"""Reproduce the submitted coefficients using only the supplied trajectories.
Run: python fit_candidates.py
All simulation uses classical RK4, one 5-second step and current-row held inputs.
Requires numpy, pandas, scipy, numba. Supporting model definitions are in
advanced.py, resistance.py, compressible.py and stable_mixed.py.
"""
import json
import advanced as A, resistance as R, compressible as G, stable_mixed as S

def main():
 out={}
 tr=A.fit(2,2,0,['train']);z=A.fit(2,2,0,['train','val'],tr['params']);z['train_only']=tr;out['ValvePower']=z
 tr=R.fit(0,0,['train'],fixed_ratio=0.);z=R.fit(0,0,['train','val'],tr['params'],fixed_ratio=0.);z['train_only']=tr;out['SeriesPipe']=z
 tr=G.fit(1,['train']);z=G.fit(1,['train','val'],tr['params']);z['train_only']=tr;out['Compressible']=z
 initial=A.setup(1,1,0)[0];tr=S.fit(['train'],initial);z=S.fit(['train','val'],tr['params']);z['train_only']=tr;out['MixedOutlet']=z
 json.dump(out,open('reproduced_parameters.json','w'),indent=2)
 expected=json.load(open('final_results.json'))
 for label,z in out.items():
  err=max(abs(a-b) for a,b in zip(z['params'],expected[label]['params']))
  print(label,'maximum coefficient difference:',err,'RMSE (bar):',z['rmse'])
if __name__=='__main__':main()
