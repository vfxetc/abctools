import imath
import alembic
from alembic import AbcGeom

import math
import numpy as np
from numpy.linalg import inv

KWrapExisting = alembic.Abc.WrapExistingFlag.kWrapExisting

def walk_objects(obj, meshs, cameras):

    if AbcGeom.ICamera.matches(obj.getHeader()):
        cameras.append(AbcGeom.ICamera(obj, KWrapExisting))

    elif AbcGeom.IPolyMesh.matches(obj.getHeader()):
        meshs.append(AbcGeom.IPolyMesh(obj, KWrapExisting))

    for i in range(obj.getNumChildren()):
        child = obj.getChild(i)
        walk_objects(child, meshs, cameras)

def get_min_max(a , b, cmp = min):
    if a is None:
        return b
    return cmp(a, b)

def get_frame_range(archive):

    start = None
    end = None

    start_single = None
    end_single = None

    start_default = None
    end_default = None

    for i in range(archive.getNumTimeSamplings()):
        index = archive.getMaxNumSamplesForTimeSamplingIndex(i);
        ts = archive.getTimeSampling(i);
        if not ts:
            continue

        if index > 1 and i != 0:
            start = get_min_max(start, ts.getSampleTime(0), min)
            end = get_min_max(end, ts.getSampleTime(index - 1), max)

        elif index == 1 and i != 0:
            start_single = get_min_max(start_single, ts.getSampleTime(0), min)
            end_single = get_min_max(end_single, ts.getSampleTime(0), max)

        elif index > 0 and i == 0:
            start_default = ts.getSampleTime(0);
            end_default = ts.getSampleTime(index - 1);

    # print start, start_single, start_default
    # print end, end_single, end_default

    if not start is None and not end is None:
        return start, end

    elif not start_single is None and not end_single is None:
        return start_single, end_single

    elif  not start_default is None and not end_default is None:
        return start_default, end_default

    else:
        return None, None

def accumulate_xform(xf, obj):
    if AbcGeom.IXform.matches(obj.getHeader()):
        x = AbcGeom.IXform(obj, KWrapExisting)
        samp = x.getSchema().getValue()
        xf *= samp.getMatrix()

def get_final_matrix(obj):

    parent = obj.getParent()
    xf = imath.M44d()
    xf.makeIdentity()

    while parent:
        accumulate_xform(xf, parent)
        parent = parent.getParent()

    xf_m = np.zeros((4, 4), dtype = np.float32)

    # transpose the matrix
    for y in range(4):
        for x in range(4):
            xf_m[y, x] = xf[x][y]

    return  np.matrix(xf_m)


def frustum(left, right, bottom, top, znear, zfar):
    assert(right != left)
    assert(bottom != top)
    assert(znear != zfar)
    # this is transposed incorrectly
    M = np.zeros((4, 4), dtype = np.float32)
    M = np.matrix(M)
    M[0, 0] = +2.0 * znear / (right - left)
    M[2, 0] = (right + left) / (right - left)
    M[1, 1] = +2.0 * znear / (top - bottom)
    M[3, 1] = (top + bottom) / (top - bottom)
    M[2, 2] = -(zfar + znear) / (zfar - znear)
    M[3, 2] = -2.0 * znear * zfar / (zfar - znear)
    M[2, 3] = -1.0

    return M

def perspective(fovy, aspect, znear, zfar):
    assert(znear != zfar)
    h = np.tan(fovy / 360.0 * np.pi) * znear
    w = h * aspect
    return frustum(-w, w, -h, h, znear, zfar)

def nuke_tracker(abc_file, abc_camera_file, dest_nuke_file):
    print abc_file
    print abc_camera_file
    print dest_nuke_file

    archive = alembic.Abc.IArchive(abc_file)
    camera_archive = alembic.Abc.IArchive(abc_camera_file)

    cameras = []
    meshs = []

    walk_objects(camera_archive.getTop(), [], cameras)
    walk_objects(archive.getTop(), meshs, [])

    if not cameras:
        raise RuntimeError("unable to find cameras in %s" % abc_camera_file)
    if not meshs:
        raise RuntimeError("unable to find polymeshs  in %s" % abc_file)

    fps = 24.0
    start, end = get_frame_range(archive)
    cam_start, cam_end = get_frame_range(camera_archive)

    start = min(start, cam_start)
    end = max(end, cam_end)

    start_frame = int(start * fps)
    end_frame = int(end * fps)
    # print alembic.Abc.GetArchiveInfo(archive)
    mesh = meshs[0]
    camera = cameras[0]
    schema = mesh.getSchema()
    cam_schema = camera.getSchema()


    x_points = []
    y_points = []
    for i in xrange(start_frame, end_frame):
        t = i * 1 / float(fps)
        cam_samp = cam_schema.getValue(t)
        mesh_samp = schema.getValue(t)

        positions = mesh_samp.getPositions()

        pos  = positions[6108]

        focal_length = cam_samp.getFocalLength()
        vertical_aperture = cam_samp.getVerticalAperture()
        horizontal_aperture = cam_samp.getHorizontalAperture()
        near = cam_samp.getNearClippingPlane()
        far = cam_samp.getFarClippingPlane()
        fovy = 2.0 * math.degrees(math.atan(vertical_aperture * 10.0 /
                                                                                (2.0 * focal_length)))

#         print "focal", focal_length
#         print "horizontal_aperture", horizontal_aperture * 10
#         print "vertical_aperture", vertical_aperture * 10
#         print "fovy", fovy, focal_length / horizontal_aperture
#         print "near, far", near, far

        width = 1920.0
        height = 1080.0

        point = [ [pos.x ], [pos.y ], [pos.z  ], [1.0] ]

        persp_matrix = perspective(fovy, width / height, near, far)
        view_matrix = inv(get_final_matrix(camera))
        model_matrix = get_final_matrix(mesh)

        # transform the point
        v = persp_matrix.T * view_matrix * model_matrix * point

        x = v[0, 0]
        y = v[1, 0]
        z = v[2, 0]
        w = v[3, 0]

        x = (((x / w) + 1) / 2.0) * width
        y = (((y / w) + 1) / 2.0) * height

        x_points.append(x)
        y_points.append(y)


    print "{curve x%d" % start_frame, " ".join([str(item) for item in x_points]), "}",
    print "{curve x%d" % start_frame, " ".join([str(item) for item in y_points]), "}"

