import struct,time,json,sys
f=open(sys.argv[1],'rb');o=open(sys.argv[2],'w')
while True:
    d=f.read(24)
    if len(d)<24: break
    s,us,typ,code,val=struct.unpack('llHHi',d)
    o.write(json.dumps({'rt':time.time(),'mt':time.monotonic(),'ev':s+us/1e6,'type':typ,'code':code,'val':val})+'\n');o.flush()
