import numpy as np,json,pandas as pd
from numba import njit
from fit_final import rhs,sim
@njit
def stress_sim(arr,t,k):
 out=np.empty(len(arr));out[0]=arr[0,0]
 for i in range(len(arr)-1):
  p=out[i];v,q=arr[i,1:3];k1=rhs(p,v,q,t,k);k2=rhs(p+2.5*k1,v,q,t,k);k3=rhs(p+2.5*k2,v,q,t,k);k4=rhs(p+5*k3,v,q,t,k)
  out[i+1]=p+5/6*(k1+2*k2+2*k3+k4)
 return out
r=json.load(open('final_results.json'));report={}
for name,d in r.items():
 t=np.array(d['parameters']);k=d['kind'];stats=[]
 for lab in ['train','val']:
  arr=pd.read_csv('data/'+lab+'.csv').to_numpy();e=sim(arr,t,k)-arr[:,0];inc=np.diff(e)/5;df=np.diff(arr[:,2])/5
  stats.append({'data':lab,'mean_pressure_residual_bar':float(e[1:].mean()),'max_abs_pressure_residual_bar':float(np.max(abs(e[1:]))),'increment_residual_future_flow_increment_correlation':float(np.corrcoef(inc,df)[0,1]),'pressure_residual_flow_correlation':float(np.corrcoef(e,arr[:,2])[0,1])})
 stress=[]
 for p in [.99,1.,1.001,1.1,2.,3.]:
  for v in [0.,10.,50.,90.,100.]:
   for q in [0.,1.,20.,40.]:
    arr=np.zeros((500,4));arr[:,0]=p;arr[:,1]=v;arr[:,2]=q;out=stress_sim(arr,t,k);stress.append((p,v,q,np.min(out),np.max(out),np.isfinite(out).all()))
 unsealed=[z for z in stress if z[1]<100];nearzero=[z for z in stress if z[2]==0 and z[1]<100]
 report[name]={'residuals':stats,'constant_input_stress_cases':len(stress),'stress_nonfinite_count':sum(not z[5] for z in stress),'stress_max_abs_bar':float(max(max(abs(z[3]),abs(z[4])) for z in stress)),'unsealed_stress_max_abs_bar':float(max(max(abs(z[3]),abs(z[4])) for z in unsealed)),'zero_flow_open_case_max_departure_from_initial_or_atmosphere_bar':float(max(max(z[4]-max(1.,z[0]),min(1.,z[0])-z[3]) for z in nearzero))}
 print(name,report[name])
open('stress_results.json','w').write(json.dumps(report,indent=2))
