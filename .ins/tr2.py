import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
for t in b.GetTracks():
    if t.GetLayerName()=='B.Cu' or type(t).__name__=='PCB_VIA':
        s,f=t.GetStart(),t.GetEnd()
        xs=[s.x/1e6-100,f.x/1e6-100]; ys=[100-s.y/1e6,100-f.y/1e6]
        if max(ys)>-31 and min(ys)<-27 and max(xs)>-3 and min(xs)<19:
            print(t.GetNetname(),type(t).__name__,[round(v,2) for v in xs],[round(v,2) for v in ys])
for z in b.Zones():
    print('zone',z.GetNetname(),z.GetLayerName())
