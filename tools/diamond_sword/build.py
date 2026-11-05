"""Build the standalone Diamond Sword overlay from the player's unmodified 1.09 files."""
import argparse
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(TOOLS / "gamedata"), str(TOOLS / "souls")]
import bbfiles
import param
import souls

BASE, SWORD, MODEL = 8100000, 42000000, 9800
GEM_DONOR = 8110000  # Uncanny Ludwig: radial, radial, triangle.
WANDERING_OFFSET = 90000
ICON = 1042
BATH_SHOPS = (100000, 110000, 120000, 130000, 140000)
SHOP_PRICE = 10000  # Optional sword: half the original Ludwig's Holy Blade price.


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def archive(path, update, rename=False):
    wrapped = path.read_bytes()
    original = souls.read_dcx(wrapped)
    count = u32(original, 12)
    assert original[32] == 36 and original[50] == 0
    output = bytearray(original[:struct.unpack_from("<Q", original, 40)[0]])
    for index, (fid, name, blob) in enumerate(souls.read_bnd4(original)):
        entry = 64 + 36 * index
        assert u32(original, entry + 8) == len(blob)
        blob = update(fid, name, blob)
        output.extend(bytes(-len(output) % 16))
        struct.pack_into("<QQI", output, entry + 8, len(blob), len(blob), len(output))
        output.extend(blob)
    assert index + 1 == count
    if rename:
        for enc in ("ascii", "utf-16-le"):
            for prefix in ("WP_A_", "wp_a_"):
                output = output.replace((prefix+"1030").encode(enc), (prefix+str(MODEL)).encode(enc))
    compressed = zlib.compress(output, 6)
    header = bytearray(wrapped[:wrapped.index(b"DCA\0")+8])
    struct.pack_into(">II", header, 28, len(output), len(compressed))
    return header + compressed


def extra_rows(name, source, copies):
    layout, size, _, rows = param.load(name)
    count = len(rows)
    assert not rows.keys() & copies.keys()
    old_start = min(rows.values())
    strings = u32(source, 0)
    header_shift = len(copies) * 24
    bodies = bytearray()
    entries = {}
    for j, key in enumerate(rows):
        row, reserved, offset, text = struct.unpack_from("<IIQQ", source, 64+j*24)
        entries[key] = (row, reserved, offset+header_shift, text)
    for key,(donor, fields) in copies.items():
        body = bytearray(source[rows[donor]:rows[donor]+size])
        for field, value in fields.items():
            _, off, width, signed, _, bit, _ = next(f for f in layout if f[0]==field)
            assert bit is None
            body[off:off+width] = value.to_bytes(width, "little", signed=signed)
        entries[key] = (key, 0, strings+header_shift+len(bodies), 0)
        bodies.extend(body)
    head = bytearray(source[:64])
    struct.pack_into("<I", head, 0, strings+header_shift+len(bodies))
    struct.pack_into("<H", head, 10, len(entries))
    struct.pack_into("<Q", head, 48, old_start+header_shift)
    for key in sorted(entries):
        row, reserved, offset, text = entries[key]
        head.extend(struct.pack("<IIQQ", row,reserved,offset,text+header_shift+len(bodies) if text else 0))
    return head + source[64+24*count:strings] + bodies + source[strings:]


def game_params(fid, name, data):
    if name.endswith("EquipParamWeapon.param"):
        donors = {}
        for level in range(11):
            donor = BASE+100*level
            layout, _, original, rows = weapon_data
            origins = param.row_values(layout, original, rows[donor], {f[0] for f in layout if f[0].startswith("originEquipWep")})
            fields = {k:SWORD+(v-BASE) for k,v in origins.items() if BASE<=v<=BASE+1000}
            donors[SWORD+100*level] = donor, dict(
                fields, equipModelId=MODEL, iconId=ICON,
                wanderingEquipId=SWORD+WANDERING_OFFSET,
                sortId=50150+level, compTrophySedId=-1, sellValue=50)
        donors[SWORD+WANDERING_OFFSET] = BASE+WANDERING_OFFSET, dict(
            equipModelId=MODEL, iconId=ICON, wanderingEquipId=SWORD+WANDERING_OFFSET)
        return extra_rows("EquipParamWeapon", data, donors)
    if name.endswith("WeaponGenParam.param"):
        copies = {SWORD+100*level:(GEM_DONOR+100*level,dict(wepParamId=SWORD+100*level))
                  for level in range(11)}
        copies[SWORD+WANDERING_OFFSET] = (
            BASE+WANDERING_OFFSET, dict(wepParamId=SWORD+WANDERING_OFFSET))
        return extra_rows("WeaponGenParam", data, copies)
    if name.endswith("ShopLineupParam.param"):
        fields = dict(equipId=SWORD, value=SHOP_PRICE, qwcId=-1, eventFlag=-1, sellQuantity=-1)
        copies = {shop+116: (shop+100, fields) for shop in BATH_SHOPS}
        return extra_rows("ShopLineupParam", data, copies)
    return data


