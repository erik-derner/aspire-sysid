import os,json,time
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from numba import njit

TS=0.01

def load(path):
 d=pd.read_csv(path); groups=[g for _,g in d.groupby('trajectory',sort=False)]
 starts=np.array([[g.theta.iloc[0],g.omega.iloc[0]] for g in groups])
 lens=np.array([len(g) for g in groups],dtype=np.int64)
 U=np.zeros((len(groups),max(lens))); Y=U.copy(); W=U.copy()
 for i,g in enumerate(groups):
  U[i,:len(g)]=g.u; Y[i,:len(g)]=g.theta; W[i,:len(g)]=g.omega
 return starts,lens,U,Y,W
train=load('data/train.csv'); val=load('data/val.csv')

# Families: 0 smooth Coulomb; 1 analytic static cancellation;
# 2 Stribeck static cancellation; 3 angle-dependent damping plus static cancellation;
# 4 asymmetric moving friction plus static cancellation;
# 5 static cancellation and second restoring harmonic;
# 6 motor saturation plus static cancellation; 7 angle-dependent friction.
@njit(cache=True)
def accel(t,w,u,p,kind):
 a,g,b,c,v=p[:5]
 drive=a*u-g*np.sin(t)
 if kind==5 or kind==10: drive=-g*np.sin(t)*(1+p[5]*np.cos(t))+a*u
 if kind==6: drive=a*p[5]*np.tanh(u/p[5])-g*np.sin(t)
 if kind==3: b=b*np.exp(p[5]*np.cos(t))
 if kind==7 or kind==11: c=c*np.exp(p[5]*np.cos(t))
 if kind>=9:
  return drive-b*w-min(max(drive+v*w,-c),c)
 h=np.tanh(w/v)
 if kind==8: h=w/np.sqrt(w*w+v*v)
 fr=c*h
 if kind==4: fr=fr*(1+p[5]*h)
 if kind==2: fr=(c+p[5]*np.exp(-(w/p[6])**2))*h
 if kind==0: return drive-b*w-fr
 cs=c
 if kind==2: cs=c+p[5]
 clipped=min(max(drive,-cs),cs)
 return drive-b*w-fr-(1-h*h)*clipped

@njit(cache=True)
def simulate(p,kind,starts,lens,U):
 n,m=U.shape; yy=np.zeros((n,m)); ww=np.zeros((n,m))
 for i in range(n):
  t,w=starts[i]; yy[i,0]=t;ww[i,0]=w
  for j in range(lens[i]-1):
   u=U[i,j]
   k1=accel(t,w,u,p,kind)
   t2=t+.005*w;w2=w+.005*k1;k2=accel(t2,w2,u,p,kind)
   t3=t+.005*w2;w3=w+.005*k2;k3=accel(t3,w3,u,p,kind)
   t4=t+.01*w3;w4=w+.01*k3;k4=accel(t4,w4,u,p,kind)
   t=t+.01*(w+2*w2+2*w3+w4)/6
   w=w+.01*(k1+2*k2+2*k3+k4)/6
   yy[i,j+1]=t;ww[i,j+1]=w
 return yy,ww

def residual(p,kind,data,balanced=False):
 s,l,u,y,w=data; yy,ww=simulate(p,kind,s,l,u)
 return np.concatenate([(yy[i,1:l[i]]-y[i,1:l[i]])/(np.sqrt(l[i]-1) if balanced else 1) for i in range(len(l))])
def score(p,kind,data):
 s,l,u,y,w=data; yy,ww=simulate(p,kind,s,l,u)
 return {'rmse':float(np.sqrt(np.mean(residual(p,kind,data)**2))), 'traj_rmse':[float(np.sqrt(np.mean((yy[i,1:l[i]]-y[i,1:l[i]])**2))) for i in range(len(l))], 'end_errors':[float(yy[i,l[i]-1]-y[i,l[i]-1]) for i in range(len(l))]}

bounds={0:([5,30,.05,2,.12],[60,180,8,45,2]),1:([5,30,.05,2,.12],[60,180,8,45,2]),2:([5,30,.05,2,.12,0,.2],[60,180,8,45,2,25,8]),3:([5,30,.05,2,.12,-1.5],[60,180,8,45,2,1.5]),4:([5,30,.05,2,.12,-.6],[60,180,8,45,2,.6]),5:([5,30,.05,2,.12,-.8],[60,180,8,45,2,.8]),6:([5,30,.05,2,.12,1],[60,180,8,45,2,30]),7:([5,30,.05,2,.12,-1.5],[60,180,8,45,2,1.5])}

def fit(kind,p0,data=train,max_nfev=250,balanced=False):
 return least_squares(residual,p0,args=(kind,data,balanced),bounds=bounds[kind],x_scale='jac',diff_step=1e-4,max_nfev=max_nfev,ftol=1e-8,xtol=1e-8,gtol=1e-8)


bounds[8]=bounds[1]
bounds[9]=([5,30,.05,2,15],[60,180,8,45,220])
bounds[10]=(bounds[9][0]+[-.8],bounds[9][1]+[.8])
bounds[11]=(bounds[9][0]+[-1.5],bounds[9][1]+[1.5])
