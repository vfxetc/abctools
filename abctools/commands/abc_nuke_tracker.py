from optparse import OptionParser
import os
import subprocess
import tempfile
import shutil
import yaml
import json
import pprint

from abctools import nuke_tracker
from abctools import metadata

def convert_camera(path, temp_dir):
    basename = os.path.basename(path)
    name, ext = os.path.splitext(basename)
    dest = os.path.join(temp_dir, name + '.abc')
    cmd = ['maya_camera2abc', path, dest]
    print "converting camera %s -> %s" % (basename, dest)
    subprocess.check_call(cmd)
    return dest

def read_tracking_set_meta(path, prefix = "__tracker__"):
    meta = metadata.load(path)

    data = {'objects':{},
            'tracks': []}

    for key, value in meta['sets'].items():
        name = key.split(':')[-1]
        if not name.lower().startswith(prefix):
            continue

        # print name.replace(prefix, "")
        tracking_points = []

        for attr in value['attributes']:
            object_name = attr.split(':')[-1].split('.')[0]

            if not object_name in data['objects']:
                data['objects'][object_name] = {'alternative_names': [object_name, object_name + "Shape"]}

            # print object_name
            for index in value['attributes'][attr].get('indices', []):
                tracking_points.append([object_name, int(index)])
            # print indices

        track = {'tracker_name':name.replace(prefix, ""),
                   'tracking_points':tracking_points}

        data['tracks'].append(track)

    return data

def cli():
    usage = "usage: %prog [options] SOURCE_ABC_FILE [DEST_NUKE_FILE]"
    parser = OptionParser(usage)
    parser.add_option("-c", '--camera', default = None, help = "camera file [.abc/.mb/.ma]")
    parser.add_option("-t", '--tracking_set', default = None, help = "tracking set file [.yml]")

    (options, args) = parser.parse_args()

    if not args:
        parser.error("Not enough arguments")

    source = args[0]


    if len(args) > 1:
        dest = args[1]
    else:
        name, ext = os.path.splitext(source)
        dest = name + ".nk"

    if options.tracking_set:
        tracking_sets = yaml.load(file(options.tracking_set, 'r'))
    else:
        tracking_sets = read_tracking_set_meta(source)

    # pprint.pprint(tracking_sets)

    camera_file = source

    temp_dir = tempfile.mkdtemp()
    try:
        if options.camera:
            name, ext = os.path.splitext(options.camera)
            camera_file = options.camera
            if ext.lower() in ('.mb', '.ma'):
                camera_file = convert_camera(options.camera, temp_dir)

        nuke_tracker.nuke_tracker(abc_file = source,
                                  abc_camera_file = camera_file,
                                  tracking_sets = tracking_sets,
                                  dest_nuke_file = dest)

    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    cli()

