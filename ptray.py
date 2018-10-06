import os
import sys
from PyQt5 import QtCore, QtWidgets
from urllib import parse


class Dropper(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('PTray')
        self.resize(380, 250)
        self.setAcceptDrops(True)
        layout = QtWidgets.QGridLayout(self)
        dropper_label = QtWidgets.QLabel(self)
        dropper_label.setText('<h1>Drop specifications here!</h1>')
        dropper_label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignHCenter)
        layout.addWidget(dropper_label, 0, 0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            spec_files = [parse.urlparse(line).path for line in event.mimeData().text().splitlines()]
            if all(os.path.isfile(file) for file in spec_files):
                return event.accept()
        event.reject()

    def dropEvent(self, event):
        spec_files = [parse.urlparse(line).path for line in event.mimeData().text().splitlines()]
        print(spec_files)


def main():
    app = QtWidgets.QApplication(sys.argv)
    dropper = Dropper()
    dropper.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
