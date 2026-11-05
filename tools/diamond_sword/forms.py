"""Voxel geometry for the diamond blade and its hollow obsidian greatsword shell."""
import numpy as np


def surface(cells, scale, origin, colors):
    """Emit only exposed voxel faces, with outward winding and hard normals."""
    faces = (
        ((0,0,1), ((0,0,1),(1,0,1),(1,1,1),(0,1,1))),
        ((0,0,-1), ((0,1,0),(1,1,0),(1,0,0),(0,0,0))),
        ((-1,0,0), ((0,0,0),(0,0,1),(0,1,1),(0,1,0))),
        ((1,0,0), ((1,1,0),(1,1,1),(1,0,1),(1,0,0))),
        ((0,-1,0), ((1,0,0),(1,0,1),(0,0,1),(0,0,0))),
        ((0,1,0), ((0,1,0),(0,1,1),(1,1,1),(1,1,0))),
    )
    vertices, indices = [], []
    for (x,y,z), color in cells.items():
        for adjacent, corners in faces:
            neighbor = tuple(a+b for a,b in zip((x,y,z),adjacent))
            if neighbor in cells:
                continue
            points = [origin+scale@np.array((x+dx,y+dy,z+dz)) for dx,dy,dz in corners]
            normal = np.cross(points[1]-points[0],points[2]-points[0])
            normal /= np.linalg.norm(normal)
            first = len(vertices)
            indices.extend(first+i for i in (0,1,2,0,2,3))
            vertices.extend((point,normal,colors.index(color)) for point in points)
    return vertices, indices


def blade(sprite, colors):
    cells = {(x,y,0):color for y,row in enumerate(sprite)
             for x,color in enumerate(row) if color!="."}
    # A 45-degree rotation aligns the vanilla diagonal item sprite with the grip.
    # This preserves its pixel silhouette and proportions, including the original guard.
    scale = np.array(((.049,.049,0),(-.049,.049,0),(0,0,.06)))
    return surface(cells,scale,np.array((-.784,-.392,-.03)),colors)


def shell(colors):
    cells = {}
    # The top remains open for the diamond blade. A central window reveals its core.
    for row in range(30):
        half_width = 4 if row<25 else (3 if row<27 else (2 if row<29 else 1))
        for x in range(-half_width,half_width+1):
            for z in range(-1,2):
                side = abs(x)==half_width
                cap = row==29
                if z==0 and not (side or cap):
                    continue
                if abs(x)==0 and not cap:
                    continue
                color = "k" if side else ("o" if (row+x)%4 else "p")
                if abs(x)==half_width-1 and row<29:
                    color = "C"
                if row in (1,9,17,25) and abs(x)>0 and not side:
                    color = "F" if abs(x)%2 else "K"
                if cap:
                    color = "F" if z else "C"
                cells[x,29-row,z] = color
    return surface(cells,np.diag((.035,.044,.035)),np.array((-.0175,-1.49,-.0175)),colors)
