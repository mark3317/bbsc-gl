"""Subset of protobuf wire types used by shadNet's private Matching2 API.
Schema is generated from the vendored .proto; unknown fields are skipped.
"""
import json
from pathlib import Path
SCHEMA=json.loads((Path(__file__).with_name('schema.json')).read_text())
NUMBERS={'uint32','uint64','int32','int64','bool','MatchingUserIdKind'}
def varint(n):
    n=int(n)&((1<<64)-1); out=bytearray()
    while n>127: out.append((n&127)|128); n>>=7
    out.append(n); return bytes(out)
def readvar(raw,at):
    n=0
    for shift in range(0,70,7):
        if at>=len(raw): raise ValueError('Short varint')
        b=raw[at]; at+=1; n|=(b&127)<<shift
        if b<128: return n,at
    raise ValueError('Long varint')
def encode(name,obj):
    out=bytearray()
    for num,key,typ,repeated in SCHEMA[name]:
        if key not in obj: continue
        values=obj[key] if repeated else [obj[key]]
        for value in values:
            if typ in NUMBERS: out.extend(varint(num<<3)+varint(value))
            else:
                raw=value.encode() if typ=='string' else value if typ=='bytes' else encode(typ,value)
                out.extend(varint((num<<3)|2)+varint(len(raw))+raw)
    return bytes(out)
def decode(name,raw):
    fields={f[0]:f[1:] for f in SCHEMA[name]}; out={}; at=0
    while at<len(raw):
        tag,at=readvar(raw,at); num,wire=tag>>3,tag&7
        if wire==0: value,at=readvar(raw,at)
        elif wire==2:
            size,at=readvar(raw,at)
            if size>len(raw)-at: raise ValueError('Short protobuf field')
            value=raw[at:at+size]; at+=size
        elif wire in (1,5): at+=8 if wire==1 else 4; continue
        else: raise ValueError('Unsupported wire type')
        if num not in fields: continue
        key,typ,repeated=fields[num]
        if wire==2:
            if typ=='string': value=value.decode()
            elif typ!='bytes':
                if typ in NUMBERS:
                    pos=0; vals=[]
                    while pos<len(value): v,pos=readvar(value,pos); vals.append(v)
                    out.setdefault(key,[]).extend(vals); continue
                value=decode(typ,value)
        if repeated: out.setdefault(key,[]).append(value)
        else: out[key]=value
    return out
