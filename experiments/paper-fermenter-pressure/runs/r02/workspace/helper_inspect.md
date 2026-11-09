
train (1452, 4) columns ['p', 'valve', 'flow', 'dp']
                 p        valve         flow           dp
count  1452.000000  1452.000000  1452.000000  1452.000000
mean      1.298163    64.577523    17.903418     0.000036
std       0.260879    18.177046     6.833631     0.006076
min       0.992309    10.307583     0.097345    -0.020900
25%       1.093695    57.980696    12.932027    -0.003375
50%       1.229201    69.451447    18.331697    -0.000049
75%       1.427059    76.736809    23.742245     0.003296
max       2.186718    92.411713    30.796778     0.023952
dp comparison lag -3: RMSE 0.00658873713 bar/s corr 0.412124937
dp comparison lag -2: RMSE 0.00599327536 bar/s corr 0.5135968
dp comparison lag -1: RMSE 0.0037987792 bar/s corr 0.804684432
dp comparison lag 0: RMSE 0.000221132141 bar/s corr 0.999338593
dp comparison lag 1: RMSE 0.00381450357 bar/s corr 0.802927969
dp comparison lag 2: RMSE 0.00601038144 bar/s corr 0.510526135
dp comparison lag 3: RMSE 0.00660252833 bar/s corr 0.409488247
valve changes 1451 unique 1452 largest changes [np.float64(25.833728790283203), np.float64(8.206916809082038), np.float64(8.165142059326186), np.float64(8.05740737915039), np.float64(7.941410064697266), np.float64(7.9198455810546875), np.float64(7.895263671875), np.float64(7.8329925537109375), np.float64(7.786003112792969), np.float64(7.754917144775391)]
flow changes 1451 unique 1444 largest changes [np.float64(22.11331231147051), np.float64(18.795897461473942), np.float64(9.500238008797169), np.float64(4.568394124507904), np.float64(3.7278881072998047), np.float64(3.344881057739265), np.float64(3.344222903251648), np.float64(3.328620910644535), np.float64(3.3198318481445312), np.float64(3.272148132324215)]

val (1454, 4) columns ['p', 'valve', 'flow', 'dp']
                 p        valve         flow           dp
count  1454.000000  1454.000000  1454.000000  1454.000000
mean      1.306319    63.036614    18.115842     0.000049
std       0.262661    20.452928     5.683909     0.005129
min       0.994018     1.628053     0.083062    -0.019630
25%       1.099005    50.743231    14.566727    -0.002539
50%       1.241104    69.200447    19.234609     0.000000
75%       1.441433    78.820923    22.523403     0.002393
max       2.144479    94.448708    29.071159     0.023708
dp comparison lag -3: RMSE 0.00589249495 bar/s corr 0.340771294
dp comparison lag -2: RMSE 0.0064469616 bar/s corr 0.210820051
dp comparison lag -1: RMSE 0.00433496119 bar/s corr 0.643415712
dp comparison lag 0: RMSE 0.000335633453 bar/s corr 0.997865701
dp comparison lag 1: RMSE 0.00436038515 bar/s corr 0.638990556
dp comparison lag 2: RMSE 0.00646799477 bar/s corr 0.205165672
dp comparison lag 3: RMSE 0.00590571125 bar/s corr 0.337521511
valve changes 1453 unique 1454 largest changes [np.float64(26.86311340332032), np.float64(7.755367279052734), np.float64(7.750663757324219), np.float64(7.721366882324219), np.float64(7.515584945678711), np.float64(7.412391662597656), np.float64(7.28367805480957), np.float64(7.268871307373047), np.float64(7.268863677978516), np.float64(7.2625885009765625)]
flow changes 1453 unique 1446 largest changes [np.float64(21.175900921225544), np.float64(17.947262689471245), np.float64(12.628236278891563), np.float64(3.3569679260253906), np.float64(3.3332347869873047), np.float64(3.3248863220214844), np.float64(3.262258529663086), np.float64(3.2569847106933594), np.float64(3.248197555541992), np.float64(3.223804950714112)]

