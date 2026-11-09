import numpy as np,pandas as pd
from scipy.optimize import lsq_linear
D=pd.read_csv('data/train.csv');sel=abs(D.omega)>1
x=D.loc[sel]; X=np.c_[x.u,-x.omega,-np.sin(x.theta),-np.sign(x.omega)];fit=lsq_linear(X,x.domega,bounds=(0,np.inf));p=fit.x
print('OLS moving a,b,c,f:',p,'rms',np.sqrt(np.mean((X@p-x.domega)**2)))
D['res']=D.domega-(p[0]*D.u-p[1]*D.omega-p[2]*np.sin(D.theta)-p[3]*np.sign(D.omega))
for col,bins in [('omega',[-25,-10,-5,-1,-.1,.1,1,5,10,25]),('theta',[-3,-2,-1,-.2,.2,1,2,3]),('u',[-5,-3,-1,-.1,.1,1,3,5])]:
 print(col,D[abs(D.omega)>1].groupby(pd.cut(D.loc[abs(D.omega)>1,col],bins),observed=True).res.agg(['count','mean','std']).to_string())
print('per trajectory',D[sel].groupby('trajectory').res.agg(['count','mean','std']).to_string())
