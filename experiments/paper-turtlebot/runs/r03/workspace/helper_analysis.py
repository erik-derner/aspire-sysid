"""Training-only diagnostic fits. No candidate models are written."""
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

D=pd.read_csv('data/train.csv')
Ts=.2
rows=[]; blocks=[]
for tr,g in D.groupby('trajectory'):
    g=g.reset_index(drop=True)
    ph=np.unwrap(g.phi.to_numpy()); x=g.x.to_numpy(); y=g.y.to_numpy()
    for k in range(len(g)-1):
        dp=ph[k+1]-ph[k]; mid=(ph[k+1]+ph[k])/2
        dx=x[k+1]-x[k]; dy=y[k+1]-y[k]
        sf=(dx*np.cos(mid)+dy*np.sin(mid))/Ts
        sl=(-dx*np.sin(mid)+dy*np.cos(mid))/Ts
        rows.append(dict(tr=tr,k=k,phase=k%5,block=k//5,u=g.v_f[k],w=g.v_a[k],up=g.v_f[max(0,k-5)],wp=g.v_a[max(0,k-5)],a=dp/Ts,f=sf,l=sl,dx=dx,dy=dy,ph=ph[k],dp=dp))
    for b in range(30):
        s=b*5
        if s+5>=len(g):continue
        for start in [0,1,2]:
            e=s+5; t=(5-start)*Ts; q=s+start
            dx=x[e]-x[q];dy=y[e]-y[q];mid=(ph[e]+ph[q])/2;dp=ph[e]-ph[q]
            sinc=np.sinc(dp/(2*np.pi))
            blocks.append(dict(tr=tr,b=b,start=start,u=g.v_f[s],w=g.v_a[s],up=g.v_f[max(0,s-5)],wp=g.v_a[max(0,s-5)],a=dp/t,f=(dx*np.cos(mid)+dy*np.sin(mid))/t/sinc,l=(-dx*np.sin(mid)+dy*np.cos(mid))/t/sinc))
R=pd.DataFrame(rows);B=pd.DataFrame(blocks)
text=[]
def say(s=''):text.append(str(s));print(s)
def Xframe(F,names):
    maps={'1':np.ones(len(F)),'u':F.u,'w':F.w,'wabs':F.w.abs(),'w3':F.w**3,'wabsw':F.w*F.w.abs(),'uw':F.u*F.w,'u2w':F.u**2*F.w,'w2':F.w**2,'uw2':F.u*F.w**2,'up':F.up,'wp':F.wp,'signw':np.sign(F.w),'u2':F.u**2,'uabsw':F.u*F.w.abs()}
    return np.column_stack([np.array(maps[n]) for n in names])
def linfit(F,target,names,label):
    X=Xframe(F,names);y=np.array(F[target]);coef=np.linalg.lstsq(X,y,rcond=None)[0];pred=X@coef
    errs=[];cs=[]
    for tr in sorted(F.tr.unique()):
        test=F.tr==tr;
        if np.sum(~test)==0: continue
        c=np.linalg.lstsq(X[~test],y[~test],rcond=None)[0];errs.extend(y[test]-X[test]@c);cs.append(c)
    mse=np.sum((y-pred)**2)/(len(y)-len(coef));se=np.sqrt(np.diag(np.linalg.pinv(X.T@X))*mse)
    say(f'{label}: n={len(F)}; target={target}; columns={names}; coeff={coef.tolist()}; SE={se.tolist()}; train rate RMSE={np.sqrt(np.mean((y-pred)**2)):.8f}; leave-one-trajectory-out rate RMSE={(np.sqrt(np.mean(np.array(errs)**2)) if errs else float("nan")):.8f}; per-trajectory coef={np.array(cs).tolist()}')
    return coef,y-pred
say('Only data/train.csv accessed. Ts=0.2 s. All coefficient diagnostics are ordinary least squares via numpy.linalg.lstsq; no starting values, randomness, or seeds. SE is conventional OLS conditional standard error, not robust to dependence. CV is leave-one-trajectory-out, fit two trajectories and predict third. Angular rates rad/s; forward and lateral rates m/s; corresponding RMSE is root mean squared observed-minus-predicted rate. Rate sample is pose difference divided by elapsed time. Forward/lateral projected at endpoint midpoint heading; block forward corrected by sinc(heading-change/2) to remove constant-curvature chord shortening.')
say('Training input ranges: '+str(D[['v_f','v_a']].agg(['min','max']).to_dict()))
for phase in range(5):
    F=R[R.phase==phase]
    linfit(F,'a',['1','w','wp','uw'],f'angular phase {phase}')
    linfit(F,'f',['1','u','up','uw2'],f'forward phase {phase}')
for start in [0,1,2]:
    F=B[B.start==start]
    say(f'\nBLOCK start-phase={start}; average duration={(5-start)*Ts:.2f} s; n={len(F)}')
    for target,names in [('a',['1','w']),('a',['1','w','uw']),('a',['1','w','w3']),('a',['1','w','wabsw']),('a',['1','w','w3','uw']),('a',['1','w','w3','uw','u2w']),('a',['1','w','w3','uw','wp']),('a',['1','w','w3','uw','u']),('a',['1','w','w3','uw','wabs']),('f',['1','u']),('f',['1','u','w']),('f',['1','u','uw2']),('f',['1','u','u2']),('f',['1','u','uabsw']),('f',['1','u','w2','uw2']),('l',['1']),('l',['1','u','w','uw'])]:
        linfit(F,target,names,f'{target} block')
F=B[B.start==1].copy()
# Fit angular deadband/saturation forms: yaw = b + gain(u)*max(|w|-deadband,0)*sign(w); tanh form.
def dead(p,F):
    return p[0]+(p[1]+p[2]*F.u.to_numpy())*np.sign(F.w.to_numpy())*np.maximum(np.abs(F.w.to_numpy())-p[3],0)
def sat(p,F):
    return p[0]+(p[1]+p[2]*F.u.to_numpy())*np.tanh(p[3]*F.w.to_numpy())
for label,fun,init,bounds in [('deadband',dead,[0,.7,0,.01],([-1,0,-5,0],[1,3,5,.5])),('tanh',sat,[0,.6,0,1.5],([-1,0,-5,.01],[1,3,5,10]))]:
    fit=least_squares(lambda p:fun(p,F)-F.a.to_numpy(),init,bounds=bounds,max_nfev=10000)
    err=fun(fit.x,F)-F.a.to_numpy();cv=[]
    for tr in [1,2,3]:
        train=F[F.tr!=tr];test=F[F.tr==tr];f=least_squares(lambda p:fun(p,train)-train.a.to_numpy(),init,bounds=bounds,max_nfev=10000);cv.extend(fun(f.x,test)-test.a.to_numpy())
    say(f'Nonlinear {label}: fitted scipy.optimize.least_squares with init={init}, bounds={bounds}, params={fit.x.tolist()}; training angular-rate RMSE={np.sqrt(np.mean(err**2)):.8f} rad/s; leave-trajectory-out angular-rate RMSE={np.sqrt(np.mean(np.array(cv)**2)):.8f} rad/s')
# Effects split by commands: estimate angular linear relation conditioned by speed, forward conditioned by turn.
say('\nSPEED/TURN SUBSETS, block phase1->5, duration0.8 s')
for low,high in [(0,.1),(.1,.2),(.2,.31)]:
    A=F[(F.u>=low)&(F.u<high)]
    linfit(A,'a',['1','w','w3'],f'speed subset [{low},{high}) m/s')
for low,high in [(0,.3),(.3,.6),(.6,1)]:
    A=F[(F.w.abs()>=low)&(F.w.abs()<high)]
    linfit(A,'f',['1','u'],f'turn subset abs in [{low},{high}) rad/s')
# Scalar lag blend for first transition, using effective steady response fit.
ca,_=linfit(F,'a',['1','w','w3','uw'],'baseline angular delayed response');cf,_=linfit(F,'f',['1','u','uw2'],'baseline forward delayed response')
for target,c,names in [('a',ca,['1','w','w3','uw']),('f',cf,['1','u','uw2'])]:
    now=Xframe(R,names)@c;prev=R.copy();prev.u=prev.up;prev.w=prev.wp;old=Xframe(prev,names)@c
    for phase in range(5):
        ix=(R.phase==phase)&(R.block>0);d=old[ix]-now[ix];e=R.loc[ix,target].to_numpy()-now[ix];alpha=(d@e)/(d@d);res=e-alpha*d
        say(f'Lag diagnostic {target}, phase={phase}, n={int(sum(ix))}: old-response blend={alpha:.8f} dimensionless; equivalent old-response time={alpha*Ts:.8f} s; unblended rate RMSE={np.sqrt(np.mean(e**2)):.8f}; blended rate RMSE={np.sqrt(np.mean(res**2)):.8f}')
say('\nLATERAL samples and apparent heading alignment')
for phase in range(5):
    A=R[R.phase==phase];say(f'phase={phase}, n={len(A)}, lateral mean={A.l.mean():.8f} m/s, lateral RMS={np.sqrt(np.mean(A.l**2)):.8f} m/s, forward mean={A.f.mean():.8f} m/s')
# Orientation transport innovation effect: phi is approximately directional orientation, but observed body lateral correlates angular rate.
for target in ['a','f']:
    say(f'FULL TRANSITIONS {target}')
    for names in ([['1','w'],['1','w','w3','uw']] if target=='a' else [['1','u'],['1','u','uw2']]):
        linfit(R,target,names,'all phases')
# Robustness: per-trajectory fits.
for tr in [1,2,3]:
    A=F[F.tr==tr];linfit(A,'a',['1','w','w3','uw'],f'trajectory={tr} angular');linfit(A,'f',['1','u','uw2'],f'trajectory={tr} forward')
open('helper_report.txt','w',encoding='utf-8').write('\n'.join(text)+'\n')
