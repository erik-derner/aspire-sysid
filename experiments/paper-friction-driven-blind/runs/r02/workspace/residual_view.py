import json
r=json.load(open('helper_results.json'))
for n in ['pendulum_coulomb','nonlinear_friction','duffing_coulomb']:
 print(n)
 for d in ['train','val']:
  z=r['residuals'][n][d];print(d,'lag1',z['lag1'],'corr',z['correlations']);print('bytraj',z['by_trajectory']);print('bins y',z['bins']['y']); print('bins v',z['bins']['x1'])
