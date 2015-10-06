import json
import re

from . import cask


def load(archive, prefix='__ksmeta__'):

    prop_prefix = 'ksmeta'
    metadata = {}

    if isinstance(archive, basestring):
        archive = cask.Archive(archive)

    for name, obj in archive.top.children.iteritems():

        if not name.startswith(prefix):
            continue

        for prop_key in '.userProperties', '.arbGeomParams':

            try:
                props = obj.properties['.xform/%s' % prop_key]
            except KeyError:
                continue

            for key, prop in props.properties.iteritems():

                m = re.match(r'^%s_(json)_(\w+)$' % prop_prefix, key)
                if not m:
                    continue

                type_, name = m.groups()
                value = prop.get_value()

                # arbGeomParams returns a imath.StringArray
                if not isinstance(value, basestring):
                    value = value[0]

                if type_ == 'json':
                    value = json.loads(value)
                else:
                    raise ValueError('unknown serialization method: %s' % type_)

                metadata[name] = value

    return metadata


if __name__ == '__main__':

    import sys
    print json.dumps(load(sys.argv[1]), indent=4, sort_keys=True)
