import os
import pathlib
import sys
from PyQt5 import QtCore, QtWidgets, sip
from urllib import parse
from src import jsonc, specification


class Dropper(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PTray')
        self.resize(380, 250)
        self.setAcceptDrops(True)
        self.show_drop_dialog()

    def clear_widget(self):
        def clear_layout(layout):
            while True:
                item = layout.takeAt(0)
                print(item)
                if item == None:
                    break
                if item.layout() != None:
                    clear_layout(item.layout())
                elif item.widget() != None:
                    item.widget().hide()
                    sip.delete(item.widget())
                else:
                    sip.delete(item)
            sip.delete(layout)
        clear_layout(self.layout())

    def show_drop_dialog(self):
        self.setLayout(QtWidgets.QVBoxLayout())
        title = QtWidgets.QLabel()
        title.setText('<h1>Drop specifications here!</h1>')
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout().addWidget(title)

    def show_drop_progress(self, paths, success=(), fails=(), ended=False):
        self.clear_widget()
        self.setLayout(QtWidgets.QVBoxLayout())
        title = QtWidgets.QLabel()
        title.setText(f'<h1>{"Testing specifications" if not ended else "Done"}</h1>')
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.layout().addWidget(title)
        paths_layout = QtWidgets.QFormLayout()
        self.layout().addLayout(paths_layout)

        path_labels = [
            QtWidgets.QLabel(
                f'<font color="{"green" if path in success else "red" if path in fails else "black"}">{path}</font>'
            )
            for path in paths
        ]
        [paths_layout.addWidget(path_label) for path_label in path_labels]

    # drag

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            specification_paths = [parse.urlparse(line).path for line in event.mimeData().text().splitlines()]
            if all(os.path.isfile(file) for file in specification_paths):
                return event.accept()
        event.reject()

    def dropEvent(self, event):
        specification_paths = [parse.urlparse(line).path for line in event.mimeData().text().splitlines()]
        specification_paths.sort()
        self.show_drop_progress(specification_paths)
        successful_paths = []
        failed_paths = []
        for path in specification_paths:
            with open(path) as file:
                try:
                    specification.run_specification(jsonc.loads(file.read()))
                    successful_paths.append(path)
                except:
                    failed_paths.append(path)
            self.show_drop_progress(specification_paths, successful_paths, failed_paths)
        self.show_drop_progress(specification_paths, successful_paths, failed_paths, True)


def main():
    application = QtWidgets.QApplication(sys.argv)
    dropper = Dropper()
    dropper.show()
    sys.exit(application.exec_())


if __name__ == '__main__':
    main()
