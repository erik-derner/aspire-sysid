import pandas as pd,numpy as np
from identify import train,val
for lab,d in [('train',train),('val',val)]:
 ix=np.where(abs(d[:-1,3]-np.diff(d[:,0])/5)>.00001)[0];print(lab,ix)
 print(pd.DataFrame(d,columns=['p','valve','flow','dp']).iloc[np.unique(np.clip(np.r_[ix-1,ix,ix+1,ix+2],0,len(d)-1))].to_string())
