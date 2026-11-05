"""Verify built weapon integration without opening or editing any save."""
import argparse
import io
from pathlib import Path

import numpy as np
from PIL import Image

import build
import bbfiles
import flver
import param
import souls
import tpf


def decoded_texture(path, name):
    entries = tpf.read_tpf(souls.read_dcx(path.read_bytes()))[1]
    texture = next(t for t in entries if t["name"]==name)
    return np.array(Image.open(io.BytesIO(tpf.dds_bytes(texture))).convert("RGBA"))


def verify(game, destination, common_textures):
    bbfiles.GAME = str(game)
    root = destination/"dvdroot_ps4"
    bundle = bbfiles.read_bnd4(bbfiles.read_dcx(root/"param/gameparam/gameparam.parambnd.dcx"))
    tables = {}
    for name in ("EquipParamWeapon","WeaponGenParam","ShopLineupParam"):
        layout,size,original,old_rows = param.load(name)
        data = bundle[name+".param"][1]
        rows = param.read_param(data)
        assert all(original[offset:offset+size]==data[rows[key]:rows[key]+size]
                   for key,offset in old_rows.items()), name
        tables[name] = {key:param.row_values(layout,data,offset) for key,offset in rows.items()}
    weapons,generators,shops = (tables[n] for n in ("EquipParamWeapon","WeaponGenParam","ShopLineupParam"))
    materials = param.load("EquipMtrlSetParam")[3]
    reinforcements = param.load("ReinforceParamWeapon")[3]
    _,_,source,source_rows = param.load("EquipParamWeapon")
    layout = param.load("EquipParamWeapon")[0]
    permitted = {"equipModelId","iconId","sortId","wanderingEquipId","compTrophySedId","sellValue"}
    permitted.update(f[0] for f in layout if f[0].startswith("originEquipWep"))
    for level in range(11):
        key = build.SWORD+100*level
        weapon,gen = weapons[key],generators[key]
        old = param.row_values(layout,source,source_rows[build.BASE+100*level])
        assert all(value==weapon[field] for field,value in old.items() if field not in permitted)
        assert weapon["equipModelId"]==build.MODEL and weapon["iconId"]==build.ICON
        assert weapon["compTrophySedId"]==-1 and 0<=weapon["sellValue"]<=100
        assert weapon["wanderingEquipId"] in weapons and weapon["wanderingEquipId"] in generators
        assert weapon["materialSetId"] in materials and weapon["reinforceTypeId"] in reinforcements
        assert weapon["originEquipWep"]==build.SWORD+100*max(0,level-1)
        assert gen["wepParamId"]==key and gen["equipableGemSegmentMask"]==1
        expected = [1 if level>=1 else 0x80000100,
                    1 if level>=3 else 0x80000100,
                    2 if level>=6 else 0x80000100]
        assert [gen[f"gemSlotType_{i}"] for i in range(3)]==expected
        assert [gen[f"reserveGemSlotNo_{i}"] for i in range(3)]==[1,1,2]
        assert all(gen[f"gemGenId_{i}"]==-1 for i in range(5))
        assert all(gen[f"gemSlotType_{i}"]==0x80000100 for i in (3,4))
    for base in build.BATH_SHOPS:
        assert shops[base+116]["equipId"]==build.SWORD and shops[base+116]["value"]==build.SHOP_PRICE
        assert shops[base+116]["qwcId"]==-1 and shops[base+116]["eventFlag"]==-1
    print("PASS: stock rows unchanged; 11 upgrade levels, gem unlocks, normalization and 5 shops")
    languages = 0
    for path in (root/"msg").glob("*/item.msgbnd.dcx"):
        original = bbfiles.read_bnd4(bbfiles.read_dcx(game/path.relative_to(root)))
        generated = bbfiles.read_bnd4(bbfiles.read_dcx(path))
        for name,(fid,old) in original.items():
            new = generated[name][1]
            if fid not in (11,21,25):
                assert old==new
                continue
            entries = bbfiles.read_fmg(new)
            assert all(entries[key]==text for key,text in bbfiles.read_fmg(old).items())
            assert all(entries[build.SWORD+100*level] for level in range(11))
            if path.parent.name=="rusru" and fid==11:
                assert entries[build.SWORD]=="Алмазный меч"
        languages += 1
    print(f"PASS: names/descriptions at every level; {languages} languages preserve stock text")
    atlas_path = root/"menu/common.tpf.dcx"
    new = decoded_texture(atlas_path,"MENU_Icon_01001")
    old = decoded_texture(common_textures,"MENU_Icon_01001")
    mask = np.ones(new.shape[:2],dtype=bool)
    mask[240:320,480:560] = False
    assert np.array_equal(old[mask],new[mask])
    large = decoded_texture(root/f"menu/menu_knowledge_{build.ICON:05}.tpf.dcx",
                            f"MENU_Knowledge_{build.ICON:05}")
    sprite = np.array(Image.open(Path(build.__file__).with_name("diamond_sword.png")).convert("RGBA"))
    for icon in (new[248:312:4,488:552:4],large[40:360:20,40:360:20]):
        assert np.array_equal(icon[:,:,3],sprite[:,:,3])
        visible = sprite[:,:,3]>0
        assert np.max(np.abs(icon[visible,:3].astype(int)-sprite[visible,:3].astype(int)))<=1
    for suffix in ("","_l"):
        path = root/f"parts/wp_a_{build.MODEL}{suffix}.partsbnd.dcx"
        originals = {i:b for i,_,b in souls.read_bnd4(
            souls.read_dcx((game/f"parts/wp_a_1030{suffix}.partsbnd.dcx").read_bytes()))}
        for fid,name,data in souls.read_bnd4(souls.read_dcx(path.read_bytes())):
            if not name.lower().endswith(".flver"):
                continue
            model,donor = flver.Flver(data),flver.Flver(originals[fid])
            assert len(model.meshes)==len(donor.meshes)
            assert [(b["t"],b["r"],b["s"],b["parent"]) for b in model.bones]==[
                (b["t"],b["r"],b["s"],b["parent"]) for b in donor.bones]
            for mesh,old_mesh in zip(model.meshes,donor.meshes):
                attrs = mesh["attrs"]
                assert np.isfinite(attrs["position"]).all()
                assert mesh["tris"].min()>=0 and mesh["tris"].max()<mesh["verts"]
                assert np.allclose(np.linalg.norm(attrs["normal"][:,:3],axis=1),1,atol=.02)
                if "bones" in attrs:
                    assert np.array_equal(np.unique(attrs["bones"],axis=0),
                                          np.unique(old_mesh["attrs"]["bones"],axis=0))
                    assert np.allclose(attrs["weights"][:,0],1)
    print("PASS: small/large icons match vanilla sprite; other atlas icons unchanged; all 6 models")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dvdroot",type=Path)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--common-textures",type=Path)
    args = parser.parse_args()
    verify(args.dvdroot,args.destination,args.common_textures or args.dvdroot/"menu/common.tpf.dcx")
