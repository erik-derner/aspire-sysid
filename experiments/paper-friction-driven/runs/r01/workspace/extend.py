import json,time
import numpy as np
from identify import *
# Extend accel by generating a separate file retaining complete reproducibility.
s=open('identify.py').read()
s=s.replace('if kind==5: drive=', 'if kind==5 or kind==10: drive=')
s=s.replace('if kind==7: c=', 'if kind==7 or kind==11: c=')
s=s.replace('h=np.tanh(w/v)', '''if kind>=9:
  return drive-b*w-min(max(drive+v*w,-c),c)
 h=np.tanh(w/v)
 if kind==8: h=w/np.sqrt(w*w+v*v)''')
s=s[:s.index("if __name__=='__main__':")]
s += '''\nbounds[8]=bounds[1]
bounds[9]=([5,30,.05,2,15],[60,180,8,45,220])
bounds[10]=(bounds[9][0]+[-.8],bounds[9][1]+[.8])
bounds[11]=(bounds[9][0]+[-1.5],bounds[9][1]+[1.5])
'''
open('extended_identify.py','w').write(s)
