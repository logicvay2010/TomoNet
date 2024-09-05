import os, glob, logging
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
try:
    matplotlib.use('TkAgg')
except:
    "no tkinter detected, suggest to install it by run in terminal < sudo apt install python3-tk >"

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTabWidget, QHeaderView, QMessageBox, QTableWidgetItem

from TomoNet.util import metadata, browse
from TomoNet.util.utils import string2float, string2int
from TomoNet.process.bash_cttfind import Ctffind4

class Ctffind(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="Ctffind/ctffind.setting"
        
        self.log_file = "Ctffind/ctffind.log"
        
        self.check_log_file("Ctffind")

        self.ctffind4_path = "Ctffind"

        self.ts_tlt_folder ="Recon/ts_tlt"

        self.recon_folder ="Recon"

        self.thread_ctffind = None

        self.ctf_results = None

        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        self.fileSystemWatcher = QtCore.QFileSystemWatcher(self)
        self.fileSystemWatcher.addPath(self.log_file)
        self.fileSystemWatcher.fileChanged.connect(self.update_log_window)

        self.setupUi()

        self.read_settting()

    def setupUi(self):
        scriptDir = os.path.dirname(os.path.realpath(__file__))

        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")     
        
        #horizontalLayout_1
        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 0, 10, 1)

        self.label_ts_tlt_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_ts_tlt_folder.sizePolicy().hasHeightForWidth())
        self.label_ts_tlt_folder.setSizePolicy(sizePolicy)
        self.label_ts_tlt_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_ts_tlt_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_ts_tlt_folder.setObjectName("label_ts_tlt_folder")
        self.horizontalLayout_1.addWidget(self.label_ts_tlt_folder)

        self.lineEdit_ts_tlt_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_ts_tlt_folder.setInputMask("")
        self.lineEdit_ts_tlt_folder.setObjectName("lineEdit_ts_tlt_folder")

        self.horizontalLayout_1.addWidget(self.lineEdit_ts_tlt_folder)

        self.pushButton_ts_tlt_folder = QtWidgets.QPushButton(self.tab)
        self.pushButton_ts_tlt_folder.setText("")
        self.pushButton_ts_tlt_folder.setIcon(icon)
        self.pushButton_ts_tlt_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_ts_tlt_folder.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_ts_tlt_folder.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_ts_tlt_folder.setObjectName("pushButton_ts_tlt_folder")
        self.horizontalLayout_1.addWidget(self.pushButton_ts_tlt_folder)
        
        self.horizontalLayout_1_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1_2.setContentsMargins(10, 0, 10, 1)
        self.label_ctffind_exe = QtWidgets.QLabel(self.tab)
        self.label_ctffind_exe.setSizePolicy(sizePolicy)
        self.label_ctffind_exe.setMinimumSize(QtCore.QSize(120, 0))
        self.label_ctffind_exe.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_ctffind_exe.setObjectName("label_ctffind_exe")
        self.horizontalLayout_1_2.addWidget(self.label_ctffind_exe)

        self.lineEdit_ctffind_exe = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_ctffind_exe.setInputMask("")
        self.lineEdit_ctffind_exe.setObjectName("lineEdit_ctffind_exe")

        self.horizontalLayout_1_2.addWidget(self.lineEdit_ctffind_exe)

        self.pushButton_ctffind_exe = QtWidgets.QPushButton(self.tab)
        self.pushButton_ctffind_exe.setText("")
        self.pushButton_ctffind_exe.setIcon(icon)
        self.pushButton_ctffind_exe.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_ctffind_exe.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_ctffind_exe.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_ctffind_exe.setObjectName("pushButton_ctffind_exe")
        self.horizontalLayout_1_2.addWidget(self.pushButton_ctffind_exe)

        self.label_cpu_num = QtWidgets.QLabel(self.tab)
        self.label_cpu_num.setSizePolicy(sizePolicy)
        self.label_cpu_num.setMinimumSize(QtCore.QSize(50, 0))
        self.label_cpu_num.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_cpu_num.setObjectName("label_cpu_num")
        self.horizontalLayout_1_2.addWidget(self.label_cpu_num)
        self.lineEdit_cpu_num = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_cpu_num.setMaximumSize(QtCore.QSize(60, 30))
        self.lineEdit_cpu_num.setInputMask("")
        self.lineEdit_cpu_num.setObjectName("lineEdit_cpu_num")
        self.horizontalLayout_1_2.addWidget(self.lineEdit_cpu_num)

        self.label_only_unfinished = QtWidgets.QLabel(self.tab)
        self.label_only_unfinished.setSizePolicy(sizePolicy)
        self.label_only_unfinished.setMinimumSize(QtCore.QSize(120, 0))
        self.label_only_unfinished.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_only_unfinished.setObjectName("label_only_unfinished")
        self.horizontalLayout_1_2.addWidget(self.label_only_unfinished)
        self.comboBox_only_unfinished = QtWidgets.QComboBox(self.tab)
        self.comboBox_only_unfinished.setObjectName("comboBox_only_unfinished")
        self.comboBox_only_unfinished.addItem("")
        self.comboBox_only_unfinished.addItem("")
        self.horizontalLayout_1_2.addWidget(self.comboBox_only_unfinished)

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(10, 0, 10, 1)
        self.label_apix = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_apix.sizePolicy().hasHeightForWidth())
        self.label_apix.setSizePolicy(sizePolicy)
        self.label_apix.setMinimumSize(QtCore.QSize(110, 0))
        self.label_apix.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_apix.setObjectName("label_apix")
        self.horizontalLayout_2.addWidget(self.label_apix)
        self.lineEdit_apix = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_apix.setInputMask("")
        self.lineEdit_apix.setObjectName("lineEdit_apix")
        self.horizontalLayout_2.addWidget(self.lineEdit_apix)
        
        self.label_voltage = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_voltage.sizePolicy().hasHeightForWidth())
        self.label_voltage.setSizePolicy(sizePolicy)
        self.label_voltage.setMinimumSize(QtCore.QSize(70, 0))
        self.label_voltage.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_voltage.setObjectName("label_voltage")
        self.horizontalLayout_2.addWidget(self.label_voltage)
        self.lineEdit_voltage = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_voltage.setInputMask("")
        self.lineEdit_voltage.setObjectName("lineEdit_voltage")
        self.horizontalLayout_2.addWidget(self.lineEdit_voltage)

        self.label_cs = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_cs.sizePolicy().hasHeightForWidth())
        self.label_cs.setSizePolicy(sizePolicy)
        self.label_cs.setMinimumSize(QtCore.QSize(30, 0))
        self.label_cs.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_cs.setObjectName("label_cs")
        self.horizontalLayout_2.addWidget(self.label_cs)
        self.lineEdit_cs = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_cs.setInputMask("")
        self.lineEdit_cs.setObjectName("lineEdit_cs")
        self.horizontalLayout_2.addWidget(self.lineEdit_cs)

        self.label_amp = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_amp.sizePolicy().hasHeightForWidth())
        self.label_amp.setSizePolicy(sizePolicy)
        self.label_amp.setMinimumSize(QtCore.QSize(150, 0))
        self.label_amp.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_amp.setObjectName("label_amp")
        self.horizontalLayout_2.addWidget(self.label_amp)
        self.lineEdit_amp = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_amp.setInputMask("")
        self.lineEdit_amp.setObjectName("lineEdit_amp")
        self.horizontalLayout_2.addWidget(self.lineEdit_amp)

        self.label_pow_size = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_pow_size.sizePolicy().hasHeightForWidth())
        self.label_pow_size.setSizePolicy(sizePolicy)
        self.label_pow_size.setMinimumSize(QtCore.QSize(40, 0))
        self.label_pow_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_pow_size.setObjectName("label_pow_size")
        self.horizontalLayout_2.addWidget(self.label_pow_size)
        self.lineEdit_pow_size = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_pow_size.setInputMask("")
        self.lineEdit_pow_size.setObjectName("lineEdit_pow_size")
        self.horizontalLayout_2.addWidget(self.lineEdit_pow_size)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(10, 0, 10, 1)

        self.label_min_res = QtWidgets.QLabel(self.tab)
        self.label_min_res.setSizePolicy(sizePolicy)
        self.label_min_res.setMinimumSize(QtCore.QSize(60, 0))
        self.label_min_res.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_res.setObjectName("label_min_res")
        self.horizontalLayout_3.addWidget(self.label_min_res)
        self.lineEdit_min_res = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_min_res.setInputMask("")
        self.lineEdit_min_res.setObjectName("lineEdit_min_res")
        self.horizontalLayout_3.addWidget(self.lineEdit_min_res)

        self.label_max_res = QtWidgets.QLabel(self.tab)
        self.label_max_res.setSizePolicy(sizePolicy)
        self.label_max_res.setMinimumSize(QtCore.QSize(70, 0))
        self.label_max_res.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_max_res.setObjectName("label_max_res")
        self.horizontalLayout_3.addWidget(self.label_max_res)
        self.lineEdit_max_res = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_max_res.setInputMask("")
        self.lineEdit_max_res.setObjectName("lineEdit_max_res")
        self.horizontalLayout_3.addWidget(self.lineEdit_max_res)

        self.label_min_defocus = QtWidgets.QLabel(self.tab)
        self.label_min_defocus.setSizePolicy(sizePolicy)
        self.label_min_defocus.setMinimumSize(QtCore.QSize(100, 0))
        self.label_min_defocus.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_defocus.setObjectName("label_min_defocus")
        self.horizontalLayout_3.addWidget(self.label_min_defocus)
        self.lineEdit_min_defocus = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_min_defocus.setInputMask("")
        self.lineEdit_min_defocus.setObjectName("lineEdit_min_defocus")
        self.horizontalLayout_3.addWidget(self.lineEdit_min_defocus)

        self.label_max_defocus = QtWidgets.QLabel(self.tab)
        self.label_max_defocus.setSizePolicy(sizePolicy)
        self.label_max_defocus.setMinimumSize(QtCore.QSize(100, 0))
        self.label_max_defocus.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_max_defocus.setObjectName("label_max_defocus")
        self.horizontalLayout_3.addWidget(self.label_max_defocus)
        self.lineEdit_max_defocus = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_max_defocus.setInputMask("")
        self.lineEdit_max_defocus.setObjectName("lineEdit_max_defocus")
        self.horizontalLayout_3.addWidget(self.lineEdit_max_defocus)

        self.label_defocus_step = QtWidgets.QLabel(self.tab)
        self.label_defocus_step.setSizePolicy(sizePolicy)
        self.label_defocus_step.setMinimumSize(QtCore.QSize(110, 0))
        self.label_defocus_step.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_defocus_step.setObjectName("label_defocus_step")
        self.horizontalLayout_3.addWidget(self.label_defocus_step)
        self.lineEdit_defocus_step = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_defocus_step.setInputMask("")
        self.lineEdit_defocus_step.setObjectName("lineEdit_defocus_step")
        self.horizontalLayout_3.addWidget(self.lineEdit_defocus_step)

        self.horizontalLayout_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last.setObjectName("horizontalLayout_last")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem1)
        self.pushButton_run_ctffind = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_run_ctffind.sizePolicy().hasHeightForWidth())
        self.pushButton_run_ctffind.setSizePolicy(sizePolicy)
        self.pushButton_run_ctffind.setMinimumSize(QtCore.QSize(72, 36))
        self.pushButton_run_ctffind.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_run_ctffind.setObjectName("run")
        self.horizontalLayout_last.addWidget(self.pushButton_run_ctffind)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem2)

        self.gridLayout_ctffind4 = QtWidgets.QGridLayout(self.tab)

        self.gridLayout_ctffind4.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_ctffind4.addLayout(self.horizontalLayout_1_2, 1, 0, 1, 1)
        self.gridLayout_ctffind4.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)
        self.gridLayout_ctffind4.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)

        #self.spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #self.gridLayout_ctffind4.addItem(self.spacerItem3, 4, 0, 1, 1)

        self.gridLayout_ctffind4.addLayout(self.horizontalLayout_last, 4, 0, 1, 1)

        self.addTab(self.tab, "Ctffind4")

        #self.tab2 = QtWidgets.QWidget()
        #self.tab2.setObjectName("tab")

        self.horizontalLayout_summary = QtWidgets.QHBoxLayout()
        self.horizontalLayout_summary.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_summary.setObjectName("horizontalLayout_summary")

        self.label_recon = QtWidgets.QLabel(self.tab)
        self.label_recon.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_recon.setAlignment(QtCore.Qt.AlignCenter)
        self.label_recon.setObjectName("label_recon")
        self.label_recon.setText("Summary of CTFFIND Defocus Estimation")
        self.horizontalLayout_summary.addWidget(self.label_recon)
        self.pushButton_reload = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.pushButton_reload.setSizePolicy(sizePolicy)
        self.pushButton_reload.setMinimumSize(QtCore.QSize(60, 20))
        self.pushButton_reload.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_reload.setObjectName("pushButton_reload")
        self.horizontalLayout_summary.addWidget(self.pushButton_reload)

        self.tableView = QtWidgets.QTableWidget(self)

        header_labels = metadata.header_labels_ctffind
        self.tableView.setColumnCount(len(header_labels))
        self.tableView.setHorizontalHeaderLabels(header_labels)

        header = self.tableView.horizontalHeader()   
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

        #self.gridLayout_result = QtWidgets.QGridLayout(self.tab)

        self.gridLayout_ctffind4.addLayout(self.horizontalLayout_summary, 5, 0, 1, 1)
        self.gridLayout_ctffind4.addWidget(self.tableView, 6, 0)

        #self.addTab(self.tab, "Results")

        self.lineEdit_ts_tlt_folder.textChanged.connect(self.save_setting)
        self.lineEdit_ctffind_exe.textChanged.connect(self.save_setting)
        self.lineEdit_cpu_num.textChanged.connect(self.save_setting)
        self.lineEdit_apix.textChanged.connect(self.save_setting)
        self.lineEdit_voltage.textChanged.connect(self.save_setting)
        self.lineEdit_cs.textChanged.connect(self.save_setting)
        self.lineEdit_amp.textChanged.connect(self.save_setting)
        self.lineEdit_pow_size.textChanged.connect(self.save_setting)
        self.lineEdit_min_res.textChanged.connect(self.save_setting)
        self.lineEdit_max_res.textChanged.connect(self.save_setting)
        self.lineEdit_min_defocus.textChanged.connect(self.save_setting)
        self.lineEdit_max_defocus.textChanged.connect(self.save_setting)
        self.lineEdit_defocus_step.textChanged.connect(self.save_setting)
       
        self.pushButton_ts_tlt_folder.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_ts_tlt_folder, location=self.recon_folder)) 
        self.pushButton_ctffind_exe.clicked.connect\
            (lambda: browse.browseSlot (self.lineEdit_ctffind_exe, location='/')) 

        self.pushButton_run_ctffind.clicked.connect(self.ctffind4)
        self.pushButton_reload.clicked.connect(self.reload_table)

        self.currentChanged.connect(self.tab_changed)

        self.tableView.doubleClicked.connect(self.table_click)
        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.retranslateUi()

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_ts_tlt_folder.setText(_translate("Form", "Tilt series folder:"))
        self.lineEdit_ts_tlt_folder.setPlaceholderText(_translate("Form", \
            "Recon/ts_tlt"))
        self.lineEdit_ts_tlt_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Path to the folder stores stacked tilt series. Default: 'Recon/ts_tlt'.\
            </span></p></body></html>"))
        
        self.label_ctffind_exe.setText(_translate("Form", "Ctffind Executable:"))
        self.lineEdit_ctffind_exe.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Your/Path/To/ctffind/bin/ctffind\
            </span></p></body></html>"))
        
        self.label_cpu_num.setText(_translate("Form", "CPU #:"))
        self.lineEdit_cpu_num.setPlaceholderText(_translate("Form", "8"))
        self.lineEdit_cpu_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">CPU(s) # to be used. Default: 8.\
            </span></p></body></html>"))
        
        self.label_apix.setText(_translate("Form", "Pixel Size (Å):"))
        #self.lineEdit_apix.setPlaceholderText(_translate("Form", "1.0"))
        self.lineEdit_apix.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Pixel size (Å).\
            </span></p></body></html>"))
        
        self.label_only_unfinished.setText(_translate("Form", "Only Process Unfinished Data?:"))
        self.comboBox_only_unfinished.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_only_unfinished.setItemText(1, _translate("Form", "No"))
        self.comboBox_only_unfinished.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Select Yes to skip generating CTFFIND result that already processed.\
            Select No to generate all CTFFIND result and overwrite the existing output.\
            The processed data info is recorded in file: Ctffind/history_record.txt, user can edit this file based on needs.\
            Default: Yes.\
            </span></p></body></html>"))
        
        self.label_voltage.setText(_translate("Form", "Voltage:"))
        self.lineEdit_voltage.setPlaceholderText(_translate("Form","300"))
        self.lineEdit_voltage.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Voltage (kv). Default: 300.\
            </span></p></body></html>"))
        
        self.label_cs.setText(_translate("Form", "CS:"))
        self.lineEdit_cs.setPlaceholderText(_translate("Form", \
            "2.7"))
        self.lineEdit_cs.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Spherical aberration. Default: 2.7.\
            </span></p></body></html>"))
        
        self.label_amp.setText(_translate("Form", "Amplitude contrast:"))
        self.lineEdit_amp.setPlaceholderText(_translate("Form", \
            "0.1"))
        self.lineEdit_amp.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Amplitude contrast.Default: 0.1.\
            </span></p></body></html>"))
        
        self.label_pow_size.setText(_translate("Form", "Size:"))
        self.lineEdit_pow_size.setPlaceholderText(_translate("Form", \
            "512"))
        self.lineEdit_pow_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Size of power spectrum. Default: 512.\
            </span></p></body></html>"))
        
        self.label_min_res.setText(_translate("Form", "Min res:"))
        self.lineEdit_min_res.setPlaceholderText(_translate("Form", \
            "50.0"))
        self.lineEdit_min_res.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Min resolution. Default: 50.0.\
            </span></p></body></html>"))
        
        self.label_max_res.setText(_translate("Form", "Max res:"))
        self.lineEdit_max_res.setPlaceholderText(_translate("Form", \
            "5.0"))
        self.lineEdit_max_res.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Max resolution. Default: 5.0.\
            </span></p></body></html>"))
        
        self.label_min_defocus.setText(_translate("Form", "Min defocus:"))
        self.lineEdit_min_defocus.setPlaceholderText(_translate("Form", \
            "5000.0"))
        self.lineEdit_min_defocus.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Min defocus. Default: 5000.0.\
            </span></p></body></html>"))
        
        self.label_max_defocus.setText(_translate("Form", "Max defocus:"))
        self.lineEdit_max_defocus.setPlaceholderText(_translate("Form", \
            "50000.0"))
        self.lineEdit_max_defocus.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Max defocus. Default: 50000.0.\
            </span></p></body></html>"))
        
        self.label_defocus_step.setText(_translate("Form", "Defocus step:"))
        self.lineEdit_defocus_step.setPlaceholderText(_translate("Form", \
            "500.0"))
        self.lineEdit_defocus_step.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Defocus search step. Default: 500.0.\
            </span></p></body></html>"))

        self.pushButton_run_ctffind.setText(_translate("Form", "RUN"))

        self.pushButton_reload.setText(_translate("Form", "Reload"))

    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 2:
                    in_current_page = False
            elif x.objectName() == "log_window":
                if in_current_page:
                    self.log_window = x
                    self.log_window.setText(self.getLogContent(txt))
                    self.log_window.moveCursor(QtGui.QTextCursor.End)

                    custom_font = QtGui.QFont()
                    custom_font.setPointSize(11)
                    self.log_window.setCurrentFont(custom_font)

    def read_settting(self):
        if not os.path.exists(self.setting_file):
            try:
                f = open(self.setting_file)
            except:
                pass        
        data = {}
        data['lineEdit_ts_tlt_folder'] = ""
        data['lineEdit_ctffind_exe'] = ""
        data['lineEdit_cpu_num'] = ""
        data['only_unfinished'] = "Yes"
        data['lineEdit_apix'] = "" 
        data['lineEdit_voltage'] = ""
        data['lineEdit_cs'] = ""         
        data['lineEdit_amp'] = "" 
        data['lineEdit_pow_size'] = ""
        data['lineEdit_min_res'] = ""
        data['lineEdit_max_res'] = ""
        data['lineEdit_min_defocus'] = "" 
        data['lineEdit_max_defocus'] = "" 
        data['lineEdit_defocus_step'] = "" 

        try:
            with open(self.setting_file) as f:
                for line in f:
                    (k, v) = line.split(":")
                    if v.strip() == "True":
                        data[k] = True
                    elif v.strip() == "False":
                        data[k] = False
                    else:
                        data[k] = v.strip()
        except:
            pass
        self.lineEdit_ts_tlt_folder.setText(data['lineEdit_ts_tlt_folder'])
        self.lineEdit_ctffind_exe.setText(data['lineEdit_ctffind_exe'])
        self.lineEdit_cpu_num.setText(data['lineEdit_cpu_num'])
        self.comboBox_only_unfinished.setCurrentText(data['only_unfinished'])
        self.lineEdit_apix.setText(data['lineEdit_apix'])
        self.lineEdit_cs.setText(data['lineEdit_cs'])
        self.lineEdit_voltage.setText(data['lineEdit_voltage'])
        self.lineEdit_amp.setText(data['lineEdit_amp'])
        self.lineEdit_pow_size.setText(data['lineEdit_pow_size'])
        self.lineEdit_min_res.setText(data['lineEdit_min_res'])
        self.lineEdit_max_res.setText(data['lineEdit_max_res'])
        self.lineEdit_min_defocus.setText(data['lineEdit_min_defocus'])
        self.lineEdit_max_defocus.setText(data['lineEdit_max_defocus'])
        self.lineEdit_defocus_step.setText(data['lineEdit_defocus_step'])
    
    def save_setting(self):
        param = {}
        param['lineEdit_ts_tlt_folder'] = self.lineEdit_ts_tlt_folder.text()
        param['lineEdit_ctffind_exe'] = self.lineEdit_ctffind_exe.text()
        param['lineEdit_cpu_num'] = self.lineEdit_cpu_num.text()
        param['only_unfinished'] = self.comboBox_only_unfinished.currentText()
        param['lineEdit_apix'] = self.lineEdit_apix.text()
        param['lineEdit_cs'] = self.lineEdit_cs.text()
        param['lineEdit_voltage'] = self.lineEdit_voltage.text()
        param['lineEdit_amp'] = self.lineEdit_amp.text()
        param['lineEdit_pow_size'] = self.lineEdit_pow_size.text()
        param['lineEdit_min_res'] = self.lineEdit_min_res.text()
        param['lineEdit_max_res'] = self.lineEdit_max_res.text()
        param['lineEdit_min_defocus'] = self.lineEdit_min_defocus.text()
        param['lineEdit_max_defocus'] = self.lineEdit_max_defocus.text()
        param['lineEdit_defocus_step'] = self.lineEdit_defocus_step.text()

        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))     

    def natural_keys(self, text):
        return int(text.split("_")[-1]) 

    def read_ctffind_result(self):

        searchPath = self.ctffind4_path

        files = sorted(glob.glob("{}/*".format(searchPath)))

        tomoNames = []
        for f in files:
            if os.path.isdir(f) :
                tomoName = f.split('/')[-1]
                if os.path.isfile("{}/{}_ctf.txt".format(f, tomoName)):
                    tomoNames.append(tomoName)
        try:
            tomoNames.sort(key=self.natural_keys)
        except:
            pass

        results = {}
        tilt_nums = []
        defocus = []
        best_ctf_rings = []
        for tomoName in tomoNames:
            ctf_txt_file = "{}/{}/{}_ctf.txt".format(searchPath, tomoName, tomoName)
            with open(ctf_txt_file) as f:
                lines = [line.rstrip() for line in f]

            newlines = []           
            for line in lines:
                if not line.startswith("#"):
                    newlines.append(line)

            first_column = [int(float(l.split()[0])) for l in newlines]

            try:
                defoci_1 = np.array([int(float(l.split()[1])) for l in newlines])
                defoci_2 = np.array([int(float(l.split()[2])) for l in newlines])
                defoci = (defoci_1 + defoci_2)//2
                
                tilt_num = first_column[-1] if len(first_column) > 0 else 0
                tilt_nums.append(tilt_num)
                defocus.append(defoci)

                best_fit = np.array([round(float(l.split()[6]),1) for l in newlines])
                best_ctf_rings.append(best_fit)
            except:
                tomoNames.remove(tomoName)
        results['tomoNames'] = tomoNames
        results['tilt_nums'] = tilt_nums
        results['defocus'] = defocus
        results['best_ctf_rings'] = best_ctf_rings
        
        return results
    
    def reload_table(self):
        results = self.read_ctffind_result()
        tomoNames = results['tomoNames']
        tilt_nums = results['tilt_nums']
        defocus = results['defocus']
        best_ctf_rings = results['best_ctf_rings']
        self.ctf_results = results
        self.tableView.setRowCount(0)
        self.tableView.setRowCount(len(tomoNames))
        if len(tomoNames) > 0:
            for i, tomo in enumerate(tomoNames):
                self.tableView.setItem(i, 0, QTableWidgetItem(tomo))
                tilt_num_i = str(tilt_nums[i])
                action_defocus = QTableWidgetItem(tilt_num_i)
                action_defocus.setBackground(QtGui.QColor("#4CAF50"))
                action_defocus.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 1, action_defocus)

                defoci = defocus[i][len(defocus[i])//2] if len(defocus[i]) > 0 else 'NA'
                action_plot_1 = QTableWidgetItem(str(defoci))
                action_plot_1.setBackground(QtGui.QColor("#008CBA"))
                action_plot_1.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 2, action_plot_1)

                best_ctf_fit = min(best_ctf_rings[i]) if len(best_ctf_rings[i]) > 0 else 'NA'
                action_plot_2 = QTableWidgetItem(str(best_ctf_fit))
                action_plot_2.setBackground(QtGui.QColor("#a0d2eb"))
                action_plot_2.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 3, action_plot_2)

                action_plot_3 = QTableWidgetItem("Plot all tilt")
                action_plot_3.setBackground(QtGui.QColor("#f75990"))
                action_plot_3.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 4, action_plot_3)

                action_plot_4 = QTableWidgetItem("Plot Thon-ring")
                action_plot_4.setBackground(QtGui.QColor("#d0bdf4"))
                action_plot_4.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 5, action_plot_4)

    def list_row_changed(self, i):
        if i == 2:
            self.reload_table()
    ##### 2023/06/06 to be changed to adapt ctffind section
    def get_params(self):
        
        if not len(self.lineEdit_ts_tlt_folder.text()) > 0:
            #return "Please provide path to your tilt series folder!"
            ts_tlt_folder = self.ts_tlt_folder
        else:
            ts_tlt_folder = self.lineEdit_ts_tlt_folder.text()

        if not len(self.lineEdit_ctffind_exe.text()) > 0:
            return "Please provide path to your ctffind executable!"
        else:
            ctffind_exe = self.lineEdit_ctffind_exe.text()
        
        if len(self.lineEdit_cpu_num.text()) > 0:
            cpu_num = string2int(self.lineEdit_cpu_num.text())
            if not cpu_num:
                return "cpu number must be a interger!"
        else: 
            cpu_num = 8

        only_unfinished = self.comboBox_only_unfinished.currentText()
        if only_unfinished == "No":
            only_unfinished = 0
        else:
            only_unfinished = 1
        

        if len(self.lineEdit_apix.text()) > 0:
            apix = string2float(self.lineEdit_apix.text(),3)
            if not apix:
                return "pixel size should be in decimal format!"
        else: 
            return "Please provide the pixel size of input TS!"
            #apix = 1.0

        if len(self.lineEdit_voltage.text()) > 0:
            voltage = string2int(self.lineEdit_voltage.text())
            if not voltage:
                return "voltage must be a interger!"
        else: 
            voltage = 300

        if len(self.lineEdit_cs.text()) > 0:
            cs = string2float(self.lineEdit_cs.text(),2)
            if not cs:
                return "cs should be in decimal format!"
        else: 
            cs = 2.7

        if len(self.lineEdit_amp.text()) > 0:
            amp = string2float(self.lineEdit_amp.text(), 2)
            if not amp:
                return "amplitude contrast should be in decimal format!"
        else: 
            amp = 0.1

        if len(self.lineEdit_pow_size.text()) > 0:
            pow_size = string2int(self.lineEdit_pow_size.text())
            if not pow_size:
                return "the size of power spectrum must be a interger, like 256, 512 or 1024!"
        else: 
            pow_size = 512

        if len(self.lineEdit_min_res.text()) > 0:
            min_res = string2float(self.lineEdit_min_res.text(), 1)
            if not min_res:
                return "min resolution should be in decimal format!"
        else: 
            min_res = 50.0

        if len(self.lineEdit_max_res.text()) > 0:
            max_res = string2float(self.lineEdit_max_res.text(), 1)
            if not max_res:
                return "max resolution should be in decimal format!"
        else: 
            max_res = 5.0

        if len(self.lineEdit_min_defocus.text()) > 0:
            min_defocus = string2float(self.lineEdit_min_defocus.text(), 1)
            if not min_defocus:
                return "min defocus should be in decimal format!"
        else: 
            min_defocus = 5000.0

        if len(self.lineEdit_max_defocus.text()) > 0:
            max_defocus = string2float(self.lineEdit_max_defocus.text(), 1)
            if not max_defocus:
                return "max defocus should be in decimal format!"
        else: 
            max_defocus = 50000.0

        if len(self.lineEdit_defocus_step.text()) > 0:
            defocus_step = string2float(self.lineEdit_defocus_step.text(), 1)
            if not defocus_step:
                return "defocus step should be in decimal format!"
        else: 
            defocus_step = 500.0

        params = {}
        params['ts_tlt_folder'] = ts_tlt_folder
        params['ctffind_exe'] = ctffind_exe
        params['cpu_num'] = cpu_num
        params['only_unfinished'] = only_unfinished
        only_unfinished
        params['apix'] = apix
        params['voltage'] = voltage
        params['cs'] = cs
        params['amp'] = amp
        params['pow_size'] = pow_size
        params['min_res'] = min_res
        params['max_res'] = max_res
        params['min_defocus'] = min_defocus
        params['max_defocus'] = max_defocus
        params['defocus_step'] = defocus_step

        return params
    
    def cmd_finished(self):
        self.pushButton_run_ctffind.setText("RUN")
        self.pushButton_run_ctffind.setStyleSheet("QPushButton {color: black;}")
        self.reload_table()

    def ctffind4(self):
        params = self.get_params()
        if type(params) is str:
            QMessageBox.warning(self, 'Error!', \
                "Error! {}"\
                .format(params))
            self.cmd_finished()
        elif type(params) is dict:
            
            if self.pushButton_run_ctffind.text() == "RUN":
                ret = QMessageBox.question(self, 'Run Ctffind!', \
                    "Run ctffind for all the tilt series. \
                    \nContinue?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
                if ret == QMessageBox.Yes:
                    self.pushButton_run_ctffind.setText("STOP")
                    self.pushButton_run_ctffind.setStyleSheet('QPushButton {color: red;}')
                    
                    override = True
                    params['override'] = override

                    self.thread_ctffind = Ctffind4(params)                

                    self.thread_ctffind.finished.connect(self.cmd_finished)
                    
                    self.thread_ctffind.start()
                else:
                    self.cmd_finished()
            else :
                ret = QMessageBox.question(self, 'Warning!', \
                    "Stop Ctf Estimation! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.pushButton_run_ctffind.setText("RUN")
                    self.pushButton_run_ctffind.setStyleSheet("QPushButton {color: black;}")
                    self.thread_ctffind.stop_process()
        
        self.save_setting()

    def tab_changed(self, i):
        if i == 1:
            self.reload_table()

    def check_or_create_path(self, folder):
        if not os.path.exists(folder):
            os.mkdir(folder)

    def isValid(self, fileName):
        try:
            file = open(fileName, 'r')
            file.close()
            return True
        except:
            return False    
        
    def check_log_file(self, folder):
        if not os.path.exists(folder):
            os.mkdir(folder)
        try:
            file = open(self.log_file, 'r')
            file.close()
        except:
            pass

    def getLogContent(self, fileName):
        '''
        sets the member fileName to the value of the argument
        if the file exists.  Otherwise resets both the filename
        and file contents members.
        '''
        if self.isValid(fileName):
            self.fileName = fileName
            content = open(fileName, 'r').read()
            return content
        else:
            return None
    
    def table_click(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.ctf_results['tomoNames'][i]
        if j == 4:
            defoci = self.ctf_results['defocus'][i]
            xpoints = np.arange(len(defoci)) + 1
            ypoints = defoci
            plt.plot(xpoints, ypoints)
            plt.xlabel("Tilt index")
            plt.ylabel("defocus est. (Å)")
            plt.title(tomoName)
            plt.show()
        elif j == 5:
            searchPath = self.ctffind4_path
            ctf_mrc_file = "{}/{}/{}_ctf.mrc".format(searchPath, tomoName, tomoName)
            cmd = "3dmod {}".format(ctf_mrc_file)
            os.system(cmd)            
        else:
            pass

