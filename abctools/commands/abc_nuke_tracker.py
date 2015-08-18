from optparse import OptionParser
import os
import subprocess
import tempfile
import shutil

from abctools import nuke_tracker

def convert_camera(path, temp_dir):
    basename = os.path.basename(path)
    name, ext = os.path.splitext(basename)
    dest = os.path.join(temp_dir, name + '.abc')
    cmd = ['maya_camera2abc', path, dest]
    print "converting camera %s -> %s" % (basename, dest)
    subprocess.check_call(cmd)
    return dest

def cli():
    usage = "usage: %prog [options] SOURCE_ABC_FILE [DEST_NUKE_FILE]"
    parser = OptionParser(usage)
    parser.add_option("-c", '--camera', default = None, help = "camera file [.abc/.mb/.ma]")

    (options, args) = parser.parse_args()

    if not args:
        parser.error("Not enough arguments")


    source = args[0]

    if len(args) > 1:
        dest = args[1]
    else:
        name, ext = os.path.splitext(source)
        dest = name + ".nk"

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
                                                            dest_nuke_file = dest)

    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    cli()

