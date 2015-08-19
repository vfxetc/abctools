import maya.cmds as cmds
import pprint
import yaml

def export_tracking_sets(sets, dest_yml):

    data = {}
    tracks = []
    objects = {}
    for set_name in sets:
        clean_name = set_name.split("__")[-1]

        # print clean_name
        tracking_points = []

        for item in  cmds.sets(set_name, q = True) or []:
            # print "   ", item
            object_name = item.split('.')[0]
            point_index = item.split('.')[-1].split('[')[-1].rstrip(']')

            tracking_points.append((object_name, int(point_index)))

            if object_name not in objects:
                objects[object_name] = {'alternative_names': []}

        if tracking_points:
            tracks.append({'tracker_name': clean_name, 'tracking_points':tracking_points})

    data['tracks'] = tracks
    data['objects'] = objects

    pprint.pprint(data)

    with open(dest_yml, 'w') as f:
        f.write(yaml.safe_dump(data))
