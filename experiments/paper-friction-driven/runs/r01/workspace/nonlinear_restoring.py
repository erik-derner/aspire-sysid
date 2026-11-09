from joint_fit import *
s=open('extended_identify.py').read().replace('if kind>=9:', 'if kind in (9,10,11):')
s=s.replace('if kind==5 or kind==10:', 'if kind in (5,10,13):')
s=s.replace('if kind==6: drive=', 'if kind in (12,13): drive=a*u-(a*u-drive)*np.exp(p[5 if kind==12 else 6]*np.sin(t))\n if kind==6: drive=')
s += '\nbounds[12]=(bounds[1][0]+[-.8],bounds[1][1]+[.8])\nbounds[13]=(bounds[5][0]+[-.8],bounds[5][1]+[.8])\n'
open('restoring_identify.py','w').write(s)
