from pathlib import Path
p=Path('fit_models.py');s=p.read_text();s=s.replace(' return 0.\n',''' if fam in [9,10,11,12,13,14,15]:
  k,hs,hc=p[4:7];ct=c*(1+hs*np.sin(t)+hc*np.cos(t))
  if fam==9:
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==10:
   return f-b*w-ct*np.tanh(w/k)
  if fam==11:
   f=a*u*(1+p[7]*u*u)-g*np.sin(t)
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==12:
   f=a*u-g*np.sin(t)*(1+p[7]*np.cos(t))
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==13:
   asym=p[7]
   return f-b*w-min(max(f+k*w,-ct*(1-asym)),ct*(1+asym))
  if fam==14:
   f=a*u-g*np.sin(t)*(1+p[7]*np.sin(t))
   return f-b*w-min(max(f+k*w,-ct),ct)
  if fam==15:
   fs,v=p[7:9];h=np.exp(-(w/v)**2)
   z=max(f-fs*ct,0)+min(f+fs*ct,0)
   return h*z+(1-h)*(f-ct*np.tanh(w/v))-b*w-k*h*w
 return 0.
''')
s=s.replace(" 'cubic_input':(8,", " 'cubic_input':(8,")
s=s.replace("60,10,200,60,240,.1])}","""60,10,200,60,240,.1]),
 'angle_friction':(9,[26.46,1.6,110.2,24.56,80,-.30,-.30],[1,0,20,0,3,-.65,-.65],[60,10,200,60,240,.65,.65]),
 'angle_smooth':(10,[26.46,1.6,110.2,24.56,.2,-.30,-.30],[1,0,20,0,.12,-.65,-.65],[60,10,200,60,5,.65,.65]),
 'angle_cubic':(11,[26.46,1.6,110.2,24.56,80,-.30,-.30,.004],[1,0,20,0,3,-.65,-.65,0],[60,10,200,60,240,.65,.65,.1]),
 'angle_harmonic':(12,[26.46,1.6,110.2,24.56,80,-.30,-.30,0],[1,0,20,0,3,-.65,-.65,-.95],[60,10,200,60,240,.65,.65,.95]),
 'angle_asym':(13,[26.46,1.6,110.2,24.56,80,-.30,-.30,0],[1,0,20,0,3,-.65,-.65,-.8],[60,10,200,60,240,.65,.65,.8]),
 'angle_singrav':(14,[26.46,1.6,110.2,24.56,80,-.30,-.30,0],[1,0,20,0,3,-.65,-.65,-.95],[60,10,200,60,240,.65,.65,.95]),
 'angle_blend':(15,[26.46,1.6,110.2,24.56,80,-.30,-.30,1,.5],[1,0,20,0,3,-.65,-.65,.5,.12],[60,10,200,60,220,.65,.65,2,5])}""")
s=s.replace("results={};", "results=json.load(open('fit_results.json')) if os.path.exists('fit_results.json') else {};")
s=s.replace("  def resid(p):", "  if name in results:continue\n  def resid(p):")
s=s.replace("if fam not in [0,2]:", "if fam not in [0,2,10]:")
p.write_text(s)
