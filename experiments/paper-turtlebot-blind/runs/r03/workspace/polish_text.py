import json
from pathlib import Path
for label in ['Deadzone','Rational','Periodic']:
 path=Path('models')/(label+'.json');m=json.load(open(path)); soft=label=='Rational'; periodic=label=='Periodic'
 v='(speed_gain*x3 + speed_bias)'
 h='(turn_gain*x4**3/(x4**2 + turn_width**2) + turn_bias)' if soft else '(turn_gain*sign(x4)*Max(Abs(x4)-turn_width,0) + turn_bias)'
 if periodic:h='('+h+' + sine_bias*sin(x2) + cosine_bias*cos(x2))'
 direction='(x2 + direction_factor*'+h+' + direction_bias)'
 text='`y`, `x1`, `x2` are current states; `x3`, `x4` are current inputs; the suffix `_next` denotes the next sample. `'+v+'` is the common signed displacement magnitude per sample: `speed_gain` scales the input, while `speed_bias` adds input-independent drift. `'+h+'` is the angular increment: `turn_gain` scales the input response, `turn_width` sets its width, and `turn_bias` adds constant angular drift. `'+direction+'` is the displacement direction; `direction_factor` and `direction_bias` are empirical fitted adjustments, not known physical averaging constants. The coordinate updates are `'+m['expressions']['y_next']+'` and `'+m['expressions']['x1_next']+'`. The expression `'+m['expressions']['x2_next']+'` wraps the angular update.'
 if soft:text+=' The rational term `x4**3/(x4**2 + turn_width**2)` tends cubically to zero near the origin and approximately linearly far beyond the width; the strictly positive denominator avoids singularities.'
 else:text+=' The term `sign(x4)*Max(Abs(x4)-turn_width,0)` suppresses small inputs and is odd outside its central dead zone.'
 if periodic:text+=' The terms `sine_bias*sin(x2)` and `cosine_bias*cos(x2)` are bounded first-harmonic angular corrections; no physical mechanism is identified.'
 m['discussion']['interpretation']=text
 m['estimation']['criterion']=m['estimation']['criterion'].replace('using residuals','using residuals').replace('where `q0` is','where `v = speed_gain*x3 + speed_bias` is the predicted displacement magnitude, `h` denotes the input-only part of the stated angular increment, and `q0` is')
 json.dump(m,open(path,'w'),indent=2)
