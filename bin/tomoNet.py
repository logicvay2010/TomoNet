#!/usr/bin/env python3
import os
import socket

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QListWidgetItem, QListWidget
from PyQt5.QtCore import Qt, QSize

from TomoNet.util import metadata
from TomoNet.gui.motioncor import MotionCor
from TomoNet.gui.ctffind import Ctffind
from TomoNet.gui.manual import Manual
from TomoNet.gui.recon import Recon
from TomoNet.gui.expand import Expand
from TomoNet.gui.autopick import Autopick
from TomoNet.gui.others import OtherUtils

class Ui_TomoNet(object):
    def setupUi(self, TomoNet):
        TomoNet.setObjectName("TomoNet")
        TomoNet.resize(1160, 800)
        self.centralwidget = QtWidgets.QWidget(TomoNet)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.listWidget = QtWidgets.QListWidget(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy)
        self.listWidget.setMaximumSize(QtCore.QSize(180, 16777215))
        self.listWidget.setMinimumSize(QtCore.QSize(180, 16777215))
        self.listWidget.setObjectName("listWidget")
        self.horizontalLayout.addWidget(self.listWidget)
        self.stackedWidget = QtWidgets.QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName("stackedWidget")
        self.horizontalLayout.addWidget(self.stackedWidget)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.log_window = QtWidgets.QTextBrowser(self.centralwidget)
        self.log_window.setObjectName("log_window")
        self.log_window.setMaximumSize(QtCore.QSize(16777215, 720))
        self.gridLayout.addWidget(self.log_window, 1, 0)
        custom_font = QtGui.QFont()
        custom_font.setPointSize(11)
        self.log_window.setCurrentFont(custom_font)
        
        TomoNet.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(TomoNet)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 822, 21))
        self.menubar.setObjectName("menubar")
        TomoNet.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(TomoNet)
        self.statusbar.setObjectName("statusbar")
        TomoNet.setStatusBar(self.statusbar)

        self.retranslateUi(TomoNet)
        
        self.initUi()

        QtCore.QMetaObject.connectSlotsByName(TomoNet)

    def initUi(self):
        self.listWidget.currentRowChanged.connect(self.stackedWidget.setCurrentIndex)
        # Remove the border
        self.listWidget.setFrameShape(QListWidget.NoFrame)
        # Hide scroll bar
        self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        list_names = metadata.LIST_NAMES

        for name in list_names:
            item = QListWidgetItem(name, self.listWidget)
            # Set the default width and height of the item (only height is useful here)
            item.setSizeHint(QSize(16777215, 35))
            # Text centered
            item.setTextAlignment(Qt.AlignCenter)

        self.listWidget.currentRowChanged.connect(self.loadLogs)

        motioncor = MotionCor()
        self.stackedWidget.addWidget(motioncor)

        recon = Recon()
        self.stackedWidget.addWidget(recon)
        
        ctffind = Ctffind()
        self.stackedWidget.addWidget(ctffind)

        manual = Manual()
        self.stackedWidget.addWidget(manual)

        expand = Expand()
        self.stackedWidget.addWidget(expand)

        autopick = Autopick()
        self.stackedWidget.addWidget(autopick)

        otherUtils = OtherUtils()
        self.stackedWidget.addWidget(otherUtils)

        self.log_file = ["MotionCorrection/motion.log", "Recon/recon.log", "Ctffind/ctffind.log",\
            "ManualPick/manual.log", "Expand/expand.log", "Autopick/autopick.log", "OtherUtils/otherUtils.log"]
        self.log_window.setText(self.getLogContent(self.log_file[0]))
        self.log_window.moveCursor(QtGui.QTextCursor.End)

    def retranslateUi(self, TomoNet):
        _translate = QtCore.QCoreApplication.translate
        try:
            TomoNet.setWindowTitle(_translate("TomoNet", "TomoNet ({})".format(socket.gethostname())))
            scriptDir = os.path.dirname(os.path.realpath(__file__))
            icon =  QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("{}/../gui/icons/web.svg".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            TomoNet.setWindowIcon(icon)
        except:
            TomoNet.setWindowTitle(_translate("TomoNet", "TomoNet"))    

    def isValid(self, fileName):
        '''
        returns True if the file exists and can be
        opened.  Returns False otherwise.
        '''
        try:
            file = open(fileName, 'r')
            file.close()
            return True
        except:
            return False    
    
    def getLogContent(self, fileName ):
        '''
        sets the member fileName to the value of the argument
        if the file exists.  Otherwise resets both the filename
        and file contents members.
        '''
        if self.isValid(fileName):
            self.fileName = fileName
            content = open( fileName, 'r' ).read()
            return content
        else:
            return None
    
    def loadLogs(self, row):
        try:
            self.log_window.setText(self.getLogContent(self.log_file[row]))
            self.log_window.moveCursor(QtGui.QTextCursor.End)
            if row == 3:
                self.stackedWidget.widget(row).reload_table()

            custom_font = QtGui.QFont()
            custom_font.setPointSize(11)
            self.log_window.setCurrentFont(custom_font)
            #highlight(self.log_window, "#CC2936", "ERROR")
            #highlight(self.log_window, "#408AF1", "INFO")
            #highlight(self.log_window, "#FC8955", "WARNING")
        except:
            pass

stylesheet = """
QPushButton#run {
    background: rgb(239,221,241);
    font: 14px;
}

QGroupBox{
    font: 12px;
}

QListWidget {
    outline: 0px;
    font: 14px;
    font-weight:bold;
    background: #e5eaf5
}

QTabWidget{
    font: 16px;
    background: rgb(144,160,187)
}

QWidget#tab {
    font: 14px;
    background: rgb(237, 240, 232)
}

QLabel{
    font-weight: bold;
    font: 14px;
}

QComboBox{
    font-weight: bold;
    font: 14px;
}
"""
class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # scriptDir = os.path.dirname(os.path.realpath(__file__))
        # icon =  QtGui.QIcon()
        # print("{}/../gui/icons/icon_folder.png".format(scriptDir))
        # icon.addPixmap(QtGui.QPixmap("{}/../gui/icons/spider.svg".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        # app.setWindowIcon(icon)
    def closeEvent(self, event):
        result = QtWidgets.QMessageBox.question(self,
                        "Confirm Exit...",
                        "Do you want to exit? ",
                        QtWidgets.QMessageBox.Yes| QtWidgets.QMessageBox.No)
        event.ignore()
        if result == QtWidgets.QMessageBox.Yes:
            event.accept()
        if result == QtWidgets.QMessageBox.No:
            pass
            #kill the old process
def check_root():
    directory = os.getcwd()
    folders = os.listdir(directory)
    return "MotionCorrection" in folders and "Recon" in folders and "Ctffind" in folders and "Expand" in folders and "Autopick" in folders and "OtherUtils" in folders

from PyQt5.QtWidgets import QMessageBox

if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # scriptDir = os.path.dirname(os.path.realpath(__file__))
    # icon =  QtGui.QIcon()
    # print("{}/../gui/icons/icon_folder.png".format(scriptDir))
    # icon.addPixmap(QtGui.QPixmap("{}/../gui/icons/spider.svg".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
    # app.setWindowIcon(icon)
    app.setStyleSheet(stylesheet)
    
    MainWindow = MyWindow()
    if not check_root():
        ret = QMessageBox.question(None, 'Notice!', "Are you sure to launch tomoNet in the current folder?\n", QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)        
    else:
        ret = QMessageBox.Yes
    
    if ret == QMessageBox.Yes:
        ui = Ui_TomoNet()
        ui.setupUi(MainWindow)
        #MainWindow.setFixedWidth(1120)
        #MainWindow.setFixedHeight(800)
        MainWindow.show()
        sys.exit(app.exec_())

        
    
