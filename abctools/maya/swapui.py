import functools

from maya import cmds
from uitools.qt import Q, QtGui

from .swap import swap_path


def iter_abc_nodes():
    for node in cmds.ls(type='AlembicNode'):
        path = cmds.getAttr(node + '.abc_File')
        cons = cmds.listConnections(node, plugs=True, connections=True)
        num_meshes = len([1 for c in cons if c.endswith('.inMesh')])
        yield node, num_meshes, path


class Dialog(QtGui.QDialog):

    def __init__(self):
        super(Dialog, self).__init__()

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)

        nodes = list(iter_abc_nodes())
        if not nodes:
            raise ValueError('no Alembic nodes')

        for node, num_meshes, path in sorted(nodes):

            label1 = QtGui.QLabel('%s (%s)' % (node, num_meshes))
            layout.addWidget(label1)

            label2 = QtGui.QLabel(path)
            layout.addWidget(label2)

            button = QtGui.QPushButton('Replace')
            button.clicked.connect(functools.partial(self.replace_clicked, node))
            if not num_meshes:
                button.setEnabled(False)
            layout.addWidget(button)

    def replace_clicked(self, node):

        #new_path = QtGui.QFileDialog.getOpenFileName(filter='Alembic (*.abc)')

        basicFilter = "Alembic (*.abc)"
        new_path = cmds.fileDialog2(fileFilter=basicFilter, fileMode=1, dialogStyle=2)
        if not new_path:
            return
        new_path = new_path[0]

        swap_path(node, new_path)

        self.close()







def run():

    dialog = Dialog()
    dialog.exec_()

