import imath
import alembic
from alembic import AbcGeom, Abc
from abctools import cask
KWrapExisting = alembic.Abc.WrapExistingFlag.kWrapExisting
import math

def accumulate_xform(xf, obj, seconds):
    if AbcGeom.IXform.matches(obj.getHeader()):
        x = AbcGeom.IXform(obj, KWrapExisting)
        sel = Abc.ISampleSelector(seconds)
        samp = x.getSchema().getValue(sel)
        xf *= samp.getMatrix()

def create_camera(camera, seconds=0.0):
    """
    convert abc camera to rib camera
    """

    if isinstance(camera, cask.Camera):
        camera = AbcGeom.ICamera(camera.iobject, KWrapExisting)

    xf = imath.M44d()
    xf.makeIdentity()
    parent = camera.getParent()
    while parent:
        accumulate_xform(xf, parent, seconds)
        parent = parent.getParent()


    xf.scale((1, 1, -1))
    xf.invert()

    camera_name = camera.getName()
    sel = Abc.ISampleSelector(seconds)
    cam_samp = camera.getSchema().getValue(sel)
    focal_length = cam_samp.getFocalLength()
    near = cam_samp.getNearClippingPlane()
    far = cam_samp.getFarClippingPlane()
    vertical_aperture = cam_samp.getVerticalAperture()
    fovy = 2.0 * math.degrees(math.atan(vertical_aperture * 10.0 /
                                        (2.0 * focal_length)))

    rib = """
    Projection "perspective" "fov" {fov}
    Transform [{transfrom}]
    """.format(fov=fovy, transfrom=" ".join(str(i) for item in xf for i in item))
    return rib


def create_subdivision_mesh(node, seconds=0.0):
    """
    converts IPolyMesh to catmull-clark SubdivisionMesh
    """

    if isinstance(node, AbcGeom.IPolyMesh):
        node = cask.wrap(node)

    geom = node.properties['.geom']

    counts = geom.properties['.faceCounts'].get_value(time=seconds)
    ids = geom.properties['.faceIndices'].get_value(time=seconds)
    Ps = geom.properties['P'].get_value(time=seconds)

    yield 'SubdivisionMesh "catmull-clark"'
    yield ' [%s]' % ' '.join(map(str, counts))
    yield ' [%s]' % ' '.join(map(str, ids))
    yield ' ["interpolateboundary"] [0 0] [] []'
    yield ' "P" [%s]' % '  '.join('%f %f %f' % tuple(P) for P in Ps)

    uvs = geom.properties.get('uv')
    if uvs:
        uv_ids = uvs.properties['.indices'].get_value(time=seconds)
        vals = uvs.properties['.vals'].get_value(time=seconds)

        yield ' "facevarying float s" [%s]' % ' '.join(str(vals[id_][0]) for id_ in uv_ids)
        yield ' "facevarying float t" [%s]' % ' '.join(str(vals[id_][1]) for id_ in uv_ids)

    yield '\n'

def iter_all(node):
    yield node
    for child in node.children.itervalues():
        for obj in iter_all(child):
            yield obj


if __name__ == "__main__":
    import sys
    import subprocess
    archive = cask.Archive(sys.argv[1])

    cameras = []
    meshs = []

    for node in iter_all(archive.top):
        if node.type() == "PolyMesh":
            meshs.append(node)
        if node.type() == "Camera":
            cameras.append(node)

    f = open("out.rib", 'w')
    f.write('Display "output.tif" "framebuffer" "rgba"\n')
    f.write('Format 1920 1080 1\n')
    seconds = 1.0
    f.write(create_camera(cameras[0], seconds))
    f.write('WorldBegin\n')
    f.write('Surface "uv_shader"\n')
    for mesh in meshs:
        f.write("\n".join(create_subdivision_mesh(mesh, seconds)))
        f.write("\n")

    f.write('WorldEnd\n')
    f.close()

    f = open("uv_shader.sl", 'w')
    f.write("""surface uv_shader(){Ci = color(s, t, 0);}""")
    f.close()

    subprocess.check_call(['shader', "uv_shader.sl"])
    subprocess.check_call(['prman', "out.rib"])