def messages(data, additions):
    """Merge by ID, including languages that have high-ID sentinel messages."""
    assert data[2]==2
    original = bbfiles.read_fmg(data)
    assert not original.keys() & additions.keys()
    entries = sorted((original | additions).items())
    groups = []
    for index,(key,_) in enumerate(entries):
        if groups and groups[-1][2]+1==key:
            groups[-1][2] = key
        else:
            groups.append([index,key,key])
    table = 40+16*len(groups)
    text_start = table+8*len(entries)
    output = bytearray(data[:40])
    struct.pack_into("<II",output,12,len(groups),len(entries))
    struct.pack_into("<Q",output,24,table)
    for group in groups:
        output.extend(struct.pack("<4i",*group,0))
    texts = bytearray()
    for _,text in entries:
        if text is None:
            output.extend(bytes(8))
        else:
            output.extend(struct.pack("<Q",text_start+len(texts)))
            texts.extend(text.encode("utf-16-le")+bytes(2))
    output.extend(texts)
    struct.pack_into("<I",output,4,len(output))
    return output


# The original vanilla item sprite is the single source for model pixels and the UI icon.
from PIL import Image

with Image.open(Path(__file__).with_name("diamond_sword.png")) as image:
    image = image.convert("RGBA")
    assert image.size==(16,16)
    pixels = list(image.get_flattened_data())
    original_colors = sorted({pixel[:3] for pixel in pixels if pixel[3]})
    COLORS = {chr(65+i):rgb for i,rgb in enumerate(original_colors)}
    symbols = {rgb:key for key,rgb in COLORS.items()}
    SPRITE = tuple("".join(symbols[p[:3]] if p[3] else "."
                           for p in pixels[y*16:(y+1)*16]) for y in range(16))
COLORS.update(o=(34,25,52),p=(65,44,90),k=(12,10,20))
PALETTE_COLUMNS = 16


