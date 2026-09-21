import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
e=b.GetBoardEdgesBoundingBox(); cx=(e.GetLeft()+e.GetRight())/2e6; cy=(e.GetTop()+e.GetBottom())/2e6
print('centre',cx,cy)
for t in b.GetTracks():
    n=t.GetNetname()
    if n in sys.argv[2:]:
        s,f=t.GetStart(),t.GetEnd()
        print(n,t.GetLayerName(),type(t).__name__,round(s.x/1e6-cx,2),round(-(s.y/1e6-cy),2),'->',round(f.x/1e6-cx,2),round(-(f.y/1e6-cy),2))
