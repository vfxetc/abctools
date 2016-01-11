import imath
import alembic
from alembic import AbcGeom, Abc

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

def accumulate_xform(xf, obj, seconds):
    if AbcGeom.IXform.matches(obj.getHeader()):
        x = AbcGeom.IXform(obj, KWrapExisting)
        sel = Abc.ISampleSelector(seconds)
        samp = x.getSchema().getValue(sel)
        xf *= samp.getMatrix()

def get_final_matrix(obj, secs = 0):

    parent = obj.getParent()
    xf = imath.M44d()
    xf.makeIdentity()

    while parent:
        accumulate_xform(xf, parent, secs)
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

def find_objects(mesh_list, object_dict):

    mesh_maping = {}
    for object_name in object_dict:
        names = object_dict[object_name].get('alternative_names', [])
        names.append(object_name)
        mesh = None

        for m in mesh_list:
            nice_name = m.getName().split(":")[-1]

            if nice_name in names:
                mesh = m
                break

        if mesh is None:
            raise Exception("Unable to find %s in abc cache" % object_name)

        mesh_maping[object_name] = mesh

    return mesh_maping

def nuke_tracker(abc_file, abc_camera_file, tracking_sets, dest_nuke_file):
#     print abc_file
#     print abc_camera_file
#     print dest_nuke_file
#     print tracking_sets

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
    width = 1920.0
    height = 1080.0

    start, end = get_frame_range(archive)
    cam_start, cam_end = get_frame_range(camera_archive)

    start = min(start, cam_start)
    end = max(end, cam_end)

    start_frame = int(start * fps + 0.5)
    end_frame = int(end * fps + 0.5)
    # print alembic.Abc.GetArchiveInfo(archive)

    object_map = find_objects(meshs, tracking_sets['objects'])

    data = {}

    # Setup Trackers
    for i, camera in enumerate(cameras):
        for tracker_data in tracking_sets['tracks']:
            # print camera.getName(), tracker['tracker_name']
            cam = camera.getName()
            tracker_name = tracker_data['tracker_name']
            if not cam in data:
                data[cam] = []
            if not tracker_name in [t.name for t in  data[cam]]:
                if i > 0:
                    tracker_name = "%s_%02d" % (tracker_name, i)

                tracker = NukeTracker(tracker_name,
                                                         tracker_data['tracking_points'],
                                                         width,
                                                         height,
                                                         start_frame)
                data[cam].append(tracker)

    for frame in xrange(start_frame, end_frame + 1):
        secs = frame * 1 / float(fps)
        for camera in cameras:
            cam = camera.getName()
            cam_schema = camera.getSchema()
            cam_samp = cam_schema.getValue(secs)
            focal_length = cam_samp.getFocalLength()
            near = cam_samp.getNearClippingPlane()
            far = cam_samp.getFarClippingPlane()
            vertical_aperture = cam_samp.getVerticalAperture()
            fovy = 2.0 * math.degrees(math.atan(vertical_aperture * 10.0 /
                                                                        (2.0 * focal_length)))

            persp_matrix = perspective(fovy, width / height, near, far)
            view_matrix = inv(get_final_matrix(camera, secs))

            for tracker in data[cam]:
                tracker.eval(persp_matrix, view_matrix , object_map, secs)

    with open(dest_nuke_file, 'w') as f:
        for camera in data:
            for tracker in data[camera]:
                tracker.export_nuke(f)


    return


class Track(object):
    def __init__(self, start):
        self.x = []
        self.y = []
        self.start_frame = start

    def curves(self):

        x = "{curve x%d " % self.start_frame
        y = "{curve x%d " % self.start_frame

        x += " ".join([str(item) for item in self.x]) + "}"
        y += " ".join([str(item) for item in self.y]) + "}"

        return x, y


