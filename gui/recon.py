from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTabWidget, QTableWidgetItem, QHeaderView, QMessageBox
from TomoNet.process.bash_gts import Generate_TS
from TomoNet.util import browse,metadata
import os, glob, subprocess, shutil, time
import logging


class Recon(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.setupUi()

        self._history_record = "Recon/history_record.txt"

        self.log_file = "Recon/recon.log"
        self.check_log_file("Recon")

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
        

    def setupUi(self):
        
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        scriptDir = os.path.dirname(os.path.realpath(__file__))

        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_2.setObjectName("gridLayout_2")
        
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_corrected_image_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_corrected_image_folder.sizePolicy().hasHeightForWidth())
        self.label_corrected_image_folder.setSizePolicy(sizePolicy)
        self.label_corrected_image_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_corrected_image_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_corrected_image_folder.setObjectName("label_corrected_image_folder")
        self.horizontalLayout.addWidget(self.label_corrected_image_folder)
        self.lineEdit_corrected_image_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_corrected_image_folder.setInputMask("")
        self.lineEdit_corrected_image_folder.setObjectName("lineEdit_corrected_image_folder")
        self.horizontalLayout.addWidget(self.lineEdit_corrected_image_folder)
        
        self.pushButton_corrected_image_folder = QtWidgets.QPushButton(self.tab)
        self.pushButton_corrected_image_folder.setText("")
        self.pushButton_corrected_image_folder.setIcon(icon)
        self.pushButton_corrected_image_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_corrected_image_folder.setMaximumSize(QtCore.QSize(60, 24))
        self.pushButton_corrected_image_folder.setObjectName("pushButton_corrected_image_folder")
        self.horizontalLayout.addWidget(self.pushButton_corrected_image_folder)
        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 1)
        
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_base_name = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_base_name.sizePolicy().hasHeightForWidth())
        self.label_base_name.setSizePolicy(sizePolicy)
        self.label_base_name.setMinimumSize(QtCore.QSize(140, 0))
        self.label_base_name.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_base_name.setObjectName("label_base_name")
        self.horizontalLayout_2.addWidget(self.label_base_name)
        self.lineEdit_base_name = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_base_name.setInputMask("")
        self.lineEdit_base_name.setMinimumSize(QtCore.QSize(160, 0))
        self.lineEdit_base_name.setObjectName("lineEdit_base_name")
        self.horizontalLayout_2.addWidget(self.lineEdit_base_name)
        self.label_delimiter = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_delimiter.sizePolicy().hasHeightForWidth())
        self.label_delimiter.setSizePolicy(sizePolicy)
        self.label_delimiter.setMinimumSize(QtCore.QSize(80, 0))
        self.label_delimiter.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_delimiter.setObjectName("label_delimiter")
        self.horizontalLayout_2.addWidget(self.label_delimiter)
        self.lineEdit_delimiter = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_delimiter.setInputMask("")
        self.lineEdit_delimiter.setObjectName("lineEdit_delimiter")
        self.horizontalLayout_2.addWidget(self.lineEdit_delimiter)
        self.label_key_index = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_key_index.sizePolicy().hasHeightForWidth())
        self.label_key_index.setSizePolicy(sizePolicy)
        self.label_key_index.setMinimumSize(QtCore.QSize(120, 0))
        self.label_key_index.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_key_index.setObjectName("label_key_index")
        self.horizontalLayout_2.addWidget(self.label_key_index)
        self.lineEdit_key_index = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_key_index.setInputMask("")
        self.lineEdit_key_index.setObjectName("lineEdit_key_index")
        self.horizontalLayout_2.addWidget(self.lineEdit_key_index)
        self.gridLayout_2.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_base_name_index = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_base_name_index.sizePolicy().hasHeightForWidth())
        self.label_base_name_index.setSizePolicy(sizePolicy)
        self.label_base_name_index.setMinimumSize(QtCore.QSize(140, 0))
        self.label_base_name_index.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_base_name_index.setObjectName("label_base_name_index")
        self.horizontalLayout_5.addWidget(self.label_base_name_index)
        self.lineEdit_base_name_index = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_base_name_index.setInputMask("")
        self.lineEdit_base_name_index.setMinimumSize(QtCore.QSize(80, 0))
        self.lineEdit_base_name_index.setObjectName("lineEdit_base_name_index")
        self.horizontalLayout_5.addWidget(self.lineEdit_base_name_index)
        self.label_image_file_suffix = QtWidgets.QLabel(self.tab)
        self.label_target_base_name = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_target_base_name.sizePolicy().hasHeightForWidth())
        self.label_target_base_name.setSizePolicy(sizePolicy)
        self.label_target_base_name.setMinimumSize(QtCore.QSize(150, 0))
        self.label_target_base_name.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_target_base_name.setIndent(-1)
        self.label_target_base_name.setObjectName("label_target_base_name")
        self.horizontalLayout_5.addWidget(self.label_target_base_name)
        self.lineEdit_target_base_name = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_target_base_name.setInputMask("")
        self.lineEdit_target_base_name.setObjectName("lineEdit_target_base_name")
        self.horizontalLayout_5.addWidget(self.lineEdit_target_base_name)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_image_file_suffix.sizePolicy().hasHeightForWidth())
        self.label_image_file_suffix.setSizePolicy(sizePolicy)
        self.label_image_file_suffix.setMinimumSize(QtCore.QSize(130, 0))
        self.label_image_file_suffix.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_image_file_suffix.setObjectName("label_image_file_suffix")
        self.horizontalLayout_5.addWidget(self.label_image_file_suffix)
        self.lineEdit_image_file_suffix = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_image_file_suffix.setInputMask("")
        self.lineEdit_image_file_suffix.setObjectName("lineEdit_image_file_suffix")
        self.horizontalLayout_5.addWidget(self.lineEdit_image_file_suffix)
        self.gridLayout_2.addLayout(self.horizontalLayout_5, 2, 0, 1, 1)
        
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_cpus = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_cpus.sizePolicy().hasHeightForWidth())
        self.label_cpus.setSizePolicy(sizePolicy)
        self.label_cpus.setMinimumSize(QtCore.QSize(70, 0))
        self.label_cpus.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_cpus.setObjectName("label_cpus")
        self.horizontalLayout_3.addWidget(self.label_cpus)
        self.lineEdit_cpus = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_cpus.setInputMask("")
        self.lineEdit_cpus.setObjectName("lineEdit_cpus")
        self.horizontalLayout_3.addWidget(self.lineEdit_cpus)
        self.label_min_num_tilt = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_min_num_tilt.sizePolicy().hasHeightForWidth())
        self.label_min_num_tilt.setSizePolicy(sizePolicy)
        self.label_min_num_tilt.setMinimumSize(QtCore.QSize(120, 0))
        self.label_min_num_tilt.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_num_tilt.setObjectName("label_min_num_tilt")
        self.horizontalLayout_3.addWidget(self.label_min_num_tilt)
        self.lineEdit_min_num_tilt = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_min_num_tilt.setInputMask("")
        self.lineEdit_min_num_tilt.setObjectName("lineEdit_min_num_tilt")
        self.horizontalLayout_3.addWidget(self.lineEdit_min_num_tilt)
        self.pushButton_check_tomo_num = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_check_tomo_num.sizePolicy().hasHeightForWidth())
        self.pushButton_check_tomo_num.setSizePolicy(sizePolicy)
        self.pushButton_check_tomo_num.setMinimumSize(QtCore.QSize(40, 20))
        self.pushButton_check_tomo_num.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_check_tomo_num.setObjectName("pushButton_check_tomo_num")
        self.horizontalLayout_3.addWidget(self.pushButton_check_tomo_num)

        self.label_remove_dup = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_remove_dup.sizePolicy().hasHeightForWidth())
        self.label_remove_dup.setSizePolicy(sizePolicy)
        self.label_remove_dup.setMinimumSize(QtCore.QSize(100, 0))
        self.label_remove_dup.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_remove_dup.setObjectName("label_remove_dup")
        self.horizontalLayout_3.addWidget(self.label_remove_dup)
        self.comboBox_rm_dup = QtWidgets.QComboBox(self.tab)
        self.comboBox_rm_dup.setObjectName("comboBox_rm_dup")
        self.comboBox_rm_dup.addItem("")
        self.comboBox_rm_dup.addItem("")
        self.horizontalLayout_3.addWidget(self.comboBox_rm_dup)

        self.label_new_data = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_new_data.sizePolicy().hasHeightForWidth())
        self.label_new_data.setSizePolicy(sizePolicy)
        self.label_new_data.setMinimumSize(QtCore.QSize(120, 0))
        self.label_new_data.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_new_data.setObjectName("label_new_data")
        self.horizontalLayout_3.addWidget(self.label_new_data)
        self.comboBox_new_data = QtWidgets.QComboBox(self.tab)
        self.comboBox_new_data.setObjectName("comboBox_new_data")
        self.comboBox_new_data.addItem("")
        self.comboBox_new_data.addItem("")
        self.horizontalLayout_3.addWidget(self.comboBox_new_data)

        self.gridLayout_2.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)
        
        self.spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(self.spacerItem1, 4, 0, 1, 1)

        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem2)
        self.pushButton_run_ts_generation = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_run_ts_generation.sizePolicy().hasHeightForWidth())
        self.pushButton_run_ts_generation.setSizePolicy(sizePolicy)
        self.pushButton_run_ts_generation.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_run_ts_generation.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_run_ts_generation.setObjectName("run")
        self.horizontalLayout_4.addWidget(self.pushButton_run_ts_generation)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem3)
        self.gridLayout_2.addLayout(self.horizontalLayout_4, 5, 0, 1, 1)

        self.addTab(self.tab, "")
        
        self.tab1 = QtWidgets.QWidget()
        self.tab1.setObjectName("tab")

        self.gridLayout_recon = QtWidgets.QGridLayout(self.tab1)

        self.horizontalLayout_recon = QtWidgets.QHBoxLayout()
        self.horizontalLayout_recon.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_recon.setObjectName("horizontalLayout_recon")

        self.label_recon = QtWidgets.QLabel(self.tab1)
        self.label_recon.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_recon.setAlignment(QtCore.Qt.AlignCenter)
        self.label_recon.setObjectName("label_recon")
        self.label_recon.setText("Summary of Reconstruction")
        self.horizontalLayout_recon.addWidget(self.label_recon)
        self.pushButton_reload = QtWidgets.QPushButton(self.tab1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.pushButton_reload.setSizePolicy(sizePolicy)
        self.pushButton_reload.setMinimumSize(QtCore.QSize(50, 20))
        self.pushButton_reload.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_reload.setObjectName("pushButton_reload")
        self.horizontalLayout_recon.addWidget(self.pushButton_reload)
        self.gridLayout_recon.addLayout(self.horizontalLayout_recon, 0, 0, 1, 1)

        self.model = QtGui.QStandardItemModel(self)

        self.tableView = QtWidgets.QTableWidget(self)
        
        header_labels = metadata.header_labels_recon
        self.tableView.setColumnCount(len(header_labels))
        self.tableView.setHorizontalHeaderLabels(header_labels)
        header = self.tableView.horizontalHeader()   
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        
        self.gridLayout_recon.addWidget(self.tableView, 1, 0)
        
        self.addTab(self.tab1, "")

        self.retranslateUi()

        ############### Define variables ################
        self.ts_folder = "Recon/ts_tlt"
        self.etomo_folder = "Recon/eTomo"
        self.areTomo_folder = "Recon/areTomo"
        ############### Define variables ################

        self.thread_gt = None
        self.pushButton_check_tomo_num.clicked.connect(self.check_tomo_num)

        self.pushButton_corrected_image_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_corrected_image_folder)) 
        self.pushButton_run_ts_generation.clicked.connect(self.generate_ts)

        self.pushButton_reload.clicked.connect(self.reload_table)
        
        self.currentChanged.connect(self.tab_changed)
        self.tableView.doubleClicked.connect(self.table_click)

        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        self.setting_file ="Recon/recon.setting"
        self.read_setting()

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        self.label_corrected_image_folder.setText(_translate("Form", "Motion Corrected Images:"))
        self.lineEdit_corrected_image_folder.setPlaceholderText(_translate("Form", "MotionCorrection/corrected_images"))
        self.lineEdit_corrected_image_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Folder path to your motion corrected images. \
            </span></p></body></html>"))

        
        self.label_base_name.setText(_translate("Form", "Filename filter text:"))
        self.lineEdit_base_name.setPlaceholderText(_translate("Form", "e.g TS_1201_* for X_TS_1201_001_X_ali.mrc"))
        self.lineEdit_base_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Base name during the data collection, \
            used to filter out target images in the provided folder. \
            e.g., HIV_mutant42 for 20180101_HIV_mutant42_00030_30.0_ali.tif\
            </span></p></body></html>"))
        
        self.label_delimiter.setText(_translate("Form", "Delimiter:"))
        self.lineEdit_delimiter.setPlaceholderText(_translate("Form", "_"))
        self.lineEdit_delimiter.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Delimiter that seperate words in the image name. (default is _)\
            </span></p></body></html>"))
        self.label_key_index.setText(_translate("Form", "Tilt Info Index:"))
        self.lineEdit_key_index.setPlaceholderText(_translate("Form", "5"))
        self.lineEdit_key_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            The place where tilt info recorded in the image name. e.g., \
            5 for 20180101_HIV_mutant42_00030_30.0_ali.tif because 30.0 is the\
            tilt angle and it's index is 5 with delimiter _\
            </span></p></body></html>"))

        self.label_base_name_index.setText(_translate("Form", "Base Name index:"))
        self.lineEdit_base_name_index.setPlaceholderText(_translate("Form", "1-4"))
        self.lineEdit_base_name_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            This is different from the above Base Name. \
            It is used for identify which images come from the same Tomogram\
            e.g., 1-4 for 20180101_HIV_mutant42_00030_30.0_ali.tif \
            because 20180101_HIV_mutant42_00030 can define one of the tomogram. \
            Only single integer or two integers (range) seperate by -\
            </span></p></body></html>"))

        self.label_target_base_name.setText(_translate("Form", "Target Base Name:"))
        self.lineEdit_target_base_name.setPlaceholderText(_translate("Form", "TS "))
        self.lineEdit_target_base_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            This program will rename all tomograms in the format \
            [target_base_name]_[index].st. (default TS)\
            </span></p></body></html>"))

        self.label_image_file_suffix.setText(_translate("Form", "Images file suffix:"))
        self.lineEdit_image_file_suffix.setPlaceholderText(_translate("Form", "_ali.mrc"))
        self.lineEdit_image_file_suffix.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Filter image with its suffix. MotionCor2 could \
            output different types of image, e.g., _ali.mrc, _ali_DW.mrc or _ali_DWS.mrc\
            </span></p></body></html>"))
        
        self.label_cpus.setText(_translate("Form", "cpu(s) #:"))
        self.lineEdit_cpus.setPlaceholderText(_translate("Form", "8"))
        self.lineEdit_cpus.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            cpus # to be used in the TS generation (default 8)\
            </span></p></body></html>"))

        self.label_min_num_tilt.setText(_translate("Form", "Min Tilt Number:"))
        self.lineEdit_min_num_tilt.setPlaceholderText(_translate("Form", "30"))
        self.lineEdit_min_num_tilt.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            The minimum number of tilts required to generate a tomogram for later process\
            any tomogram with less than this number will be discarded. Use the check button\
            to the right to check how many tomograms will be generated with the current params.\
             (default 30 )\
            </span></p></body></html>"))
        
        self.pushButton_check_tomo_num.setText(_translate("Form", "check"))
        
        self.label_remove_dup.setText(_translate("Form", "Remove Dup:"))
        self.comboBox_rm_dup.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_rm_dup.setItemText(1, _translate("Form", "No"))
        self.comboBox_rm_dup.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Sometimes the microscope take multiple image for the same tilt \
            because previous one failed, if you want to remove those failed ones, \
            select Yes, otherwise No. (default Yes)\
            </span></p></body></html>"))
        
        self.label_new_data.setText(_translate("Form", "Add New Data?:"))
        self.comboBox_new_data.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_new_data.setItemText(1, _translate("Form", "No"))
        self.comboBox_rm_dup.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            If you dont want to overwrite the existing tomogram, select Yes, otherwise No \
            (default Yes)\
            </span></p></body></html>"))
        
        self.pushButton_run_ts_generation.setText(_translate("Form", "RUN"))
        
        self.setTabText(self.indexOf(self.tab), _translate("Form", "TS Generation"))
        self.setTabText(self.indexOf(self.tab1), _translate("Form", "eTomo Reconstruction"))

        self.pushButton_reload.setText(_translate("Form", "Reload"))

    def generate_ts(self):
        if self.pushButton_run_ts_generation.text() == "RUN":
            if len(self.lineEdit_corrected_image_folder.text()) > 0:
                corrected_folder_path = self.lineEdit_corrected_image_folder.text()
            else: 
                self.logger.error( "corrected image folder path cannot be empty!")
                return 1        
            ret = QMessageBox.question(self, 'Run Tilt Series Generation!', \
                    "Generate tilt series from all images from {}. \
                    \nContinue?\n".format(corrected_folder_path)\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
            if ret == QMessageBox.Yes:
                self.pushButton_run_ts_generation.setText("STOP")
                self.pushButton_run_ts_generation.setStyleSheet('QPushButton {color: red;}')

                if len(self.lineEdit_base_name.text()) >0:
                    base_name = self.lineEdit_base_name.text()
                else: 
                    self.cmd_finished()
                    self.logger.error("base name cannot be empty!")
                    return 2

                if len(self.lineEdit_image_file_suffix.text()) > 0:
                    image_file_suffix = self.lineEdit_image_file_suffix.text()
                else: 
                    self.cmd_finished()
                    self.logger.error("base name cannot be empty!")
                    return 2
                try:
                    file_names = "{}/*{}*{}".format(corrected_folder_path,base_name,image_file_suffix)
                except:
                    self.cmd_finished()
                    self.logger.error("Please check your corrected image fold path!")
                    return 3
                
                images_list = sorted([os.path.basename(x) for x in glob.glob(file_names)])
                delimiter = self.lineEdit_delimiter.text() if len(self.lineEdit_delimiter.text()) > 0 else '_'
                
                if len(self.lineEdit_base_name_index.text()) > 0:
                    base_name_index = self.lineEdit_base_name_index.text()
                    if '-' in base_name_index:
                        try:
                            key_index = [int(x) for x in base_name_index.split('-')]
                            key_index[0]-=1
                        except:
                            self.cmd_finished()
                            self.logger.error("base_name_index format error!")
                            return 3
                    else:
                        try:
                            key_index = [int(base_name_index)-1, int(base_name_index)]
                        except:
                            self.cmd_finished()
                            self.logger.error("base_name_index format error!")
                            return 3
                    if len(key_index) != 2:
                        self.cmd_finished()
                        self.logger.error("base_name_index format error!")
                        return 3
                else: 
                    self.cmd_finished()
                    self.logger.error("please provide base name index for identifying tilts for each tomogram!")
                    return 2

                if len(images_list) == 0:
                    self.logger.error("No required images detected!")
                    self.cmd_finished()
                    return 6
        
                tomo_lists = []
                if len(images_list) > 0:
                    current_tomo = []

                    prefix = delimiter.join(images_list[0].split(delimiter)[key_index[0]:key_index[1]])
                    
                    for im in images_list:
                        key = delimiter.join(im.split(delimiter)[key_index[0]:key_index[1]])
                        if key == prefix:
                            current_tomo.append(im)
                        else:
                            prefix = key
                            tomo_lists.append(current_tomo)
                            current_tomo = [im]
                    tomo_lists.append(current_tomo)
                else: 
                    self.cmd_finished()
                    self.logger.error("no images found!")
                    return 4
                    
                if self.lineEdit_key_index.text().isdigit():
                    key_index_sort = int(self.lineEdit_key_index.text()) - 1
                else: 
                    self.cmd_finished()
                    self.logger.error("Please provide a valid index number!")
                    return 5
          
                tomo_lists = [sorted(x, key = lambda \
                            y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) \
                            for x in tomo_lists]
                
                rawtlt_lists = [[float(x.split(image_file_suffix)[0].split(delimiter)[key_index_sort])\
                                for x in y] for y in tomo_lists]

                if self.comboBox_rm_dup.currentText()== "Yes":
                    for i,tlts in enumerate(rawtlt_lists):
                        pop_list = []
                        for j, tlt in enumerate(tlts):
                            if j > 0 and tlt == tlts[j-1]:
                                pop_list.append(j-1)
                        for k in sorted(pop_list, reverse=True):
                            del rawtlt_lists[i][k]
                            del tomo_lists[i][k]

                if not len(self.lineEdit_min_num_tilt.text()) > 0:
                    min_num_tilt = 30
                else:
                    min_num_tilt = int(self.lineEdit_min_num_tilt.text())
                tomo_lists = [x for x in tomo_lists if len(x) >= min_num_tilt]
                rawtlt_lists = [x for x in rawtlt_lists if len(x) >= min_num_tilt]

                add_new_data = self.comboBox_new_data.currentText()
                if add_new_data == "Yes":
                    try:
                        current_ts_list = sorted([os.path.basename(x) for x in glob.glob("{}/*.st".format(self.ts_folder))])
                        if len(current_ts_list) > 0:
                            #last_item = current_ts_list[-1]
                            #last_index = os.path.splitext(last_item)[0].split("_")[-1]
                            indexes = [int(os.path.splitext(x)[0].split("_")[-1]) for x in current_ts_list]
                            indexes.sort()
                            last_index = indexes[-1]
                            start_index = int(last_index) + 1
                        else:
                            start_index = 1
                    except:
                        self.logger.error("error when check current ts info!")
                        return 6
                else:
                    start_index = 1
                self.logger.info("########Total tomo # detected is {} from {} images: min number of tilts set as {}.########".format(len(tomo_lists), len(images_list), min_num_tilt ))
                self.logger.info("########The generated tilt series will be save in {}. And start with index {}.########".format(self.ts_folder, start_index))
                image_folder = self.lineEdit_corrected_image_folder.text()
                target_base_name = self.lineEdit_target_base_name.text() \
                    if not self.lineEdit_target_base_name.text() == "" else "TS"
                
                cpus = int(self.lineEdit_cpus.text()) if len(self.lineEdit_cpus.text()) > 0 else 8
                if not self.thread_gt:
                    self.thread_gt = Generate_TS(image_folder,tomo_lists,\
                        rawtlt_lists,target_base_name,start_index,delimiter,\
                        key_index,self.ts_folder,cpus)
                else:
                    self.thread_gt = Generate_TS(image_folder,tomo_lists,\
                        rawtlt_lists,target_base_name,start_index,delimiter,\
                        key_index,self.ts_folder,cpus)

                self.thread_gt.finished.connect(self.cmd_finished)
                
                self.thread_gt.start()
                
                    
        else:
            ret = QMessageBox.question(self, 'Stop Generate Tilt Series!', \
                "Stop Generate Tilt Series! \
                \nConfirm?\n"\
                , QMessageBox.Yes | QMessageBox.No, \
                QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.pushButton_run_ts_generation.setText("RUN")
                self.pushButton_run_ts_generation.setStyleSheet("QPushButton {color: black;}")
                try:
                    self.thread_gt.stop_process()
                except:
                    pass
      
    def cmd_finished(self):
        self.pushButton_run_ts_generation.setText("RUN")
        self.pushButton_run_ts_generation.setStyleSheet("QPushButton {color: black;}")
        #self.thread_gt.quit()
        #self.thread_gt.wait()

    def read_setting(self):
        if os.path.exists(self.setting_file):
            data = {}
            data['image_folder'] = ""
            data['base_name'] = ""
            data['delimiter'] = ""
            data['key_index'] = ""
            data['min_num_tilt'] = ""
            data['target_base_name'] = ""
            data['rm_dup'] = "Yes"
            data['new_data'] = "Yes"
            data['base_name_index'] = ""
            data['image_file_suffix'] = ""
            data['cpus'] = ""
            try:
                with open(self.setting_file) as f:
                    for line in f:
                        (k, v) = line.split(":")
                        data[k] = v.strip()
                self.lineEdit_corrected_image_folder.setText(data['image_folder'])
                self.lineEdit_base_name.setText(data['base_name'])
                self.lineEdit_delimiter.setText(data['delimiter'])
                self.lineEdit_key_index.setText(data['key_index'])
                self.lineEdit_base_name_index.setText(data['base_name_index'])
                self.lineEdit_image_file_suffix.setText(data['image_file_suffix'])
                self.lineEdit_cpus.setText(data['cpus'])
                self.lineEdit_min_num_tilt.setText(data['min_num_tilt'])
                self.lineEdit_target_base_name.setText(data['target_base_name'])
                self.comboBox_rm_dup.setCurrentText(data['rm_dup'])
                self.comboBox_new_data.setCurrentText(data['new_data'])
                
            except:
                self.logger.error("error reading {}!".format(self.setting_file))

    def save_setting(self):
        param = {}
        param['image_folder'] = self.lineEdit_corrected_image_folder.text()
        param['base_name'] = self.lineEdit_base_name.text()
        param['delimiter'] = self.lineEdit_delimiter.text()
        param['key_index'] = self.lineEdit_key_index.text()
        param['base_name_index'] = self.lineEdit_base_name_index.text()
        param['image_file_suffix'] = self.lineEdit_image_file_suffix.text()
        param['cpus'] = self.lineEdit_cpus.text()
        param['min_num_tilt'] = self.lineEdit_min_num_tilt.text()
        param['target_base_name'] = self.lineEdit_target_base_name.text()
        param['rm_dup'] = self.comboBox_rm_dup.currentText()
        param['new_data'] = self.comboBox_new_data.currentText()
        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            pass

    def tab_changed(self,i):
        if i == 1:
            # You are now at Reconstruction tab, refresh the table contain the tomo information

            self.reload_table()

    def natural_keys(self, text):
        return int(text.split("_")[-1]) 

    def read_tomo(self):
        tomoNames1 = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*.st".format(self.ts_folder)))]
        tomoNames2 = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*.rawtlt".format(self.ts_folder)))]

        tomoNames = list(set(tomoNames1) & set(tomoNames2))
        tomoNames.sort(key=self.natural_keys)

        return tomoNames

    def loadTomo(self):

        tomoNames = self.read_tomo()
        self.tableView.setRowCount(len(tomoNames))
        if len(tomoNames) > 0:
            for i, tomo in enumerate(tomoNames):    

                self.tableView.setItem(i, 0, QTableWidgetItem(tomo))
                action_continue = QTableWidgetItem("Continue")
                action_continue.setBackground(QtGui.QColor("#4CAF50"))
                action_continue.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 1, action_continue)

                action_starover = QTableWidgetItem("Start Over")
                action_starover.setBackground(QtGui.QColor("#008CBA"))
                action_starover.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 2, action_starover)

                action_starover = QTableWidgetItem("Delete")
                action_starover.setBackground(QtGui.QColor("#f44336"))
                action_starover.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 3, action_starover)

            self.tableView.horizontalHeader().show()

        else:
            self.model.clear()
            items = [
                        QtGui.QStandardItem(field)
                        for field in ["No tomogram data found yet!"]
                    ]
            self.model.appendRow(items)
            self.tableView.horizontalHeader().hide()

    def open_tomo_recon(self, item):
        i = item.row()
        j = item.column()
        if j == 1:
            tomoName = self.model.item(item.row(),0).text()
            baseName = tomoName.split('.')[0]
            
            current_tomo_folder = "{}/{}".format(self.etomo_folder,baseName)

            if not os.path.exists(current_tomo_folder):
                os.makedirs(current_tomo_folder)
            
            edfName = "{}/{}.edf".format(current_tomo_folder,baseName)
            current_st_path = "{}/{}".format(current_tomo_folder,tomoName)

            if not os.path.exists(current_st_path):
                current_st_link_path = "{}/{}".format(self.ts_folder,tomoName)
                current_rawtlt_link_path = "{}/{}.rawtlt".format(self.ts_folder,baseName)
                cmd = "cd {} ; ln -s ../../../{} ./ ; ln -s ../../../{} ./ ; etomo".format(current_tomo_folder, current_st_link_path,current_rawtlt_link_path)
                subprocess.check_output(cmd, shell=True)

            elif not os.path.exists(edfName):
                cmd = "cd {}; etomo".format(current_tomo_folder)
                subprocess.check_output(cmd, shell=True)
            else:
                cmd = "cd {};etomo *edf".format(current_tomo_folder)
                subprocess.check_output(cmd, shell=True)

        elif j == 2:
            pass

    def table_click(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.tableView.item(i, 0).text()
        if j == 1:
            current_st_link_path = "{}/{}.st".format(self.ts_folder, tomoName)
            cmd = "3dmod -b 12,1 {}".format(current_st_link_path)
            os.system(cmd)
        elif j == 2:
            current_tomo_folder = "{}/{}".format(self.etomo_folder,tomoName)
            if not os.path.exists(current_tomo_folder):
                os.makedirs(current_tomo_folder)
            
            edfName = "{}/{}.edf".format(current_tomo_folder,tomoName)
            current_st_path = "{}/{}.st".format(current_tomo_folder,tomoName)
            if not os.path.exists(current_st_path):
                current_st_link_path = "{}/{}.st".format(self.ts_folder,tomoName)
                current_rawtlt_link_path = "{}/{}.rawtlt".format(self.ts_folder,tomoName)
                cmd = "cd {} ; ln -s ../../../{} ./ ; ln -s ../../../{} ./ ; etomo".format(current_tomo_folder, current_st_link_path, current_rawtlt_link_path)
                
                subprocess.check_output(cmd, shell=True)
            elif not os.path.exists(edfName):
                
                cmd = "cd {}; etomo".format(current_tomo_folder)
                subprocess.check_output(cmd, shell=True)
            else:
                cmd = "cd {};etomo *edf".format(current_tomo_folder)
                subprocess.check_output(cmd, shell=True)
        elif j == 3:
            ret = QMessageBox.question(self, 'Risky Action!', "Do you want to star over for {}? All progresses will be reset.".format(tomoName), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret == QMessageBox.Yes:
                current_tomo_folder = "{}/{}".format(self.etomo_folder,tomoName)
                if not os.path.exists(current_tomo_folder):
                    os.makedirs(current_tomo_folder)
                edfName = "{}/{}.edf".format(current_tomo_folder,tomoName)
                current_st_path = "{}/{}.st".format(current_tomo_folder,tomoName)
                if not os.path.exists(current_st_path):
                    current_st_link_path = "{}/{}.st".format(self.ts_folder,tomoName)
                    current_rawtlt_link_path = "{}/{}.rawtlt".format(self.ts_folder,tomoName)
                    cmd = "cd {} ; ln -s ../../../{} ./ ; ln -s ../../../{} ./ ; etomo".format(current_tomo_folder, current_st_link_path,current_rawtlt_link_path)
                    subprocess.check_output(cmd, shell=True)
                
                cmd = "cd {}; etomo".format(current_tomo_folder)
                subprocess.check_output(cmd, shell=True)
        elif j == 4:
            ret = QMessageBox.question(self, 'Risky Action!', "Do you want to move {} to trash?".format(tomoName), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret == QMessageBox.Yes:
                trash_ts_tlt = "{}/{}".format(self.ts_folder, "Trash")
                trash_ts_etomo = "{}/{}".format(self.etomo_folder, "Trash")
                if not os.path.exists(trash_ts_tlt):
                    os.makedirs(trash_ts_tlt)
                if not os.path.exists(trash_ts_etomo):
                    os.makedirs(trash_ts_etomo)
                ts_path = "{}/{}.st".format(self.ts_folder,tomoName)
                tlt_path = "{}/{}.rawtlt".format(self.ts_folder,tomoName)
                try:
                    if os.path.exists("{}/{}.st".format(trash_ts_tlt, tomoName)):
                        os.remove("{}/{}.st".format(trash_ts_tlt, tomoName))
                    if os.path.exists("{}/{}.rawtlt".format(trash_ts_tlt, tomoName)):
                        os.remove("{}/{}.rawtlt".format(trash_ts_tlt, tomoName))
                    shutil.move(ts_path, trash_ts_tlt)
                    shutil.move(tlt_path, trash_ts_tlt)
                except:
                    pass
                try:
                    if os.path.exists("{}/{}".format(trash_ts_etomo, tomoName)):
                        shutil.rmtree("{}/{}".format(trash_ts_etomo, tomoName))
                    etomo_folder = "{}/{}".format(self.etomo_folder, tomoName)
                    shutil.move(etomo_folder, trash_ts_etomo)
                except:
                    pass

                existing_tomo = []
                existing_record = []
                if os.path.exists(self._history_record):
                    with open(self._history_record) as file:
                        try:
                            existing_record = [line.strip() for line in file]
                            existing_tomo = [line.split("->")[1] for line in existing_record]
                            
                        except:
                            self.logger.warning("The history record file's format is wrong: {}".format(self._history_record))
                    try:      
                        ind = existing_tomo.index(tomoName)
                    except:
                        ind = -1
                    existing_tomo = sorted(list(existing_tomo))
                    with open(self._history_record, "w") as f:
                        for i, record in enumerate(existing_record):
                            if not i == ind:
                                f.write("{}\n".format(record))
                self.reload_table()
        else:
            pass
    
    def read_recon_folder(self, tomoName):

        tilt_num, re_mean, re_range, binning, thickness_nm, skipped_view = ["", "", "", "", "", ""]
        etomo_path = "{}/{}".format(self.etomo_folder, tomoName)

        tiltcom_path = "{}/{}".format(etomo_path, "tilt.com")
        st_path = "{}/{}.st".format(etomo_path, tomoName)
        rec_path = "{}/{}.rec".format(etomo_path, tomoName)
        mrc_path = "{}/{}_rec.mrc".format(etomo_path, tomoName)


        if os.path.exists(rec_path) or os.path.exists(mrc_path):
            try:                
                d_st = self.read_header(st_path)
                if os.path.exists(rec_path):
                    d_rec = self.read_header(rec_path)
                else:
                    d_rec = self.read_header(mrc_path)


                tilt_num = str(d_st["sections"])
                
                taError_path = "{}/{}".format(etomo_path, "taError.log")
                
                binning = str(int(d_rec["apix"]/d_st["apix"]))

                thickness_nm = str(int(d_rec["sections"] * d_rec["apix"]))

                if os.path.exists(taError_path):
                    try:
                        cmd = "cat {} | grep \"{}\"".format(taError_path, "Residual error local mean")
                        
                        out = subprocess.check_output(cmd, shell=True)
                        line = out.decode('utf-8').split("\n")[0]

                        re_mean = line.strip().split()[4]
                        re_range = "{} - {}".format(line.split()[6],line.split()[8])
                    except:
                        self.logger.warning("cannot reading RE mean error !")
                
                with open(tiltcom_path) as f:
                    for line in f:
                        if "EXCLUDELIST" in line:
                            skipped_view = line.split()[-1]
                        elif "EXCLUDELIST2" in line:
                            skipped_view = line.split()[-1]      
            except:
                pass                                
        return [tilt_num, re_mean, re_range, binning, thickness_nm, skipped_view]
    
    def read_header(self, st_path):
        d = {}
        d['apix'] = 1.0
        cmd = "header {} ".format(st_path)
        out = subprocess.check_output(cmd, shell=True)
        lines = out.decode('utf-8').split("\n")
        for line in lines:
            if "Pixel spacing" in line:
                apix = line.strip().split()[-1]
                d['apix'] = float(apix)
            if "Number of columns" in line:
                sections = line.strip().split()[-1]
                d['sections'] = int(sections)  
        return d
    
    def reload_table(self):
        tomoNames = self.read_tomo()
        self.tableView.setRowCount(0)
        self.tableView.setRowCount(len(tomoNames))
        if len(tomoNames) > 0:
            for i, tomo in enumerate(tomoNames):
                start_time = time.time()
                self.tableView.setItem(i, 0, QTableWidgetItem(tomo))                
                action_check = QTableWidgetItem("View ST")
                action_check.setBackground(QtGui.QColor("#a0d2eb"))
                action_check.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 1, action_check)
                
                action_continue = QTableWidgetItem("Continue")
                action_continue.setBackground(QtGui.QColor("#4CAF50"))
                action_continue.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 2, action_continue)

                action_starover = QTableWidgetItem("Start Over")
                action_starover.setBackground(QtGui.QColor("#008CBA"))
                action_starover.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 3, action_starover)

                action_delete = QTableWidgetItem("Delete")
                action_delete.setBackground(QtGui.QColor("#f44336"))
                action_delete.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 4, action_delete)
                
                items = self.read_recon_folder(tomo)

                self.tableView.setItem(i, 5, QTableWidgetItem(items[0]))
                self.tableView.setItem(i, 6, QTableWidgetItem(items[1]))
                self.tableView.setItem(i, 7, QTableWidgetItem(items[2]))
                self.tableView.setItem(i, 8, QTableWidgetItem(items[3]))
                if len(items[4]) > 0:
                    self.tableView.setItem(i, 9, QTableWidgetItem("{} nm".format(str(int(items[4])/10))))
                else:
                    self.tableView.setItem(i, 9, QTableWidgetItem(""))
                self.tableView.setItem(i, 10, QTableWidgetItem(items[5]))

    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 1:
                    in_current_page = False
            elif x.objectName() == "log_window":
                if in_current_page:
                    self.log_window = x
                    self.log_window.setText(self.getLogContent(txt))
                    self.log_window.moveCursor(QtGui.QTextCursor.End)

                    custom_font = QtGui.QFont()
                    custom_font.setPointSize(11)
                    self.log_window.setCurrentFont(custom_font)
        # self.log_window = self.parentWidget().parentWidget().children()[3] 
        # self.log_window.setText(self.getLogContent(self.log_file))
        # self.log_window.moveCursor(QtGui.QTextCursor.End)
        
        # custom_font = QtGui.QFont()
        # custom_font.setPointSize(11)
        # self.log_window.setCurrentFont(custom_font)

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
        
    def check_tomo_num(self):
        if len(self.lineEdit_corrected_image_folder.text()) > 0:
                corrected_folder_path = self.lineEdit_corrected_image_folder.text()
        else: 
            self.logger.error( "corrected image folder path cannot be empty!")
            return 1

        if len(self.lineEdit_base_name.text()) >0:
            base_name = self.lineEdit_base_name.text()
        else: 
            self.logger.error("base name cannot be empty!")
            return 2

        if len(self.lineEdit_image_file_suffix.text()) > 0:
            image_file_suffix = self.lineEdit_image_file_suffix.text()
        else: 
            self.logger.error("image file suffix cannot be empty!")
            return 2
        try:
            file_names = "{}/*{}*{}".format(corrected_folder_path,base_name,image_file_suffix)
        except:
            self.logger.error("Please check your corrected image fold path!")
            return 3
        
        images_list = sorted([os.path.basename(x) for x in glob.glob(file_names)])
        delimiter = self.lineEdit_delimiter.text() if len(self.lineEdit_delimiter.text()) > 0 else '_'
        
        if len(self.lineEdit_base_name_index.text()) > 0:
            base_name_index = self.lineEdit_base_name_index.text()
            if '-' in base_name_index:
                try:
                    key_index = [int(x) for x in base_name_index.split('-')]
                    key_index[0]-=1
                except:
                    self.logger.error("base_name_index format error!")
                    return 3
            else:
                try:
                    key_index = [int(base_name_index)-1, int(base_name_index)]
                except:
                    self.logger.error("base_name_index format error!")
                    return 3
            if len(key_index) != 2:
                self.logger.error("base_name_index format error!")
                return 3
        else: 
            self.logger.error("please provide base name index for identifying tilts for each tomogram!")
            return 2

        if len(images_list) == 0:
            self.logger.error("No required images detected!")
            return 6

        tomo_lists = []
        if len(images_list) > 0:
            current_tomo = []

            prefix = delimiter.join(images_list[0].split(delimiter)[key_index[0]:key_index[1]])
            for im in images_list:
                key = delimiter.join(im.split(delimiter)[key_index[0]:key_index[1]])
                if key == prefix:
                    current_tomo.append(im)
                else:
                    prefix = key
                    tomo_lists.append(current_tomo)
                    current_tomo = [im]
            tomo_lists.append(current_tomo)
        else: 
            self.logger.error("no images found!")
            return 4
            
        if self.lineEdit_key_index.text().isdigit():
            key_index_sort = int(self.lineEdit_key_index.text()) - 1
        else: 
            self.logger.error("Please provide a valid index number!")
            return 5

        try:
            tomo_lists = [sorted(x, key = lambda y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) for x in tomo_lists]
        except:
            self.logger.error("It looks like the tilt info index info is wrong! For example, Please check the tilt info index for {} is {}".\
                              format(tomo_lists[-1][0], key_index_sort+1))
            return 5

        rawtlt_lists = [[float(x.split(image_file_suffix)[0].split(delimiter)[key_index_sort]) for x in y] for y in tomo_lists]
        if self.comboBox_rm_dup.currentText()== "Yes":
            for i,tlts in enumerate(rawtlt_lists):
                pop_list = []
                for j, tlt in enumerate(tlts):
                    if j > 0 and tlt == tlts[j-1]:
                        pop_list.append(j-1)
                for k in sorted(pop_list, reverse=True):
                    del rawtlt_lists[i][k]
                    del tomo_lists[i][k]

        if not len(self.lineEdit_min_num_tilt.text()) > 0:
            min_num_tilt = 30
        else:
            min_num_tilt = int(self.lineEdit_min_num_tilt.text())
        tomo_lists = [x for x in tomo_lists if len(x) >= min_num_tilt]
        rawtlt_lists = [x for x in rawtlt_lists if len(x) >= min_num_tilt]    

        self.logger.info("Check: Total tomo # is {} from {} images".format(len(tomo_lists), len(images_list)))