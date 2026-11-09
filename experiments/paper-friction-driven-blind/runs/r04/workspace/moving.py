exec(open('explore.py').read().split('for names in families:')[0])
for cutoff in [0,.2,.5,1,2]:
 ok=np.abs(D.x1.to_numpy())>cutoff
 for names in [['sin','v','u','sign'],['sin','v','u','sign','one'],['y','y3','v','u','sign','one']]:
  A=np.stack([F[n] for n in names],1)
  p=np.linalg.lstsq(A[ok],D.dx1[ok],rcond=None)[0];err=D.dx1[ok]-A[ok]@p
  print(cutoff,names,p,np.sqrt(np.mean(err**2)))
