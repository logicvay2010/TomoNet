import os, glob, subprocess, shutil
import logging
import json
import numpy as np

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTabWidget, QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog, QLineEdit

from TomoNet.util import browse, metadata
from TomoNet.util.io import mkfolder
from TomoNet.util.utils import string2float, string2int, idx2list
from TomoNet.process.bash_gts import Generate_TS
from TomoNet.process.bash_aretomo import AreTomo


class Recon(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabShape(QtWidgets.QTabWidget.Triangular)

        ############### Define variables ################
        self.ts_folder = "Recon/ts_tlt"
        self.etomo_folder = "Recon/eTomo"
        self.areTomo_folder = "Recon/AreTomo"
        self._history_record = "Recon/history_record.txt"
        self.current_ts_list = None
        self.current_ts_list_selected = []
        self.current_tomoNames_aretomo = []
        ############### Define variables ################
        
        self.log_file = "Recon/recon.log"
        self.note_json = "Recon/notes.json"
        self.check_log_file("Recon")

        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

                
        self.setupUi()
        self.setupUi_aretomo()


        self.retranslateUi()
        self.retranslateUi_aretomo()

        self.thread_gt = None
        self.thread_aretomo = None

        self.pushButton_check_tomo_num.clicked.connect(self.check_tomo_num)

        self.pushButton_corrected_image_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_corrected_image_folder)) 
        
        self.pushButton_run_ts_generation.clicked.connect(self.generate_ts)

        self.pushButton_reload.clicked.connect(self.reload_table)

        self.pushButton_run_aretomo.clicked.connect(self.run_aretomo)

        self.pushButton_aretomo_input_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_aretomo_input_folder)) 
        
        self.currentChanged.connect(self.tab_changed)
        
        self.tableView.doubleClicked.connect(self.table_click)

        self.tableView_aretomo.doubleClicked.connect(self.table_click_aretomo)

        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        self.lineEdit_aretomo_input_folder.textChanged.connect(self.aretomo_count_tomo)

        self.setting_file ="Recon/recon.setting"
        
        self.read_setting()

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
        
        sizePolicy.setHeightForWidth(self.label_base_name.sizePolicy().hasHeightForWidth())
        self.label_base_name.setSizePolicy(sizePolicy)
        self.label_base_name.setMinimumSize(QtCore.QSize(150, 0))
        self.label_base_name.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_base_name.setObjectName("label_base_name")
        self.horizontalLayout_2.addWidget(self.label_base_name)
        self.lineEdit_base_name = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_base_name.setInputMask("")
        #self.lineEdit_base_name.setMinimumSize(QtCore.QSize(140, 0))
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
        self.lineEdit_delimiter.setMaximumSize(QtCore.QSize(50, 30))
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
        self.lineEdit_key_index.setMaximumSize(QtCore.QSize(50, 30))
        self.horizontalLayout_2.addWidget(self.lineEdit_key_index)

        self.label_flip_axis = QtWidgets.QLabel(self.tab)
        self.label_flip_axis.setSizePolicy(sizePolicy)
        self.label_flip_axis.setMinimumSize(QtCore.QSize(100, 0))
        self.label_flip_axis.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_flip_axis.setObjectName("label_flip_axis")
        self.horizontalLayout_2.addWidget(self.label_flip_axis)
        self.comboBox_flip_axis = QtWidgets.QComboBox(self.tab)
        self.comboBox_flip_axis.setObjectName("comboBox_flip_axis")
        self.comboBox_flip_axis.addItem("")
        self.comboBox_flip_axis.addItem("")
        self.comboBox_flip_axis.addItem("")
        self.comboBox_flip_axis.setMaximumWidth(60)
        self.horizontalLayout_2.addWidget(self.comboBox_flip_axis)

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
        self.label_base_name_index.setMinimumSize(QtCore.QSize(150, 0))
        self.label_base_name_index.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_base_name_index.setObjectName("label_base_name_index")
        self.horizontalLayout_5.addWidget(self.label_base_name_index)
        self.lineEdit_base_name_index = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_base_name_index.setInputMask("")
        #self.lineEdit_base_name_index.setMinimumSize(QtCore.QSize(60, 0))
        self.lineEdit_base_name_index.setObjectName("lineEdit_base_name_index")
        self.lineEdit_base_name_index.setMaximumSize(QtCore.QSize(50, 30))
        self.horizontalLayout_5.addWidget(self.lineEdit_base_name_index)
        
        self.label_target_base_name = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_target_base_name.sizePolicy().hasHeightForWidth())
        self.label_target_base_name.setSizePolicy(sizePolicy)
        self.label_target_base_name.setMinimumSize(QtCore.QSize(160, 0))
        self.label_target_base_name.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_target_base_name.setIndent(-1)
        self.label_target_base_name.setObjectName("label_target_base_name")
        self.horizontalLayout_5.addWidget(self.label_target_base_name)
        self.lineEdit_target_base_name = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_target_base_name.setInputMask("")
        self.lineEdit_target_base_name.setObjectName("lineEdit_target_base_name")
        self.lineEdit_target_base_name.setMaximumSize(QtCore.QSize(100, 30))
        self.horizontalLayout_5.addWidget(self.lineEdit_target_base_name)
        
        self.label_image_file_suffix = QtWidgets.QLabel(self.tab)
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
        self.lineEdit_cpus.setMaximumSize(QtCore.QSize(40, 30))
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
        self.lineEdit_min_num_tilt.setMaximumSize(QtCore.QSize(40, 30))
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
        self.label_remove_dup.setMinimumSize(QtCore.QSize(120, 0))
        self.label_remove_dup.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_remove_dup.setObjectName("label_remove_dup")
        self.horizontalLayout_3.addWidget(self.label_remove_dup)
        self.comboBox_rm_dup = QtWidgets.QComboBox(self.tab)
        self.comboBox_rm_dup.setObjectName("comboBox_rm_dup")
        self.comboBox_rm_dup.addItem("")
        self.comboBox_rm_dup.addItem("")
        #self.comboBox_rm_dup.setMaximumWidth(60)
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
        #self.comboBox_new_data.setMaximumWidth(60)
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

    def setupUi_aretomo(self):
        self.tab_aretomo = QtWidgets.QWidget()
        self.tab_aretomo.setObjectName("tab")

        scriptDir = os.path.dirname(os.path.realpath(__file__))

        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab_aretomo)
        self.gridLayout_3.setObjectName("gridLayout_3")
        
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_aretomo_input_folder = QtWidgets.QLabel(self.tab_aretomo)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_aretomo_input_folder.sizePolicy().hasHeightForWidth())
        self.label_aretomo_input_folder.setSizePolicy(sizePolicy)
        self.label_aretomo_input_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_aretomo_input_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_aretomo_input_folder.setObjectName("label_aretomo_input_folder")
        self.horizontalLayout_6.addWidget(self.label_aretomo_input_folder)
        
        self.lineEdit_aretomo_input_folder = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_aretomo_input_folder.setInputMask("")
        self.lineEdit_aretomo_input_folder.setObjectName("lineEdit_aretomo_input_folder")
        self.horizontalLayout_6.addWidget(self.lineEdit_aretomo_input_folder)

        self.pushButton_aretomo_input_folder = QtWidgets.QPushButton(self.tab_aretomo)
        self.pushButton_aretomo_input_folder.setText("")
        self.pushButton_aretomo_input_folder.setIcon(icon)
        self.pushButton_aretomo_input_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_aretomo_input_folder.setMaximumSize(QtCore.QSize(60, 24))
        self.pushButton_aretomo_input_folder.setObjectName("pushButton_aretomo_input_folder")
        self.horizontalLayout_6.addWidget(self.pushButton_aretomo_input_folder)

        self.label_aretomo_tomoNum_detect = QtWidgets.QLabel(self.tab_aretomo)
        self.label_aretomo_tomoNum_detect.setSizePolicy(sizePolicy)
        self.label_aretomo_tomoNum_detect.setMinimumSize(QtCore.QSize(120, 0))
        self.label_aretomo_tomoNum_detect.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_aretomo_tomoNum_detect.setObjectName("label_aretomo_tomoNum_detect")
        self.horizontalLayout_6.addWidget(self.label_aretomo_tomoNum_detect)
        
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        
        self.label_VolZ = QtWidgets.QLabel(self.tab_aretomo)
        self.label_VolZ.setSizePolicy(sizePolicy)
        self.label_VolZ.setMinimumSize(QtCore.QSize(40, 0))
        self.label_VolZ.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_VolZ.setObjectName("label_VolZ")
        self.horizontalLayout_7.addWidget(self.label_VolZ)
        
        self.lineEdit_VolZ = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_VolZ.setInputMask("")
        self.lineEdit_VolZ.setMinimumSize(QtCore.QSize(160, 0))
        self.lineEdit_VolZ.setObjectName("lineEdit_VolZ")
        self.horizontalLayout_7.addWidget(self.lineEdit_VolZ)
        
        self.label_OutBin = QtWidgets.QLabel(self.tab_aretomo)
        self.label_OutBin.setSizePolicy(sizePolicy)
        self.label_OutBin.setMinimumSize(QtCore.QSize(60, 0))
        self.label_OutBin.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_OutBin.setObjectName("label_OutBin")
        self.horizontalLayout_7.addWidget(self.label_OutBin)
        
        self.lineEdit_OutBin = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_OutBin.setInputMask("")
        self.lineEdit_OutBin.setObjectName("lineEdit_OutBin")
        self.horizontalLayout_7.addWidget(self.lineEdit_OutBin)
        
        self.label_TiltAxis = QtWidgets.QLabel(self.tab_aretomo)
        self.label_TiltAxis.setSizePolicy(sizePolicy)
        self.label_TiltAxis.setMinimumSize(QtCore.QSize(60, 0))
        self.label_TiltAxis.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_TiltAxis.setObjectName("label_TiltAxis")
        self.horizontalLayout_7.addWidget(self.label_TiltAxis)
        
        self.lineEdit_TiltAxis = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_TiltAxis.setInputMask("")
        self.lineEdit_TiltAxis.setObjectName("lineEdit_TiltAxis")
        self.horizontalLayout_7.addWidget(self.lineEdit_TiltAxis)        

        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        
        self.label_OutImod = QtWidgets.QLabel(self.tab_aretomo)
        self.label_OutImod.setSizePolicy(sizePolicy)
        self.label_OutImod.setMinimumSize(QtCore.QSize(60, 0))
        self.label_OutImod.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_OutImod.setObjectName("label_OutImod")
        self.horizontalLayout_8.addWidget(self.label_OutImod)
        
        self.lineEdit_OutImod = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_OutImod.setInputMask("")
        self.lineEdit_OutImod.setMinimumSize(QtCore.QSize(160, 0))
        self.lineEdit_OutImod.setObjectName("lineEdit_OutImod")
        self.horizontalLayout_8.addWidget(self.lineEdit_OutImod)
        
        self.label_FlipVol = QtWidgets.QLabel(self.tab_aretomo)
        self.label_FlipVol.setSizePolicy(sizePolicy)
        self.label_FlipVol.setMinimumSize(QtCore.QSize(60, 0))
        self.label_FlipVol.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_FlipVol.setObjectName("label_FlipVol")
        self.horizontalLayout_8.addWidget(self.label_FlipVol)
        
        self.lineEdit_FlipVol = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_FlipVol.setInputMask("")
        self.lineEdit_FlipVol.setObjectName("lineEdit_FlipVol")
        self.horizontalLayout_8.addWidget(self.lineEdit_FlipVol)
        
        self.label_UseAlnFile = QtWidgets.QLabel(self.tab_aretomo)
        self.label_UseAlnFile.setSizePolicy(sizePolicy)
        self.label_UseAlnFile.setMinimumSize(QtCore.QSize(60, 0))
        self.label_UseAlnFile.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_UseAlnFile.setObjectName("label_UseAlnFile")
        self.horizontalLayout_8.addWidget(self.label_UseAlnFile)
        
        self.lineEdit_UseAlnFile = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_UseAlnFile.setInputMask("")
        self.lineEdit_UseAlnFile.setObjectName("lineEdit_UseAlnFile")
        self.horizontalLayout_8.addWidget(self.lineEdit_UseAlnFile)  

        self.label_GPU_ID = QtWidgets.QLabel(self.tab_aretomo)
        self.label_GPU_ID.setSizePolicy(sizePolicy)
        self.label_GPU_ID.setMinimumSize(QtCore.QSize(60, 0))
        self.label_GPU_ID.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_GPU_ID.setObjectName("label_GPU_ID")
        self.horizontalLayout_8.addWidget(self.label_GPU_ID)
        
        self.lineEdit_GPU_ID = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_GPU_ID.setInputMask("")
        self.lineEdit_GPU_ID.setObjectName("lineEdit_GPU_ID")
        self.horizontalLayout_8.addWidget(self.lineEdit_GPU_ID) 
        
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")

        self.label_aretomo_addtional_param = QtWidgets.QLabel(self.tab_aretomo)
        self.label_aretomo_addtional_param.setSizePolicy(sizePolicy)
        self.label_aretomo_addtional_param.setMinimumSize(QtCore.QSize(90, 0))
        self.label_aretomo_addtional_param.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_aretomo_addtional_param.setObjectName("label_aretomo_addtional_param")
        self.horizontalLayout_9.addWidget(self.label_aretomo_addtional_param)
        
        self.lineEdit_aretomo_addtional_param = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_aretomo_addtional_param.setInputMask("")
        self.lineEdit_aretomo_addtional_param.setObjectName("lineEdit_aretomo_addtional_param")
        self.horizontalLayout_9.addWidget(self.lineEdit_aretomo_addtional_param)

        self.label_tomo_index = QtWidgets.QLabel(self.tab_aretomo)
        self.label_tomo_index.setSizePolicy(sizePolicy)
        self.label_tomo_index.setMinimumSize(QtCore.QSize(100, 0))
        self.label_tomo_index.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index.setObjectName("label_tomo_index")
        self.horizontalLayout_9.addWidget(self.label_tomo_index)

        self.lineEdit_tomo_index = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_tomo_index.setInputMask("")
        self.lineEdit_tomo_index.setMaximumSize(QtCore.QSize(100, 30))
        self.lineEdit_tomo_index.setObjectName("lineEdit_tomo_index")
        self.horizontalLayout_9.addWidget(self.lineEdit_tomo_index)

        ############################# Run button ###########################
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem2)
        self.pushButton_run_aretomo = QtWidgets.QPushButton(self.tab_aretomo)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_run_aretomo.sizePolicy().hasHeightForWidth())
        self.pushButton_run_aretomo.setSizePolicy(sizePolicy)
        self.pushButton_run_aretomo.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_run_aretomo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_run_aretomo.setObjectName("run")
        self.horizontalLayout_10.addWidget(self.pushButton_run_aretomo)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_10.addItem(spacerItem3)
        
        
        self.gridLayout_3.addLayout(self.horizontalLayout_6, 0, 0, 1, 1)
        self.gridLayout_3.addLayout(self.horizontalLayout_7, 1, 0, 1, 1)
        self.gridLayout_3.addLayout(self.horizontalLayout_8, 2, 0, 1, 1)
        self.gridLayout_3.addLayout(self.horizontalLayout_9, 3, 0, 1, 1)
        #self.spacerItem_aretomo_1 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #self.gridLayout_3.addItem(self.spacerItem_aretomo_1, 4, 0, 1, 1)
        self.gridLayout_3.addLayout(self.horizontalLayout_10, 4, 0, 1, 1)

        self.tableView_aretomo = QtWidgets.QTableWidget(self)
        
        header_labels_aretomo = metadata.header_labels_aretomo
        
        self.tableView_aretomo.setColumnCount(len(header_labels_aretomo))
        self.tableView_aretomo.setHorizontalHeaderLabels(header_labels_aretomo)
        
        header_aretomo = self.tableView_aretomo.horizontalHeader()   
        header_aretomo.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView_aretomo.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        
        self.gridLayout_3.addWidget(self.tableView_aretomo, 5, 0)


        self.addTab(self.tab_aretomo, "")

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        self.label_corrected_image_folder.setText(_translate("Form", "Motion Corrected Images Folder:"))
        self.lineEdit_corrected_image_folder.setPlaceholderText(_translate("Form", "MotionCorrection/MotionCor2/corrected_images"))
        self.lineEdit_corrected_image_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            The folder path to your motion corrected images. \
            </span></p></body></html>"))
        self.label_corrected_image_folder.setText(_translate("Form", "Motion Corrected Images Folder:"))
        
        self.label_base_name.setText(_translate("Form", "Filename Filter Text:"))
        self.lineEdit_base_name.setPlaceholderText(_translate("Form", "2018Jan01_HIV"))
        self.lineEdit_base_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            This field is used for image filenames filtering. In case you have mixed data in the same data collection, and you want to process them seperately.\
            Only image filenames contain the provided substring will be selected for Tilt Series (TS) generation. \
            Default: No filter.\
            </span></p></body></html>"))
        
        self.label_delimiter.setText(_translate("Form", "Delimiter:"))
        self.lineEdit_delimiter.setPlaceholderText(_translate("Form", "_"))
        self.lineEdit_delimiter.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Delimiter that seperate text in the image filename, e.g, '_' in 2018Jan01_HIV_mutant_Pos42_00030_30.0_ali.mrc.\
            This image filename will be seperated by this delimiter into [2018Jan01, HIV, mutant, Pos42, 00030, 30.0, _ali.mrc].\
            Default:'_'.\
            </span></p></body></html>"))
        
        self.label_key_index.setText(_translate("Form", "Tilt Info Index:"))
        self.lineEdit_key_index.setPlaceholderText(_translate("Form", "6"))
        self.lineEdit_key_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Related to the delimiter.\
            The index of the tilt info in image filename after seperating by the delimiter.\
            For example, the tilt info (30.0) index is 6 in '2018Jan01_HIV_mutant_Pos42_00030_30.0_ali.mrc'.\
            </span></p></body></html>"))

        self.label_flip_axis.setText(_translate("Form", "Flip Images?"))
        self.comboBox_flip_axis.setItemText(0, _translate("Form", "No"))
        self.comboBox_flip_axis.setItemText(1, _translate("Form", "Horizontally"))
        self.comboBox_flip_axis.setItemText(2, _translate("Form", "Vertically"))
        self.comboBox_flip_axis.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Use this field in case you need to flip images before 3D reconstruction to accomendate defocus or structure handedness.\
            Select either 'Horizontally' (flip over the current X-axis) or 'Vertically' (flip over the current Y-axis).\
            Default: No.\
            </span></p></body></html>"))

        self.label_base_name_index.setText(_translate("Form", "Tomogram Base Name Index:"))
        self.lineEdit_base_name_index.setPlaceholderText(_translate("Form", "1-4"))
        self.lineEdit_base_name_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Related to the delimiter.\
            It is used to identify what are the text that defining one tomogram.\
            For example, in 2018Jan01_HIV_mutant_Pos42_00030_30.0_ali.mrc,\
            'HIV_mutant_Pos42' defines the tomogram at Position 42, thus the index should be 2-4.\
            '2018Jan01_HIV_mutant_Pos42' also defines the tomogram at Position 42, in this case the index should be 1-4.\
            Accepted format: a single integer n or two integers seperate by - (range): n1-n2.\
            </span></p></body></html>"))

        self.label_target_base_name.setText(_translate("Form", "Tomogram Target Base Name:"))
        self.lineEdit_target_base_name.setPlaceholderText(_translate("Form", "TS"))
        self.lineEdit_target_base_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            This program names all output tilt series in the format of \
            '[tomogram_target_base_name]_[index].st'. Default: 'TS'.\
            </span></p></body></html>"))

        self.label_image_file_suffix.setText(_translate("Form", "Image Filename Suffix:"))
        self.lineEdit_image_file_suffix.setPlaceholderText(_translate("Form", "_ali.mrc"))
        self.lineEdit_image_file_suffix.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            This field is used for a second image filenames filtering.\
            Only image filenames ends with provided Suffix will be selected as input.\
            Default: '_ali.mrc'.\
            </span></p></body></html>"))
        
        self.label_cpus.setText(_translate("Form", "CPU(s) #:"))
        self.lineEdit_cpus.setPlaceholderText(_translate("Form", "8"))
        self.lineEdit_cpus.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            CPU(s) # to be used in the TS generation. Default: 8.\
            </span></p></body></html>"))

        self.label_min_num_tilt.setText(_translate("Form", "Minimum Tilts #:"))
        self.lineEdit_min_num_tilt.setPlaceholderText(_translate("Form", "30"))
        self.lineEdit_min_num_tilt.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            The minimum number of tilts expected to generate a tilt series for later 3D reconstruction.\
            Any tilt series with tilts number less than this will be ignored. \
            Please use the 'check' button (next to this) to check expected number of tilt series will be generated with the current setting.\
            Default: 30.\
            </span></p></body></html>"))
        
        self.pushButton_check_tomo_num.setText(_translate("Form", "check"))
        
        self.label_remove_dup.setText(_translate("Form", "Remove Duplicates?:"))
        self.comboBox_rm_dup.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_rm_dup.setItemText(1, _translate("Form", "No"))
        self.comboBox_rm_dup.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Sometimes, multiple images were taken at the same tilt angle, because of the failure of previous ones. \
            Thus, typically only the image with the latest time stamp is needed.\
            Select Yes to exclude the failed ones, otherwise No. Default: Yes.\
            </span></p></body></html>"))
        
        self.label_new_data.setText(_translate("Form", "Only Process Unfinished Data?:"))
        self.comboBox_new_data.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_new_data.setItemText(1, _translate("Form", "No"))
        self.comboBox_new_data.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Select Yes to skip generating tilt series that already processed.\
            Select No to generate all tilt series and overwrite the existing output.\
            The processed data info is recorded in file: Recon/history_record.txt, user can edit this file based on needs.\
            Default: Yes.\
            </span></p></body></html>"))
        
        self.pushButton_run_ts_generation.setText(_translate("Form", "RUN"))
        
        self.setTabText(self.indexOf(self.tab), _translate("Form", "TS Generation"))
        
        self.setTabText(self.indexOf(self.tab1), _translate("Form", "eTomo Reconstruction"))

        self.pushButton_reload.setText(_translate("Form", "Reload"))

    def retranslateUi_aretomo(self):
        _translate = QtCore.QCoreApplication.translate
        self.setTabText(self.indexOf(self.tab_aretomo), _translate("Form", "AreTomo Reconstruction"))

        self.label_aretomo_input_folder.setText(_translate("Form", "Tilt Series Folder:"))
        self.lineEdit_aretomo_input_folder.setPlaceholderText(_translate("Form", "Root/Recon/ts_tlt"))
        self.lineEdit_aretomo_input_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Folder path to your tilt series and tlt files. \
            </span></p></body></html>"))
        self.label_aretomo_tomoNum_detect.setText(_translate("Form", "< 0 Tomo(s) >"))
        
        self.label_VolZ.setText(_translate("Form", "-VolZ:"))
        self.lineEdit_VolZ.setPlaceholderText(_translate("Form", "2000"))
        self.lineEdit_VolZ.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            volume height or the z dimension to unbinned voxels (default: 2000) \
            </span></p></body></html>"))
        
        self.label_OutBin.setText(_translate("Form", "-OutBin:"))
        self.lineEdit_OutBin.setPlaceholderText(_translate("Form", "4"))
        self.lineEdit_OutBin.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Binning of final output reconstruction map (default: 4) \
            </span></p></body></html>"))
        
        self.label_TiltAxis.setText(_translate("Form", "-TiltAxis:"))
        self.lineEdit_TiltAxis.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_TiltAxis.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            tilt axis is relative to the y-axis (vertical axis of tilt image) and rotates counter-clockwise. (default: 0)\
            </span></p></body></html>"))
        
        self.label_OutImod.setText(_translate("Form", "-OutImod:"))
        self.lineEdit_OutImod.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_OutImod.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            0: Disabled; 1: for Relion4; 2: Warp; 3: Global- and local-aligned tilt series (default: 1)\
            </span></p></body></html>"))
        
        self.label_FlipVol.setText(_translate("Form", "-FlipVol:"))
        self.lineEdit_FlipVol.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_FlipVol.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            By default, the x-z slices of the reconstructed volume are saved according to their y coordinates\
            in the output MRC file. -FlipVol 1 saves x-y slices instead according to their z coordinates.(default: 1)\
            </span></p></body></html>"))
        
        self.label_UseAlnFile.setText(_translate("Form", "-UseAlnFile?"))
        self.lineEdit_UseAlnFile.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_UseAlnFile.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Should users decide to reconstruct the volume with a different setting, \
            the corresponding aln file can be loaded by means of -AlnFile to bypass the lengthy alignment process. \
            1: use Aln file if found, 0: redo the alignment (default: 0)\
            </span></p></body></html>"))
        
        self.label_GPU_ID.setText(_translate("Form", "GPUs ID:"))
        self.lineEdit_GPU_ID.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_GPU_ID.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            use format like 0,1,2,3 to use multiple GPUs for parallel processing\
            </span></p></body></html>"))
        
        self.label_aretomo_addtional_param.setText(_translate("Form", "Other Parameters:"))
        self.lineEdit_aretomo_addtional_param.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_aretomo_addtional_param.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Addtional parameters to be used. Follow format: -Option1 value1 -Option2 value2 ...\
            </span></p></body></html>"))
        
        self.label_tomo_index.setText(_translate("Form", "Select Tomo Index:"))
        self.label_tomo_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Select which tomograms to perform Aretomo operation.\
            </span></p></body></html>"))
        self.lineEdit_tomo_index.setPlaceholderText(_translate("Form", "1-5,7-8,12"))
        self.lineEdit_tomo_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"font-size:9pt;\"> different tomo indexes are seperated by comma, sequential indexes are connected by dash. \
            </span></p></body></html>"))
        
        self.pushButton_run_aretomo.setText(_translate("Form", "RUN"))

    def generate_ts(self):
        if self.pushButton_run_ts_generation.text() == "RUN":
            if len(self.lineEdit_corrected_image_folder.text()) > 0:
                corrected_folder_path = self.lineEdit_corrected_image_folder.text()
            else: 
                self.logger.error( "The corrected image folder path cannot be empty!")
                return -1        
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
                    self.logger.warning("Filename Filter Text is not provided.")
                    base_name = ""

                if len(self.lineEdit_image_file_suffix.text()) > 0:
                    image_file_suffix = self.lineEdit_image_file_suffix.text()
                else: 
                    self.logger.warning("Image Filename Suffix is empty. Use default '_ali.mrc'")
                    image_file_suffix = "_ali.mrc"

                try:
                    file_names = "{}/*{}*{}".format(corrected_folder_path, base_name, image_file_suffix)
                    images_list = sorted([os.path.basename(x) for x in glob.glob(file_names)])
                except Exception as err:
                    self.logger.error(f"Unexpected {err=}, {type(err)=}")
                    self.logger.error("Please check your corrected images fold path!")
                    self.cmd_finished()
                    return -1
                
                delimiter = self.lineEdit_delimiter.text() if len(self.lineEdit_delimiter.text()) > 0 else '_'
                
                if len(self.lineEdit_base_name_index.text()) > 0:
                    base_name_index = self.lineEdit_base_name_index.text()
                    if '-' in base_name_index:
                        try:
                            key_index = [int(x) for x in base_name_index.split('-')]
                            key_index[0]-=1
                        except:
                            self.logger.error("Tomogram Base Name Index format error!")
                            self.cmd_finished()
                            return -1
                    else:
                        try:
                            key_index = [int(base_name_index)-1, int(base_name_index)]
                        except:
                            self.logger.error("Tomogram Base Name Index format error!")
                            self.cmd_finished()
                            return -1
                    if len(key_index) != 2:
                        self.logger.error("Tomogram Base Name Index format error!")
                        self.cmd_finished()
                        return -1
                else: 
                    self.logger.error("Please provide Tomogram Base Name Index for identifying tilts for each tomogram!")
                    self.cmd_finished()                    
                    return -1

                if len(images_list) <= 0:
                    self.logger.error("No specified images are detected! Please make sure the images exist and the parameters are correctly set.")
                    self.cmd_finished()
                    return -1
                else:
                    tomo_lists = []
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
                    
                if self.lineEdit_key_index.text().isdigit():
                    key_index_sort = int(self.lineEdit_key_index.text()) - 1
                else: 
                    self.logger.error("Please provide a valid Tilt Info Index number!")
                    self.cmd_finished()
                    return -1
          
                try:
                    tomo_lists = [sorted(x, key = lambda \
                                y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) \
                                for x in tomo_lists]
                    rawtlt_lists = [[float(x.split(image_file_suffix)[0].split(delimiter)[key_index_sort])\
                                for x in y] for y in tomo_lists]
                except Exception as err:
                    self.logger.error(f"Unexpected {err=}, {type(err)=}")
                    self.cmd_finished()
                    return -1
                
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
                    self.logger.warning("Minimum Tilts # is not provided, use 30 as default.")
                else:
                    min_num_tilt = string2int(self.lineEdit_min_num_tilt.text())
                    if min_num_tilt == None:
                        self.logger.error("The Minimum Tilts # format is invalid!")
                        self.cmd_finished()
                        return -1
                    #min_num_tilt = int(self.lineEdit_min_num_tilt.text())
                
                try:
                    tomo_lists = [x for x in tomo_lists if len(x) >= min_num_tilt]
                    rawtlt_lists = [x for x in rawtlt_lists if len(x) >= min_num_tilt]
                except Exception as err:
                    self.logger.error(f"Unexpected {err=}, {type(err)=}")
                    self.cmd_finished()
                    return -1
                
                only_process_unfinished = self.comboBox_new_data.currentText()
                if only_process_unfinished == "No":
                    only_process_unfinished = 0
                else:
                    only_process_unfinished = 1
                # if only_process_unfinished == "Yes":
                #     try:
                #         current_ts_list = sorted([os.path.basename(x) for x in glob.glob("{}/*.st".format(self.ts_folder))])
                #         if len(current_ts_list) > 0:
                #             indexes = [int(os.path.splitext(x)[0].split("_")[-1]) for x in current_ts_list]
                #             indexes.sort()
                #             last_index = indexes[-1]
                #             start_index = int(last_index) + 1
                #         else:
                #             start_index = 1
                #     except:
                #         self.logger.error("error when check current TS info!")
                #         return 6
                # else:
                    # start_index = 1
                
                start_index = 1
                self.logger.info("########Total TS # detected is {} from {} tilt images, the minimum number of tilts used is {}.########".format(len(tomo_lists), len(images_list), min_num_tilt))
                #self.logger.info("########The generated tilt series will be saved at {}. Index starts from {}.########".format(self.ts_folder, start_index))
                self.logger.info("########The generated tilt series will be saved under {}/.########".format(self.ts_folder))

                image_folder = self.lineEdit_corrected_image_folder.text()
                
                target_base_name = self.lineEdit_target_base_name.text() \
                    if not self.lineEdit_target_base_name.text() == "" else "TS"
                
                cpus = string2int(self.lineEdit_cpus.text()) if len(self.lineEdit_cpus.text()) > 0 else 8
                if cpus == None:
                    self.logger.error("The CPUs # format is invalid!")
                    self.cmd_finished()
                    return -1

                flip_axis = self.comboBox_flip_axis.currentIndex()

                if not self.thread_gt:
                    self.thread_gt = Generate_TS(image_folder, tomo_lists,\
                        rawtlt_lists, target_base_name, start_index, delimiter,\
                        key_index, self.ts_folder, cpus, flip_axis, only_process_unfinished)
                else:
                    self.thread_gt = Generate_TS(image_folder, tomo_lists,\
                        rawtlt_lists, target_base_name, start_index, delimiter,\
                        key_index, self.ts_folder, cpus, flip_axis, only_process_unfinished)

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

    def read_setting(self):
        if os.path.exists(self.setting_file):
            data = {}
            data['image_folder'] = ""
            data['base_name'] = ""
            data['delimiter'] = ""
            data['key_index'] = ""
            data['flip_axis'] = 0
            data['min_num_tilt'] = ""
            data['target_base_name'] = ""
            data['rm_dup'] = "Yes"
            data['new_data'] = "Yes"
            data['base_name_index'] = ""
            data['image_file_suffix'] = ""
            data['cpus'] = ""

            #tab 3
            data['aretomo_input_folder'] = ""
            data['VolZ'] = ""
            data['OutBin'] = ""
            data['TiltAxis'] = ""
            data['OutImod'] = ""
            data['FlipVol'] = ""
            data['UseAlnFile'] = ""
            data['GPU_ID'] = ""
            data['aretomo_addtional_param'] = ""
            data['lineEdit_tomo_index'] = ""
            try:
                with open(self.setting_file) as f:
                    for line in f:
                        (k, v) = line.split(":")
                        data[k] = v.strip()
                self.lineEdit_corrected_image_folder.setText(data['image_folder'])
                self.lineEdit_base_name.setText(data['base_name'])
                self.lineEdit_delimiter.setText(data['delimiter'])
                self.lineEdit_key_index.setText(data['key_index'])
                self.comboBox_flip_axis.setCurrentIndex(int(data['flip_axis']))
                self.lineEdit_base_name_index.setText(data['base_name_index'])
                self.lineEdit_image_file_suffix.setText(data['image_file_suffix'])
                self.lineEdit_cpus.setText(data['cpus'])
                self.lineEdit_min_num_tilt.setText(data['min_num_tilt'])
                self.lineEdit_target_base_name.setText(data['target_base_name'])
                self.comboBox_rm_dup.setCurrentText(data['rm_dup'])
                self.comboBox_new_data.setCurrentText(data['new_data'])

                #tab 3
                self.lineEdit_aretomo_input_folder.setText(data['aretomo_input_folder'])
                self.lineEdit_VolZ.setText(data['VolZ'])
                self.lineEdit_OutBin.setText(data['OutBin'])
                self.lineEdit_TiltAxis.setText(data['TiltAxis'])
                self.lineEdit_OutImod.setText(data['OutImod'])
                self.lineEdit_FlipVol.setText(data['FlipVol'])
                self.lineEdit_UseAlnFile.setText(data['UseAlnFile'])
                self.lineEdit_GPU_ID.setText(data['GPU_ID'])
                self.lineEdit_aretomo_addtional_param.setText(data['aretomo_addtional_param'])
                self.lineEdit_tomo_index.setText(data['lineEdit_tomo_index'])
                
            except:
                self.logger.error("error reading {}!".format(self.setting_file))

    def save_setting(self):
        param = {}
        param['image_folder'] = self.lineEdit_corrected_image_folder.text()
        param['base_name'] = self.lineEdit_base_name.text()
        param['delimiter'] = self.lineEdit_delimiter.text()
        param['key_index'] = self.lineEdit_key_index.text()
        param['flip_axis'] = self.comboBox_flip_axis.currentIndex()
        param['base_name_index'] = self.lineEdit_base_name_index.text()
        param['image_file_suffix'] = self.lineEdit_image_file_suffix.text()
        param['cpus'] = self.lineEdit_cpus.text()
        param['min_num_tilt'] = self.lineEdit_min_num_tilt.text()
        param['target_base_name'] = self.lineEdit_target_base_name.text()
        param['rm_dup'] = self.comboBox_rm_dup.currentText()
        param['new_data'] = self.comboBox_new_data.currentText()

        #tab aretomo
        param['aretomo_input_folder'] = self.lineEdit_aretomo_input_folder.text()
        param['VolZ'] = self.lineEdit_VolZ.text()
        param['OutBin'] = self.lineEdit_OutBin.text()
        param['TiltAxis'] = self.lineEdit_TiltAxis.text()
        param['OutImod'] = self.lineEdit_OutImod.text()
        param['FlipVol'] = self.lineEdit_FlipVol.text()
        param['UseAlnFile'] = self.lineEdit_UseAlnFile.text()
        param['GPU_ID'] = self.lineEdit_GPU_ID.text()
        param['aretomo_addtional_param'] = self.lineEdit_aretomo_addtional_param.text()
        param['lineEdit_tomo_index'] = self.lineEdit_tomo_index.text()
        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            pass

    def tab_changed(self,i):
        if i == 1:
            self.reload_table()
        if i == 2:
            self.reload_table_aretomo()
            self.aretomo_count_tomo()

    def natural_keys(self, text):
        return int(text.split("_")[-1]) 

    def read_tomo(self, folder_path):
        #folder_path = self.ts_folder
        tomoNames1 = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*.st".format(folder_path)))]
        tomoNames2 = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*.rawtlt".format(folder_path)))]

        tomoNames = sorted(list(set(tomoNames1) & set(tomoNames2)))
        try:
            tomoNames.sort(key=self.natural_keys)
        except:
            pass

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
            cmd = "3dmod -b 8,1 {}".format(current_st_link_path)
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
                mkfolder(current_tomo_folder)

                current_st_link_path = "{}/{}.st".format(self.ts_folder,tomoName)
                current_rawtlt_link_path = "{}/{}.rawtlt".format(self.ts_folder,tomoName)
                cmd = "cd {} ; ln -s ../../../{} ./ ; ln -s ../../../{} ./ ; etomo".format(current_tomo_folder, current_st_link_path, current_rawtlt_link_path)
                
                subprocess.check_output(cmd, shell=True)

                self.reload_table()
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
        elif j == 5:
            if self.tableView.item(i, j).text().strip() == "NA":
                pass
            else:
                tomoName = self.tableView.item(i, 0).text()
                rec_path = self.read_recon_folder(tomoName, self.etomo_folder)[6]
                cmd = "3dmod {}".format(rec_path)
                os.system(cmd)
                #subprocess.check_output(cmd, shell=True)
        elif j == 12:
            previous_text = self.tableView.item(i, j).text()
            text, ok = QInputDialog.getText(self, 'Take notes!', 'Confirm changes?', QLineEdit.Normal, previous_text)
            if ok:
                self.tableView.setItem(i, j, QTableWidgetItem(text))

                params = self.get_note_params(1)

                with open("{}".format(self.note_json), 'w') as fp:
                    json.dump(params, fp, indent=2, default=int)
    
    def table_click_aretomo(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.tableView_aretomo.item(i, 0).text()
        if j == 1:
            current_st_link_path = "{}/{}.st".format(self.ts_folder, tomoName)
            cmd = "3dmod -b 8,1 {}".format(current_st_link_path)
            os.system(cmd)
        elif j == 2:
            try:
                if self.tableView_aretomo.item(i, j).text().strip() == "NA":
                    pass
                else:
                    tomoName = self.tableView_aretomo.item(i, 0).text()
                    rec_path = self.read_recon_folder(tomoName, self.areTomo_folder)[6]
                    cmd = "3dmod {}".format(rec_path)
                    os.system(cmd)
            except:
                pass
        elif j == 7:
            previous_text = self.tableView_aretomo.item(i, j).text()
            text, ok = QInputDialog.getText(self, 'Take notes!', 'Confirm changes?', QLineEdit.Normal, previous_text)
            if ok:
                self.tableView_aretomo.setItem(i, j, QTableWidgetItem(text))

                params = self.get_note_params(2)

                with open("{}".format(self.note_json), 'w') as fp:
                    json.dump(params, fp, indent=2, default=int)

    def get_note_params(self, code):
        if code == 1:
            tableView = self.tableView
        else:
            tableView = self.tableView_aretomo
        
        row_count = tableView.rowCount()
        params = {}
        index = 12 if code == 1 else 7
        for i in range(row_count):
            params[tableView.item(i, 0).text()] = tableView.item(i, index).text()
        return params

    def read_recon_folder(self, tomoName, rec_root):

        tilt_num, re_mean, re_range, binning, thickness_nm, skipped_view = ["", "", "", "", "", ""]
        etomo_path = "{}/{}".format(rec_root, tomoName)

        tiltcom_path = "{}/{}".format(etomo_path, "tilt.com")
        #st_path = "{}/{}.st".format(etomo_path, tomoName)
        st_path = "{}/{}.st".format(self.ts_folder, tomoName)
        rec_path = "{}/{}.rec".format(etomo_path, tomoName)
        mrc_path = "{}/{}_rec.mrc".format(etomo_path, tomoName)
        final_rec_path = ""
        if os.path.exists(rec_path) or os.path.exists(mrc_path):
            try:                
                d_st = self.read_header(st_path)
                if os.path.exists(rec_path):
                    d_rec = self.read_header(rec_path)
                    final_rec_path = rec_path
                else:
                    d_rec = self.read_header(mrc_path)
                    final_rec_path = mrc_path

                tilt_num = str(d_st["sections"])
                
                taError_path = "{}/{}".format(etomo_path, "taError.log")
                
                binning = str(int(np.round(d_rec["apix"]/d_st["apix"], 0)))

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
        return [tilt_num, re_mean, re_range, binning, thickness_nm, skipped_view, final_rec_path]
    
    def read_header(self, file_path):
        d = {}
        d['apix'] = 1.0
        cmd = "header {} ".format(file_path)
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
        tomoNames = self.read_tomo(self.ts_folder)
        self.tableView.setRowCount(0)
        self.tableView.setRowCount(len(tomoNames))
        
        try:
            with open(self.note_json) as f:
                note_dict = json.load(f)
        except:
            note_dict = {}
        if len(tomoNames) > 0:
            for i, tomo in enumerate(tomoNames):
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
                
                items = self.read_recon_folder(tomo, self.etomo_folder)

                if len(items[6]) > 0:
                    action_view = QTableWidgetItem(os.path.basename(items[6]))
                else:
                    action_view = QTableWidgetItem("NA")
                
                action_view.setBackground(QtGui.QColor("#d0bdf4"))
                action_view.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 5, action_view)

                self.tableView.setItem(i, 6, QTableWidgetItem(items[0]))
                self.tableView.setItem(i, 7, QTableWidgetItem(items[1]))
                self.tableView.setItem(i, 8, QTableWidgetItem(items[2]))
                self.tableView.setItem(i, 9, QTableWidgetItem(items[3]))
                if len(items[4]) > 0:
                    self.tableView.setItem(i, 10, QTableWidgetItem("{} nm".format(str(int(items[4])/10))))
                else:
                    self.tableView.setItem(i, 10, QTableWidgetItem(""))
                self.tableView.setItem(i, 11, QTableWidgetItem(items[5]))
                notes_i = note_dict[tomo] if tomo in note_dict.keys() else ""
                self.tableView.setItem(i, 12, QTableWidgetItem(notes_i))

    def reload_table_aretomo(self):
        tomoNames = self.read_tomo(self.lineEdit_aretomo_input_folder.text())
        self.tableView_aretomo.setRowCount(0)
        self.tableView_aretomo.setRowCount(len(tomoNames))
        try:
            with open(self.note_json) as f:
                note_dict = json.load(f)
        except:
            note_dict = {}
        if len(tomoNames) > 0:
            for i, tomo in enumerate(tomoNames):
                self.tableView_aretomo.setItem(i, 0, QTableWidgetItem(tomo))                
                action_check = QTableWidgetItem("View ST")
                action_check.setBackground(QtGui.QColor("#a0d2eb"))
                action_check.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView_aretomo.setItem(i, 1, action_check)
                
                items = self.read_recon_folder(tomo, self.areTomo_folder)

                if len(items[6]) > 0:
                    action_view = QTableWidgetItem(os.path.basename(items[6]))
                else:
                    action_view = QTableWidgetItem("NA")
                
                action_view.setBackground(QtGui.QColor("#d0bdf4"))
                action_view.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView_aretomo.setItem(i, 2, action_view)

                self.tableView_aretomo.setItem(i, 3, QTableWidgetItem(items[0]))
                self.tableView_aretomo.setItem(i, 4, QTableWidgetItem(items[3]))
                if len(items[4]) > 0:
                    self.tableView_aretomo.setItem(i, 5, QTableWidgetItem("{} nm".format(str(int(items[4])/10))))
                else:
                    self.tableView_aretomo.setItem(i, 5, QTableWidgetItem(""))
                self.tableView_aretomo.setItem(i, 6, QTableWidgetItem(items[5]))
                notes_i = note_dict[tomo] if tomo in note_dict.keys() else ""
                self.tableView_aretomo.setItem(i, 7, QTableWidgetItem(notes_i))
        self.current_tomoNames_aretomo = tomoNames
    
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
            self.logger.error( "The Corrected Image Folder Path cannot be empty!")
            return -1
        
        if len(self.lineEdit_base_name.text()) >0:
            base_name = self.lineEdit_base_name.text()
        else: 
            self.logger.warning("Filename Filter Text is not provided.")
            base_name = ""

        if len(self.lineEdit_image_file_suffix.text()) > 0:
            image_file_suffix = self.lineEdit_image_file_suffix.text()
        else: 
            self.logger.warning("Image Filename Suffix is empty. Use default '_ali.mrc'")
            image_file_suffix = "_ali.mrc"
        
        try:
            file_names = "{}/*{}*{}".format(corrected_folder_path, base_name, image_file_suffix)
            images_list = sorted([os.path.basename(x) for x in glob.glob(file_names)])
        except Exception as err:
            self.logger.error(f"Unexpected {err=}, {type(err)=}")
            self.logger.error("Please check your corrected images fold path!")
            return -1

        delimiter = self.lineEdit_delimiter.text() if len(self.lineEdit_delimiter.text()) > 0 else '_'
        
        if len(self.lineEdit_base_name_index.text()) > 0:
            base_name_index = self.lineEdit_base_name_index.text()
            if '-' in base_name_index:
                try:
                    key_index = [int(x) for x in base_name_index.split('-')]
                    key_index[0]-=1
                except:
                    self.logger.error("Tomogram Base Name Index format error!")
                    return -1
            else:
                try:
                    key_index = [int(base_name_index)-1, int(base_name_index)]
                except:
                    self.logger.error("Tomogram Base Name Index format error!")
                    return -1
            if len(key_index) != 2:
                self.logger.error("Tomogram Base Name Index format error!")
                return -1
        else: 
            self.logger.error("Please provide Tomogram Base Name Index!")
            return -1
        
        tomo_lists = []
        if len(images_list) <= 0:
            self.logger.error("No specified images are detected! \
                        Please make sure the images exist and the parameters are correctly set.")
            return -1
        else:
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

        if self.lineEdit_key_index.text().isdigit():
            key_index_sort = int(self.lineEdit_key_index.text()) - 1
        else: 
            self.logger.error("Please provide a valid Tilt Info Index number!")
            return -1

        try:
            tomo_lists = [sorted(x, key = lambda y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) for x in tomo_lists]
        except:
            self.logger.error("It looks like the Tilt Info Index is not correct! \
                            Please make sure the Tilt Info Index for {} is {}".\
                            format(tomo_lists[-1][0], key_index_sort+1))
            return -1

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
            self.logger.warning("Minimum Tilts # is not provided, use 30 as default.")
        else:
            min_num_tilt = string2int(self.lineEdit_min_num_tilt.text())
            if min_num_tilt == None:
                self.logger.error("The Minimum Tilts # format is invalid!")
                return -1

        tomo_lists = [x for x in tomo_lists if len(x) >= min_num_tilt]
        rawtlt_lists = [x for x in rawtlt_lists if len(x) >= min_num_tilt]    

        self.logger.info("Check result: Total TS # is {} from {} images".format(len(tomo_lists), len(images_list)))

    ############# for AreTomo tab ###########################
    def aretomo_count_tomo(self):
        folder_path = self.lineEdit_aretomo_input_folder.text()
        if os.path.exists(folder_path):
            self.current_ts_list = sorted([os.path.basename(x) for x in glob.glob("{}/*.st".format(folder_path))])
            if self.current_ts_list and len(self.current_ts_list) > 0:
                self.label_aretomo_tomoNum_detect.setText("< {} Tomo(s)>".format(len(self.current_ts_list)))
            else:
                self.label_aretomo_tomoNum_detect.setText("< 0 Tomo(s)>")
        else:
            self.label_aretomo_tomoNum_detect.setText("< 0 Tomo(s)>")
            try:
                if len(self.lineEdit_aretomo_input_folder.text()) > 0:
                    self.logger.warning("The input folder path is not found!")
            except:
                pass

    def get_aretomo_param(self):
        params = {}

        if not len(self.lineEdit_aretomo_input_folder.text()) > 0:
            return "Please specify the tilt series folder as input!"
        elif not os.path.exists(self.lineEdit_aretomo_input_folder.text()):
            return "The input folder path is not found!"
        else:
            aretomo_input_folder = self.lineEdit_aretomo_input_folder.text()
        params['aretomo_input_folder'] = aretomo_input_folder

        if len(self.lineEdit_VolZ.text()) > 0:
            VolZ = string2int(self.lineEdit_VolZ.text())
            if VolZ == None:
                return "error reading -VolZ value!"   
            if VolZ < 0:
                return "VolZ should be a positive integer!"      
        else:
            VolZ = 2000
        params['VolZ'] = VolZ

        if len(self.lineEdit_OutBin.text()) > 0:
            OutBin = string2int(self.lineEdit_OutBin.text())
            if OutBin == None:
                return "error reading -OutBin value!"   
            if OutBin < 0:
                return "OutBin should be a positive integer!"      
        else:
            OutBin = 4
        params['OutBin'] = OutBin    

        if len(self.lineEdit_TiltAxis.text()) > 0:
            TiltAxis = string2float(self.lineEdit_TiltAxis.text())
            if TiltAxis == None:
                return "error reading -TiltAxis value!"   
        else:
            TiltAxis = 0
        params['TiltAxis'] = TiltAxis      

        if len(self.lineEdit_OutImod.text()) > 0:
            OutImod = string2int(self.lineEdit_OutImod.text())
            if OutImod == None:
                return "error reading -OutImod value!" 
            if OutImod not in [0, 1, 2, 3]:
                return "-OutImod value has to be one from 0, 1, 2, 3!"
        else:
            OutImod = 1
        params['OutImod'] = OutImod    

        if len(self.lineEdit_FlipVol.text()) > 0:
            FlipVol = string2int(self.lineEdit_FlipVol.text())
            if FlipVol == None:
                return "error reading -FlipVol value!" 
            if FlipVol not in [0, 1]:
                return "-FlipVol value has to be one from 0, 1!"
        else:
            FlipVol = 1
        params['FlipVol'] = FlipVol    

        if len(self.lineEdit_UseAlnFile.text()) > 0:
            UseAlnFile = string2int(self.lineEdit_UseAlnFile.text())
            if UseAlnFile == None:
                return "error reading -UseAlnFile value!" 
            if UseAlnFile not in [0, 1]:
                return "-UseAlnFile value has to be one from 0, 1!"
        else:
            UseAlnFile = 0
        params['UseAlnFile'] = UseAlnFile
        
        GPU_ID = self.lineEdit_GPU_ID.text() if len(self.lineEdit_GPU_ID.text()) > 0 else "0"
        params['GPU_ID'] = GPU_ID

        aretomo_addtional_param = self.lineEdit_aretomo_addtional_param.text()
        params['aretomo_addtional_param'] = aretomo_addtional_param
        

        if len(self.lineEdit_tomo_index.text()) > 0:
            try:
                tomo_index = list(set([string2int(x) for x in idx2list(self.lineEdit_tomo_index.text())]))
                
                for i in tomo_index:
                    if not i or i <=0:
                        return "Please use valid format for the select tomo index!"
                self.current_ts_list_selected = []
                if len(tomo_index) > 0:
                    for i in tomo_index:
                        if i > 0 and i <= len(self.current_tomoNames_aretomo):
                            tomo_i = self.current_tomoNames_aretomo[i-1]
                            
                            full_path_i = "{}/{}.st".format(aretomo_input_folder, tomo_i)
                            
                            if os.path.exists(full_path_i):
                                self.current_ts_list_selected.append("{}.st".format(tomo_i))
                else:
                    self.current_ts_list_selected = []
            except:
                return "Please use valid format for the select tomo index!"
        else: 
            self.current_ts_list_selected = []

        params['current_ts_list_selected'] = self.current_ts_list_selected
        
        return params
    
    def run_aretomo(self):
        d = self.get_aretomo_param()
        if (not self.current_ts_list) or len(self.current_ts_list) == 0:
            self.logger.error("No Tomogram has detected yet! Please adjust your tilt series folder!")
        elif type(d) is dict:
            if self.pushButton_run_aretomo.text() == "RUN":
                ret = QMessageBox.question(self, 'Run AreTomo Reconstruction!', \
                    "Run AreTomo for all the image from {}. \
                    \nContinue?\n".format(d['aretomo_input_folder'])\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
                if ret == QMessageBox.Yes:
                    self.pushButton_run_aretomo.setText("STOP")
                    self.pushButton_run_aretomo.setStyleSheet('QPushButton {color: red;}')
                    
                    self.thread_aretomo = AreTomo(d, self.areTomo_folder)
        
                    self.thread_aretomo.finished.connect(self.cmd_finished_aretomo)
                    try:
                        self.thread_aretomo.start()
                    except:
                        self.thread_aretomo.stop_process()
                else:
                    self.cmd_finished_aretomo()
            else :
                ret = QMessageBox.question(self, 'Stop AreTomo Reconstruction!', \
                    "Stop AreTomo Reconstruction! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.pushButton_run_aretomo.setText("RUN")
                    self.pushButton_run_aretomo.setStyleSheet("QPushButton {color: black;}")
        else:
             self.logger.error(d)
             self.cmd_finished_aretomo()

    def cmd_finished_aretomo(self):
        self.pushButton_run_aretomo.setText("RUN")
        self.pushButton_run_aretomo.setStyleSheet("QPushButton {color: black;}")
        self.reload_table_aretomo()