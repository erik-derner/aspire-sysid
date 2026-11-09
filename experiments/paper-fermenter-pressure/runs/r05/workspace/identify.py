import json, numpy as np, pandas as pd
from scipy.optimize import least_squares
from numba import njit
from pathlib import Path

@njit
def rhs(p,v,q,t,kind):
    a,b,m=t[0],t[1],t[2]
    op=max(0., min(1.,1-v/100))
    x=p-1.
    if kind in (0,1,3,4,5): c=b*op**m
    elif kind==2: c=b*(np.exp(m*op)-1.)
    elif kind==6: c=b*op/(op+t[4])
    elif kind==7: c=b*op**m/(1+t[5]*op**m)
    else: c=b*op**m
    if kind==0: h=x
    elif kind in (1,2,6,7):
        n,d=t[3],t[4] if kind!=6 else t[5]
        h=x/(x*x+d*d)**((1-n)/2)
    elif kind==3:
        d=t[3]; h=x*np.sqrt(max(p+1,0.01))/(x*x+d*d)**0.25
    elif kind==4:
        d=t[3]; high=max(p,1.); low=min(max(p,0.01),1.); r=max(low/high,(2/2.4)**3.5)
        h=np.sign(x)*high*np.sqrt(max(r**(2/1.4)-r**(2.4/1.4),0))
        h=h*abs(x)/np.sqrt(x*x+d*d)
    elif kind==5:
        d=t[3]; h=2*x/(d+np.sqrt(d*d+4*abs(x)))
    else: h=x
    return a*q-c*h

@njit
def sim(arr,t,kind):
    N=len(arr); out=np.empty(N); out[0]=arr[0,0]
    for i in range(N-1):
        p=out[i]; v,q=arr[i,1],arr[i,2]
        k1=rhs(p,v,q,t,kind); k2=rhs(p+2.5*k1,v,q,t,kind); k3=rhs(p+2.5*k2,v,q,t,kind); k4=rhs(p+5*k3,v,q,t,kind)
        out[i+1]=p+5/6*(k1+2*k2+2*k3+k4)
        if not np.isfinite(out[i+1]) or abs(out[i+1])>50:
            out[i+1:]=50.; return out
    return out

specs={
 'linear':(0,[.001,.2,2],[.0001,.0001,.1],[.01,5,8]),
 'power':(1,[.001,.1,1.5,.6,.015],[.0001,.0001,.1,.3,.002],[.01,5,8,1.5,.2]),
 'exponential':(2,[.001,.01,3.,.6,.015],[.0001,.00001,.01,.3,.002],[.01,5,12,1.5,.2]),
 'gas_sqrt':(3,[.001,.1,1.5,.015],[.0001,.0001,.1,.002],[.01,5,8,.2]),
 'isentropic':(4,[.001,.3,1.5,.015],[.0001,.0001,.1,.002],[.01,5,8,.2]),
 'resistance':(5,[.001,.1,1.5,.1],[.0001,.0001,.1,.002],[.01,5,8,2]),
 'saturating':(6,[.001,.1,1.,.6,.2,.015],[.0001,.0001,.9999,.3,.001,.002],[.01,5,1.0001,1.5,5,.2]),
 'bounded_power':(7,[.001,.2,2,.6,.015,3],[.0001,.0001,.1,.3,.002,.001],[.01,5,8,1.5,.2,100])}
train=pd.read_csv('data/train.csv').to_numpy(); val=pd.read_csv('data/val.csv').to_numpy()

def derivres(t,k):
    return np.array([rhs(p,v,q,t,k) for p,v,q,_ in train])-train[:,3]

def run():
    results={}
    for name,(k,start,lo,hi) in specs.items():
        print('\nFITTING',name,flush=True)
        dfit=least_squares(derivres,start,args=(k,),bounds=(lo,hi),max_nfev=500,x_scale='jac',ftol=1e-10,xtol=1e-10,gtol=1e-10)
        fit=least_squares(lambda t:sim(train,t,k)[1:]-train[1:,0],dfit.x,bounds=(lo,hi),max_nfev=400,x_scale='jac',ftol=1e-10,xtol=1e-10,gtol=1e-10)
        pt=sim(train,fit.x,k); pv=sim(val,fit.x,k)
        res={'kind':k,'start':start,'lower':lo,'upper':hi,'derivative_fit':dfit.x.tolist(),'parameters':fit.x.tolist(),'train_rmse':float(np.sqrt(np.mean((pt[1:]-train[1:,0])**2))),'val_rmse':float(np.sqrt(np.mean((pv[1:]-val[1:,0])**2))),'nfev':fit.nfev}
        results[name]=res; print(res,flush=True)
        pd.DataFrame({'train_p':pd.Series(pt),'train_error':pd.Series(pt-train[:,0]),'val_p':pd.Series(pv),'val_error':pd.Series(pv-val[:,0])}).to_csv('diagnostics_'+name+'.csv',index=False)
    Path('fit_results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__': run()