power current parameters a,b,n,m [0.00111222 0.13745884 0.89779872 0.58912492]
train derivative RMSE 0.00272589913 bar/s change 0.00272589913 unchanged nan bias 0.000227655219 bar/s
train rollout RMSE 0.0431408326 bar
residual pressure bins {'mean': {Interval(0.991, 1.231, closed='right'): 0.0005238601123214609, Interval(1.231, 1.47, closed='right'): 0.0004801500886151593, Interval(1.47, 1.709, closed='right'): -0.0003251600718038368, Interval(1.709, 1.948, closed='right'): -0.0015711795551839323, Interval(1.948, 2.187, closed='right'): -0.0008098874371852789}, 'std': {Interval(0.991, 1.231, closed='right'): 0.002584083311789177, Interval(1.231, 1.47, closed='right'): 0.0024974106714844148, Interval(1.47, 1.709, closed='right'): 0.00312338332349283, Interval(1.709, 1.948, closed='right'): 0.002939946821032635, Interval(1.948, 2.187, closed='right'): 0.0026763661991988934}}
residual valve bins {'mean': {Interval(10.225, 26.728, closed='right'): -0.000842375171618662, Interval(26.728, 43.149, closed='right'): 0.000446288134228724, Interval(43.149, 59.57, closed='right'): 0.001258517366894885, Interval(59.57, 75.991, closed='right'): 0.0009365580054249057, Interval(75.991, 92.412, closed='right'): -0.0012049333223274512}, 'std': {Interval(10.225, 26.728, closed='right'): 0.004102634679742011, Interval(26.728, 43.149, closed='right'): 0.002499673180029039, Interval(43.149, 59.57, closed='right'): 0.0019173088050880541, Interval(59.57, 75.991, closed='right'): 0.0021257033901628235, Interval(75.991, 92.412, closed='right'): 0.0028546034393756624}}
val derivative RMSE 0.00249279036 bar/s change 0.00249279036 unchanged nan bias -0.000221593586 bar/s
val rollout RMSE 0.0507720666 bar
residual pressure bins {'mean': {Interval(0.993, 1.224, closed='right'): -1.0140497105131582e-05, Interval(1.224, 1.454, closed='right'): 0.00030139166886512456, Interval(1.454, 1.684, closed='right'): -0.0007306857656547069, Interval(1.684, 1.914, closed='right'): -0.0014613819831964133, Interval(1.914, 2.144, closed='right'): -0.0023799538819314}, 'std': {Interval(0.993, 1.224, closed='right'): 0.002632001173984584, Interval(1.224, 1.454, closed='right'): 0.0019211093957014213, Interval(1.454, 1.684, closed='right'): 0.0025104902145535756, Interval(1.684, 1.914, closed='right'): 0.00214805942167447, Interval(1.914, 2.144, closed='right'): 0.0027359330190111584}}
residual valve bins {'mean': {Interval(1.535, 20.192, closed='right'): -0.002581040391938575, Interval(20.192, 38.756, closed='right'): -0.0012299154040561154, Interval(38.756, 57.32, closed='right'): 0.0003588535101106917, Interval(57.32, 75.885, closed='right'): 0.0009841269882378862, Interval(75.885, 94.449, closed='right'): -0.0010114425814524805}, 'std': {Interval(1.535, 20.192, closed='right'): 0.003484160416767328, Interval(20.192, 38.756, closed='right'): 0.002496259939237384, Interval(38.756, 57.32, closed='right'): 0.0024465314217108824, Interval(57.32, 75.885, closed='right'): 0.0015293134779961093, Interval(75.885, 94.449, closed='right'): 0.0024547838505608126}}

power next parameters a,b,n,m [9.05023528e-04 1.10085859e-01 9.06709689e-01 5.78255141e-01]
train derivative RMSE 0.00313126369 bar/s change 0.00313126369 unchanged nan bias 0.00027457165 bar/s
val derivative RMSE 0.003489407 bar/s change 0.003489407 unchanged nan bias -0.000114183576 bar/s

power average parameters a,b,n,m [0.00108635 0.12967065 0.88863619 0.5751631 ]
train derivative RMSE 0.00257380229 bar/s change 0.00257380229 unchanged nan bias 0.000273917164 bar/s
val derivative RMSE 0.00271478178 bar/s change 0.00271478178 unchanged nan bias -0.000183333404 bar/s

