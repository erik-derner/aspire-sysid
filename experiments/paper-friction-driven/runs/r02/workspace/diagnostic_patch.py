p='diagnostic_analysis.py'
s=open(p).read().replace('np.diff(u[sl])!=0','np.abs(np.diff(u[sl]))>0.5').replace('samples within 0.02 s of an input change excluded','samples within 0.02 s of an input increment exceeding 0.5 V excluded (the logged input is continuously varying, so exact inequality would incorrectly discard nearly all driven samples)').replace('sample count, voltage levels (V), moving count','sample count, voltage range (V), unique voltage count, moving count').replace('voltage levels {sorted(g.u.unique().tolist())} V','voltage range [{g.u.min():.6g}, {g.u.max():.6g}] V; {g.u.nunique()} unique values')
a=s.index('for val in sorted(np.unique(u)):');b=s.index('for lo,hi in [(-3.15',a)
s=s[:a]+'''for lo,hi in [(-10,-5),(-5,-2),(-2,-.5),(-.5,.5),(.5,2),(2,5),(5,10.01)]:
 m=move&(u>=lo)&(u<hi)
 if m.sum():out(f'`{lo} <= u < {hi}` V: '+metrics(res,m))
'''+s[b:]
open(p,'w').write(s)
