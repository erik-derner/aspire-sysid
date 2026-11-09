import fit_models as f,numpy as np,json,sys,os
from scipy.optimize import least_squares
orig=f.accel

def accel(y,v,u,p,fam):
 b,a,d,k,F,w=p[:6];j=6
 if 'rational' in fam:
  c=p[j];j+=1;rest=y/(1+c*y*y)
 elif 'poly' in fam:
  c=p[j];j+=1;rest=y+c*y**3
 else:rest=np.sin(y)
 drive=b+a*u-k*rest
 if 'cos' in fam:drive=drive+p[j]*(np.cos(y)-1);j+=1
 if 'fsin' in fam:F=F+p[j]*np.sin(y);j+=1
 if 'fcos' in fam:F=F+p[j]*(np.cos(y)-1);j+=1
 if 'dcos' in fam:d=d+p[j]*(np.cos(y)-1);j+=1
 if 'vquad' in fam:d=d+p[j]*np.abs(v);j+=1
 if 'static' in fam:
  tv=np.tanh(v/w);fr=F*tv+np.clip(drive,-F,F)*(1-tv*tv)
 elif 'clamp' in fam:fr=np.clip(drive+w*v,-F,F)
 elif 'atan' in fam:fr=F*2/np.pi*np.arctan(v/w)
 else:fr=F*np.tanh(v/w)
 return drive-d*v-fr
f.accel=accel

def start(fam):
 p=[2,28,1.8,110,20,100 if 'clamp' in fam else .2];lo=[-30,5,.1,30,5,5 if 'clamp' in fam else .12];hi=[30,60,6,180,40,220 if 'clamp' in fam else 4]
 for t in ['rational','poly','cos','fsin','fcos','dcos','vquad']:
  if t in fam:
   p += [0.24 if t=='rational' else -.13 if t=='poly' else 0];lo += [.01 if t=='rational' else -.16 if t=='poly' else -.03 if t=='vquad' else -1 if t=='dcos' else -15];hi += [.5 if t=='rational' else 0 if t=='poly' else .3 if t=='vquad' else 1 if t=='dcos' else 15]
 return np.array(p),np.array(lo),np.array(hi)
f.start=start
if __name__=='__main__':
 for fam in sys.argv[1:]:
  r=f.fit(fam);json.dump(r,open('results/'+fam+'.json','w'),indent=2)