def pixel_model(template, form):
    """Keep each donor skeleton and mesh binding, replacing its GPU geometry buffers."""
    import flver
    import forms
    source = flver.Flver(template)
    output = bytearray(template)
    _, data_at, _, dummy, materials, bones, meshes, buffers = struct.unpack_from("<8I",output,8)
    assert meshes==buffers and meshes in (1,2)
    bones_at = 128+dummy*64+materials*32
    meshes_at = bones_at+bones*128
    faces_at = meshes_at+meshes*48
    buffer_at = faces_at+32*u32(output,80)
    geometry = dict(blade=forms.blade(SPRITE,list(COLORS)), shell=forms.shell(list(COLORS)))
    mesh_forms = ("blade","shell") if form=="combined" else (form,)
    assert len(mesh_forms)==meshes
    all_points = []

    def append(blob):
        output.extend(bytes(-len(output)%16))
        offset = len(output)-data_at
        output.extend(blob)
        return offset

    for index,kind in enumerate(mesh_forms):
        vertices,indices = geometry[kind]
        assert len(vertices)<65535
        mesh = meshes_at+index*48
        face_count,face_list,buffer_count,buffer_list = struct.unpack_from("<4I",output,mesh+32)
        assert buffer_count==1
        buffer_id = u32(output,buffer_list)
        buffer = buffer_at+buffer_id*32
        stride = u32(output,buffer+8)
        assert stride in (36,44)
        dynamic = stride==44
        if dynamic:
            # Both components of the donor have rigid 100% weights, but distinct animated bones.
            bindings = np.unique(source.meshes[index]["attrs"]["bones"],axis=0)
            weights = np.unique(source.meshes[index]["attrs"]["weights"],axis=0)
            assert len(bindings)==len(weights)==1 and np.array_equal(weights[0],[1,0,0,0])
        encoded = bytearray()
        for point,normal,color in vertices:
            vertex = bytearray(stride)
            struct.pack_into("<3f",vertex,0,*point)
            vertex[12:16] = bytes([*(round(127+127*n) for n in normal),0])
            reference = np.array((0.,1.,0.)) if abs(normal[1])<.9 else np.array((1.,0.,0.))
            tangent = np.cross(reference,normal)
            tangent /= np.linalg.norm(tangent)
            packed = bytes([*(round(127+127*n) for n in tangent),255])
            vertex[16:20] = packed
            vertex[20:24] = packed
            if dynamic:
                vertex[24:28] = bytes(int(bone) for bone in bindings[0])
                vertex[28:32] = bytes((255,0,0,0))
            color_offset,uv_offset = (32,36) if dynamic else (24,28)
            vertex[color_offset:color_offset+4] = bytes([255]*4)
            uv = round((color+.5)*2048/PALETTE_COLUMNS)
            struct.pack_into("<4h",vertex,uv_offset,uv,1024,uv,1024)
            encoded.extend(vertex)
        index_blob = struct.pack("<"+"H"*len(indices),*indices)
        index_offset = append(index_blob)
        vertex_offset = append(encoded)
        for j in range(face_count):
            face = faces_at+u32(output,face_list+4*j)*32
            output[face+4] = 0  # triangle list, including every LOD/motion variant
            struct.pack_into("<3I",output,face+8,len(indices),index_offset,len(index_blob))
            struct.pack_into("<I",output,face+24,16)
        struct.pack_into("<I",output,buffer+12,len(vertices))
        struct.pack_into("<II",output,buffer+24,len(encoded),vertex_offset)
        points = np.array([v[0] for v in vertices])
        bounds = [*points.min(0),*points.max(0)]
        struct.pack_into("<6f",output,u32(output,mesh+24),*bounds)
        all_points.extend(points)
    points = np.array(all_points)
    bounds = [*points.min(0),*points.max(0)]
    struct.pack_into("<6f",output,40,*bounds)
    # Conservative bounds cover the new stepped tip and shell for every donor bone.
    for index in range(bones):
        struct.pack_into("<3f",output,bones_at+128*index+48,*bounds[:3])
        struct.pack_into("<3f",output,bones_at+128*index+64,*bounds[3:])
    output.extend(bytes(-len(output)%16))
    struct.pack_into("<I",output,16,len(output)-data_at)
    return output


