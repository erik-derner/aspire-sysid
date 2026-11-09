from pathlib import Path
p=Path('fit_models.py');s=p.read_text();s=s.replace(' return 0.\n',''' if fam==16: # angle-dependent projected Stribeck friction
  k,hs,hc,ds,vs=p[4:9];ct=c*(1+hs*np.sin(t)+hc*np.cos(t))+ds*np.exp(-(w/vs)**2)
  return f-b*w-min(max(f+k*w,-ct),ct)
 if fam==17: # static friction no smaller than kinetic
  k,hs,hc,ds,v=p[4:9];ct=c*(1+hs*np.sin(t)+hc*np.cos(t));h=np.exp(-(w/v)**2);fs=ct*(1+ds)
  z=max(f-fs,0)+min(f+fs,0)
  return h*z+(1-h)*(f-ct*np.tanh(w/v))-b*w-k*h*w
 if fam==18: # asymmetric projection with extra restoring harmonic
  k,hs,hc,asym,hg=p[4:9];ct=c*(1+hs*np.sin(t)+hc*np.cos(t));f=a*u-g*np.sin(t)*(1+hg*np.cos(t))
  return f-b*w-min(max(f+k*w,-ct*(1-asym)),ct*(1+asym))
 return 0.
''')
s=s.replace("60,10,200,60,220,.65,.65,2,5])}","""60,10,200,60,220,.65,.65,2,5]),
 'angle_stribeck':(16,[29,1.8,115,28,150,-.2,-.3,3,1],[1,0,20,0,3,-.65,-.65,0,.2],[60,10,200,60,240,.65,.65,40,15]),
 'physical_blend':(17,[29,1.8,115,28,80,-.2,-.3,.1,.5],[1,0,20,0,3,-.65,-.65,0,.12],[60,10,200,60,220,.65,.65,1,5]),
 'asym_harmonic':(18,[29,1.8,115,28,150,-.2,-.3,-.1,0],[1,0,20,0,3,-.65,-.65,-.8,-.95],[60,10,200,60,240,.65,.65,.8,.95])}""")
p.write_text(s)
