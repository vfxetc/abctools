from optparse import OptionParser
import os
import re

cmds = None

def setup_standalone():
    import maya.standalone
    maya.standalone.initialize()

    import maya.cmds
    import maya.mel
    global cmds
    global mel
    cmds = maya.cmds

def cli():
    usage = "usage: %prog [options] MAYA_FILE [ABC_FILE]"
    parser = OptionParser(usage)
    parser.add_option("-v", '--verbose', dest = "verbose", action = "store_true", default = False, help = "verbose mode")

    (options, args) = parser.parse_args()

    if not args:
        parser.error("Not enough arguments")

    source = args[0]

    if len(args) > 1:
        dest = args[1]
    else:
        name, ext = os.path.splitext(source)
        dest = name + ".abc"

    dest = os.path.abspath(dest)

    setup_standalone()

    # load AbcExport plugin
    if not cmds.pluginInfo('AbcExport', query = True, loaded = True):
        cmds.loadPlugin('AbcExport')

    nodes = cmds.file(source, i = True, returnNewNodes = True) or []

    # remove underworld nodes
    nodes = [n for n in nodes if not n.count("->")]

    cameras = cmds.ls(nodes, type = "camera", l = True)
    if not cameras:
        parser.error("maya scene file has no cameras")

    cmds.select(cameras)

    keys = cmds.keyframe(query = True, hierarchy = "both") or [1]
    frame_from = min(keys)
    frame_to = max(keys)

    job = '''
                -selection
                -stripNamespaces
                -eulerFilter
                -frameRange {frame_from} {frame_to}
                -file {path}
            '''

    kwargs= {
             'frame_from': frame_from,
             'frame_to' : frame_to,
             'path': dest
             }

    cmds.AbcExport(j = re.sub(r'\s+', ' ', job).format(**kwargs), verbose = options.verbose)


if __name__ == "__main__":
    cli()
