from maya import cmds


def swap_path(old_abc, new_path, name=None):

    if name is None:
        name = old_abc.split('|')[-1].split(':')[-1]

    new_abc = cmds.createNode('AlembicNode', name=name)
    cmds.setAttr('%s.abc_File' % new_abc, new_path, type='string')

    plugs = cmds.listConnections(old_abc, connections=True, plugs=True, source=True, destination=False)
    print plugs
    for old_dst, src in zip(plugs[::2], plugs[1::2]):
        new_dst = new_abc + '.' + old_dst.split('.')[1]
        cmds.connectAttr(src, new_dst, force=True)

    plugs = cmds.listConnections(old_abc, connections=True, plugs=True, source=False, destination=True)
    for old_src, dst in zip(plugs[::2], plugs[1::2]):
        new_src = new_abc + '.' + old_src.split('.')[1]
        cmds.connectAttr(new_src, dst, force=True)

    return new_abc

