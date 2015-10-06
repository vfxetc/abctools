from maya import cmds

from .metadata import create_metadata_transform


def export(file, metadata=None, metadata_prefix='__ksmeta__', **kwargs):

    job = ['-file', file]

    for key, value in kwargs.iteritems():
        if value is True:
            job.append('-%s' % key)
        elif isinstance(value, (tuple, list)):
            for v in value:
                job.extend(('-' + key, v))
        else:
            job.extend(('-' + key, value))

    if metadata:
        metadata_transform = create_metadata_transform(metadata, prefix=metadata_prefix)

        # If we are only exporting the selection, then we must include
        # the metadata object in it.
        if kwargs.get('sl') or kwargs.get('selection'):
            cmds.select(metadata_transform, add=True)

        # This attribute prefix is currently hardcoded into create_metadata_transform.
        job.extend(('-userAttrPrefix', 'ksmeta_'))

    try:
        cmds.AbcExport(j=' '.join(job))

    finally:
        if metadata:
            cmds.delete(metadata_transform)

