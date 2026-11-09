from pathlib import Path
s=Path('fit_models.py').read_text().replace(' return 0.\n',''' if fam==19: # equal static and kinetic friction, smooth blend
  k,hs,hc,v=p[4:8];ct=c*(1+hs*np.sin(t)+hc*np.cos(t));h=np.exp(-(w/v)**2)
  z=max(f-ct,0)+min(f+ct,0)
  return h*z+(1-h)*(f-ct*np.tanh(w/v))-b*w-k*h*w
 if fam==20: # identified Stribeck asymptote was zero; remove it
  v,vs=p[4:6]
  return f-b*w-c*np.exp(-(w/vs)**2)*np.tanh(w/v)
 return 0.
''').replace("60,10,200,60,240,.65,.65,.8,.95])}","""60,10,200,60,240,.65,.65,.8,.95]),
 'equal_blend':(19,[29.13,1.71,115.33,28.82,14.28,-.19,-.29,.435],[1,0,20,0,3,-.65,-.65,.12],[60,10,200,60,220,.65,.65,5]),
 'speed_weakening':(20,[28.46,3.056,111.67,19.95,.12,9.48],[1,0,20,0,.12,.2],[60,10,200,60,5,15])}""")
Path('fit_models.py').write_text(s)
