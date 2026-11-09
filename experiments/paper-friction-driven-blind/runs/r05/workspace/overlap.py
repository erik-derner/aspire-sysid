import pandas as pd,numpy as np
D=pd.read_csv('data/train.csv');V=pd.read_csv('data/val.csv')
for k,g in D.groupby('trajectory'):
 if k<8:continue
 for split,d in [('train',D),('val',V)]:
  for j,h in d.groupby('trajectory'):
   if split=='train' and j>=8:continue
   for i in np.where(abs(h.y.values-g.y.iloc[0])<1e-10)[0]:
    n=min(len(g),len(h)-i);e=np.max(abs(h.iloc[i:i+n][['y','x1']].values-g.iloc[:n][['y','x1']].values))
    if e<1e-10:print('train',k,'matches',split,j,'from row',i,'length',n)
