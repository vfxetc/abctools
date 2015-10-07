from maya import cmds

def load_export_plugin(verbose=False):
    if not cmds.pluginInfo('AbcExport', q=True, loaded=True):
        if verbose:
            print 'Loading AbcExport plugin...'
        cmds.loadPlugin('AbcExport')