exponential current parameters a,b,n,m [1.01184082e-03 3.10362736e+00 5.00000000e-02 6.37903378e-01]
train derivative RMSE 0.00279800643 bar/s change 0.00279800643 unchanged nan bias 0.000329666168 bar/s
train rollout RMSE 0.0437521359 bar
residual pressure bins {'mean': {Interval(0.991, 1.231, closed='right'): 0.0006353958584088843, Interval(1.231, 1.47, closed='right'): 0.000600472081216214, Interval(1.47, 1.709, closed='right'): -0.0002541278118495467, Interval(1.709, 1.948, closed='right'): -0.0015813468399563488, Interval(1.948, 2.187, closed='right'): -0.0006540695464775001}, 'std': {Interval(0.991, 1.231, closed='right'): 0.002726870616023026, Interval(1.231, 1.47, closed='right'): 0.00245351987139739, Interval(1.47, 1.709, closed='right'): 0.003136153724483256, Interval(1.709, 1.948, closed='right'): 0.0028878307596185908, Interval(1.948, 2.187, closed='right'): 0.0026509751515884803}}
residual valve bins {'mean': {Interval(10.225, 26.728, closed='right'): -0.0014388174814438754, Interval(26.728, 43.149, closed='right'): 0.00014074773592845033, Interval(43.149, 59.57, closed='right'): 0.0012626648220198154, Interval(59.57, 75.991, closed='right'): 0.0010992527573926566, Interval(75.991, 92.412, closed='right'): -0.0008693376399066826}, 'std': {Interval(10.225, 26.728, closed='right'): 0.004315889926488205, Interval(26.728, 43.149, closed='right'): 0.0026307100742406267, Interval(43.149, 59.57, closed='right'): 0.0019433078461249611, Interval(59.57, 75.991, closed='right'): 0.002159326558343606, Interval(75.991, 92.412, closed='right'): 0.0029251034002581834}}
val derivative RMSE 0.00260268063 bar/s change 0.00260268063 unchanged nan bias -8.17508086e-05 bar/s
val rollout RMSE 0.0469497286 bar
residual pressure bins {'mean': {Interval(0.993, 1.224, closed='right'): 3.873753023294928e-06, Interval(1.224, 1.454, closed='right'): 0.0004200912360484821, Interval(1.454, 1.684, closed='right'): -0.00036551622844063466, Interval(1.684, 1.914, closed='right'): -0.0010310079691089643, Interval(1.914, 2.144, closed='right'): -0.0018770862683234967}, 'std': {Interval(0.993, 1.224, closed='right'): 0.002906388602271673, Interval(1.224, 1.454, closed='right'): 0.001968047121668588, Interval(1.454, 1.684, closed='right'): 0.0025029462082456705, Interval(1.684, 1.914, closed='right'): 0.002111950888835467, Interval(1.914, 2.144, closed='right'): 0.002771898559057484}}
residual valve bins {'mean': {Interval(1.535, 20.192, closed='right'): -0.0030009619977195076, Interval(20.192, 38.756, closed='right'): -0.0015314109641359648, Interval(38.756, 57.32, closed='right'): 0.0001761263326496678, Interval(57.32, 75.885, closed='right'): 0.0011639275438052013, Interval(75.885, 94.449, closed='right'): -0.0005635578567714014}, 'std': {Interval(1.535, 20.192, closed='right'): 0.00390441060932134, Interval(20.192, 38.756, closed='right'): 0.0028106222564419797, Interval(38.756, 57.32, closed='right'): 0.00258096114370036, Interval(57.32, 75.885, closed='right'): 0.001528303623161667, Interval(75.885, 94.449, closed='right'): 0.002488071013833236}}

exponential next parameters a,b,n,m [8.40263725e-04 2.48948581e+00 5.00000000e-02 6.21438535e-01]
train derivative RMSE 0.00317151396 bar/s change 0.00317151396 unchanged nan bias 0.000356176949 bar/s
val derivative RMSE 0.00357105903 bar/s change 0.00357105903 unchanged nan bias -1.16447159e-05 bar/s

exponential average parameters a,b,n,m [9.85583999e-04 2.95718733e+00 5.00000000e-02 6.26459726e-01]
train derivative RMSE 0.00265887543 bar/s change 0.00265887543 unchanged nan bias 0.000380890858 bar/s
val derivative RMSE 0.00285302106 bar/s change 0.00285302106 unchanged nan bias -3.89936017e-05 bar/s