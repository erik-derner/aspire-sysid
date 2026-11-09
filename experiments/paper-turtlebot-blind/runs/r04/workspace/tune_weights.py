exec(open('refine.py').read().split('\nR={}\n')[0])
R={}
for f in ['smoothyaw','deadwheel','smoothwheel']:
 for weight in [4,12,16,24,40]:
  p,p0,lag,loss=fit2(f,[0,1,2],weight);cv=[];train=[]
  for i in range(3):
   pp,_,_,_=fit2(f,[j for j in range(3) if j!=i],weight);ss=sim2(pp,f,i);cv.append(np.sqrt(np.mean((ss[1:,0]-G[i][1:,0])**2)))
   ss=sim2(p,f,i);train.append(np.sqrt(np.mean((ss[1:,0]-G[i][1:,0])**2)))
  key=f+'_'+str(weight);R[key]={'p':p.tolist(),'cv':cv,'train':train};print(key,'p',np.round(p,6),'train',np.round(train,4),'cv',np.round(cv,4),'pooled',np.sqrt(np.mean(np.array(cv)**2)),flush=True)
json.dump(R,open('select_results.json','w'),indent=2)
