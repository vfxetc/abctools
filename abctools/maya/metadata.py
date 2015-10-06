import json

from maya import cmds


def create_metadata_transform(metadata, prefix='__ksmeta__'):

    prop_prefix = 'ksmeta'
    
    transform = cmds.createNode('transform', name=prefix, skipSelect=True)

    try:
        for key, value in metadata.iteritems():
            attr = '%s_json_%s' % (prop_prefix, key)
            cmds.addAttr(transform, longName=attr, dataType='string')
            cmds.setAttr('%s.%s' % (transform, attr), json.dumps(value), type='string')

    except:
        # Clean up if we didn't manage to create everything.
        cmds.delete(transform)
        raise

    return transform