def texture(data):
    import tpf
    output = bytearray(data)
    offset,size = struct.unpack_from("<II",data,16)
    width,height = struct.unpack_from("<HH",data,28)
    assert data[24]==1 and width%256==0
    blocks=[]
    for rgb in COLORS.values():
        r,g,b=rgb
        color=(r>>3)<<11 | (g>>2)<<5 | b>>3
        blocks.append(struct.pack("<HHI",color,color,0)*64)
    level=b"".join(blocks[min(x*PALETTE_COLUMNS//(width//32),len(COLORS)-1)] for x in range(width//32))*(height//32)
    assert len(level)<=size
    output[offset:offset+len(level)]=level
    output[26]=1
    # Flat normal/specular maps give the hard voxel faces clean surfaces instead of
    # sampling the donor sword's engraved metal at the new palette UV coordinates.
    for index,entry in enumerate(tpf.read_tpf(data)[1]):
        if index==0:
            continue
        start,length = struct.unpack_from("<II",data,16+36*index)
        if entry["dxgi"] in (71,72):
            rgb = (128,128,255) if "_n" in entry["name"] else (65,75,75)
            r,g,b = rgb
            color = (r>>3)<<11 | (g>>2)<<5 | b>>3
            block = struct.pack("<HHI",color,color,0)
        else:
            assert entry["dxgi"]==80
            block = bytes((110,110,0,0,0,0,0,0))
        assert length%len(block)==0
        output[start:start+length] = block*(length//len(block))
    return output


def solid_bc7(rgba):
    """BC7 mode 6 with identical endpoints and zero interpolation indices."""
    parity = 1 if rgba[3] else 0
    value,shift = 64,7
    for component in rgba:
        for _ in range(2):
            value |= (component>>1)<<shift
            shift += 7
    value |= parity<<shift | parity<<(shift+1)
    return value.to_bytes(16,"little")


def paint_icon(output,start,width,rect):
    """Paint one icon rectangle in a PS4-tiled BC7 texture, preserving every other block."""
    left,top,size = rect
    assert all(v%4==0 for v in rect) and size in (80,400)
    scale = size//20
    border = scale*2
    tile_columns = (width+31)//32
    for y in range(size//4):
        for x in range(size//4):
            px,py = x*4,y*4
            color = "."
            if border<=px<size-border and border<=py<size-border:
                color = SPRITE[(py-border)//scale][(px-border)//scale]
            rgba = (*COLORS[color],255) if color!="." else (0,0,0,0)
            bx,by = left//4+x,top//4+y
            morton = sum(((bx>>b)&1)<<(2*b) | ((by>>b)&1)<<(2*b+1) for b in range(3))
            offset = start+(((by//8)*tile_columns+bx//8)*64+morton)*16
            output[offset:offset+16] = solid_bc7(rgba)


def compressed_dcx(data,template):
    compressed = zlib.compress(data,6)
    header = bytearray(template[:template.index(b"DCA\0")+8])
    struct.pack_into(">II",header,28,len(data),len(compressed))
    return header+compressed


def icon_atlas(wrapped):
    """Small icon for inventory, shop, storage and equipment lists."""
    import tpf
    output = bytearray(souls.read_dcx(wrapped))
    index,atlas = next((i,t) for i,t in enumerate(tpf.read_tpf(output)[1])
                      if t["name"]=="MENU_Icon_01001")
    assert (atlas["fmt"],atlas["w"],atlas["h"],atlas["mips"])==(102,1024,512,1)
    start = u32(output,16+36*index)
    paint_icon(output,start,atlas["w"],(480,240,80))
    return compressed_dcx(output,wrapped)


def knowledge_icon(wrapped):
    """Separate 400px item-detail texture requested by the native menu's icon ID."""
    import tpf
    output = bytearray(souls.read_dcx(wrapped))
    _,textures = tpf.read_tpf(output)
    assert len(textures)==1
    atlas = textures[0]
    assert (atlas["fmt"],atlas["w"],atlas["h"],atlas["mips"])==(102,400,400,1)
    paint_icon(output,u32(output,16),400,(0,0,400))
    output = output.replace("MENU_Knowledge_01010".encode("utf-16-le"),
                            f"MENU_Knowledge_{ICON:05}".encode("utf-16-le"))
    return compressed_dcx(output,wrapped)


def build(game,destination,common_textures=None):
    global weapon_data
    bbfiles.GAME=str(game)
    weapon_data=param.load("EquipParamWeapon")
    rel=Path("param/gameparam/gameparam.parambnd.dcx")
    def write(path,content):
        target=destination/"dvdroot_ps4"/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(content)
    write(rel,archive(game/rel,game_params))
    icon_path = Path("menu/common.tpf.dcx")
    write(icon_path,icon_atlas((common_textures or game/icon_path).read_bytes()))
    write(Path(f"menu/menu_knowledge_{ICON:05}.tpf.dcx"),
          knowledge_icon((game/"menu/menu_knowledge_01010.tpf.dcx").read_bytes()))
    for suffix in ("","_l"):
        donor=game/f"parts/wp_a_1030{suffix}.partsbnd.dcx"
        def parts(fid,name,blob):
            if fid==100:
                return texture(blob)
            if name.lower().endswith(".flver"):
                return pixel_model(blob,{200:"blade",201:"shell",202:"combined"}[fid])
            return blob
        write(Path(f"parts/wp_a_{MODEL}{suffix}.partsbnd.dcx"),archive(donor,parts,True))
    for folder in sorted((game/"msg").iterdir()):
        lang=folder.name
        rel=Path("msg")/lang/"item.msgbnd.dcx"
        if not (game/rel).is_file():
            continue
        russian=lang=="rusru"
        def localize(fid,name,blob):
            if fid not in (11,21,25):
                return blob
            title="Алмазный меч" if russian else "Diamond Sword"
            description=("Алмазный клинок с обсидиановой оболочкой.\n"
                         "Соединяется с ней в массивный двуручный меч."
                         if russian else
                         "A diamond blade with an obsidian shell.\n"
                         "Combine them to form a massive greatsword.")
            additions = {SWORD+100*n: (title+(f" +{n}" if n else "") if fid==11 else description)
                         for n in range(11)}
            additions[SWORD+WANDERING_OFFSET] = title if fid==11 else description
            return messages(blob,additions)
        write(rel,archive(game/rel,localize))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dvdroot",type=Path)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--common-textures",type=Path,help="Preserve the selected button prompt pack's common.tpf.dcx")
    args=parser.parse_args()
    if args.destination.resolve().is_relative_to(args.dvdroot.resolve().parent):
        parser.error("destination must be outside the game")
    build(args.dvdroot,args.destination,args.common_textures)