class NukeTracker(object):

    def __init__(self, name, tracking_points, width, height, start):
        self.tracks = []
        self.name = name
        self.tracking_points = tracking_points
        self.width = width
        self.height = height
        self.start = start

        for item in tracking_points:
            self.tracks.append(Track(start))

    def eval(self, persp_matrix, view_matrix , object_map, secs):
        for i, (object_name, point_index) in enumerate(self.tracking_points):
            mesh = object_map[object_name]
            schema = mesh.getSchema()
            sel = Abc.ISampleSelector(secs)
            mesh_samp = schema.getValue(sel)
            model_matrix = get_final_matrix(mesh, secs)

            positions = mesh_samp.getPositions()
            pos = positions[point_index]

            point = [ [pos.x ], [pos.y ], [pos.z  ], [1.0] ]

            v = persp_matrix.T * view_matrix * model_matrix * point

            x = v[0, 0]
            y = v[1, 0]
            z = v[2, 0]
            w = v[3, 0]

            x = (((x / w) + 1) / 2.0) * self.width
            y = (((y / w) + 1) / 2.0) * self.height

            self.tracks[i].x.append(x)
            self.tracks[i].y.append(y)

    def export_nuke(self, f):
        l = []
        f.write("Tracker4 {\n")
        f.write("tracks { { 1 31 %d }\n" % len(self.tracks))
        f.write("{ { 5 1 20 enable e 1 }\n")
        f.write("{ 3 1 75 name name 1 }\n")
        f.write("{ 2 1 58 track_x track_x 1 }\n")
        f.write("{ 2 1 58 track_y track_y 1 }\n")
        f.write("{ 2 1 63 offset_x offset_x 1 }\n")
        f.write("{ 2 1 63 offset_y offset_y 1 }\n")
        f.write("{ 4 1 27 T T 1 }\n")
        f.write("{ 4 1 27 R R 1 }\n")
        f.write("{ 4 1 27 S S 1 }\n")
        f.write("{ 2 0 45 error error 1 }\n")
        f.write("{ 1 1 0 error_min error_min 1 }\n")
        f.write("{ 1 1 0 error_max error_max 1 } \n")
        f.write("{ 1 1 0 pattern_x pattern_x 1 }\n")
        f.write("{ 1 1 0 pattern_y pattern_y 1 }\n")
        f.write("{ 1 1 0 pattern_r pattern_r 1 }\n")
        f.write("{ 1 1 0 pattern_t pattern_t 1 }\n")
        f.write("{ 1 1 0 search_x search_x 1 }\n")
        f.write("{ 1 1 0 search_y search_y 1 }\n")
        f.write("{ 1 1 0 search_r search_r 1 }\n")
        f.write("{ 1 1 0 search_t search_t 1 }\n")
        f.write("{ 2 1 0 key_track key_track 1 }\n")
        f.write("{ 2 1 0 key_search_x key_search_x 1 }\n")
        f.write("{ 2 1 0 key_search_y key_search_y 1 }\n")
        f.write("{ 2 1 0 key_search_r key_search_r 1 }\n")
        f.write("{ 2 1 0 key_search_t key_search_t 1 }\n")
        f.write("{ 2 1 0 key_track_x key_track_x 1 }\n")
        f.write("{ 2 1 0 key_track_y key_track_y 1 }\n")
        f.write("{ 2 1 0 key_track_r key_track_r 1 }\n")
        f.write("{ 2 1 0 key_track_t key_track_t 1 }\n")
        f.write("{ 2 1 0 key_centre_offset_x key_centre_offset_x 1 }\n")
        f.write("{ 2 1 0 key_centre_offset_y key_centre_offset_y 1 }\n")
        f.write("}\n")


        track_tail = "{} {} 1 0 0 {} 1 0 -30 -30 30 30 -21 -21 21 21 {} {}  {}  {}  {}  {}  {}  {}  {}  {}  {}"

        f.write("{\n")
        for i, track in enumerate(self.tracks):
            track_name = "track %d" % (i + 1,)
            x_curve, y_curve = track.curves()
            track_string = '{ 1 "%s"  %s %s  %s }\n' % (track_name, x_curve, y_curve, track_tail)
            f.write(track_string)

        f.write("}\n")
        f.write("}\n") # tracks

        f.write("name %s\n" % self.name)
        f.write("}\n")
        f.write("\n")

