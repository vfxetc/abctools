
import maya.cmds as cmds
import pprint
import yaml

def find_objects(object_list):
    object_mapping = {}

    for key, item in object_list.items():
        if cmds.objExists(key):
            object_mapping[key] = key
            continue

        for name in item['alternative_names']:
            if cmds.objExists(name):
                object_mapping[key] = name
                break

    return object_mapping

def import_tracking_sets(path):
    tracking_sets = yaml.load(file(path, 'r'))

    object_mapping = find_objects(tracking_sets['objects'])

    pprint.pprint(tracking_sets)
    print object_mapping

    for track in tracking_sets['tracks']:

        sets_name = "__tracker__%s" % track['tracker_name']

        members = []
        for m in track['tracking_points']:
            attr = "%s.vtx[%d]" % (object_mapping[m[0]], m[1])
            members.append(attr)

        cmds.sets(members, name=sets_name)