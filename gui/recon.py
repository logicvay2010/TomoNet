import os, glob, subprocess, shutil, logging, json

import numpy as np
from shutil import which

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtWidgets import QTabWidget, QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog, QLineEdit, QWidget

from TomoNet.util import browse, metadata
from TomoNet.util.io import mkfolder, mkfolder_ifnotexist
from TomoNet.util.utils import string2float, string2int, idx2list
from TomoNet.process.bash_gts import Generate_TS
from TomoNet.process.bash_aretomo import AreTomo

class Color(QWidget):

    def __init__(self, color):
        super(Color, self).__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)

class Recon(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.root_folder = "Recon"
        ############### Define variables ################
        self.etomo_ts_folder = "Recon/ts_tlt"
        self.aretomo_ts_folder = "Recon/ts_tlt"
        self.default_ts_folder = "Recon/ts_tlt"
        self.etomo_folder = "Recon/eTomo"
        self.areTomo_folder = "Recon/AreTomo"
        self.etomo_recon_folder = "Recon/etomo_Recons"
        self.aretomo_recon_folder = "Recon/aretomo_Recons"
        self._history_record = "Recon/history_record.txt"
        self.current_ts_list = None
        self.current_ts_list_selected = []
        self.current_tomoNames_aretomo = []

        self.motionCor_folder = "MotionCorrection"
        
        self.total_tomo_num_etomo = 0

        self.total_tomo_num_aretomo = 0

        self.table_display_interval_etomo = 10

        self.table_display_interval_aretomo = 10

        self.table_display_range_etomo = [1,10]
        
        self.table_display_range_aretomo = [1,10]

        self.tomoNames_etomo = []

        self.tomoNames_aretomo = []

        self.etomo_preview_loc = 1
        self.etomo_continue_loc = 2
        self.etomo_startover_loc = 3
        self.etomo_delete_loc = 4
        self.etomo_oddevn_loc = 5
        self.etomo_recon_loc = 6
        self.etomo_notes_loc = 12

        self.aretomo_preview_loc = 1
        self.aretomo_recon_loc = 2
        self.aretomo_notes_loc = 6

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

        self.pushButton_corrected_image_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_corrected_image_folder, location=self.motionCor_folder)) 
        
        self.pushButton_run_ts_generation.clicked.connect(self.generate_ts)

        self.pushButton_export_recon_etomo.clicked.connect(lambda: self.export_recons('etomo'))

        self.pushButton_export_recon_aretomo.clicked.connect(lambda: self.export_recons('aretomo'))

        self.pushButton_run_aretomo.clicked.connect(self.run_aretomo)
        
        self.pushButton_etomo_input_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_etomo_input_folder, location=self.root_folder)) 

        self.pushButton_aretomo_input_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_aretomo_input_folder, location=self.root_folder)) 
        
        self.currentChanged.connect(self.tab_changed)
        
        self.tableView.doubleClicked.connect(self.table_click)

        self.tableView_aretomo.doubleClicked.connect(self.table_click_aretomo)

        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        self.lineEdit_etomo_input_folder.textChanged.connect(self.etomo_count_tomo)
        self.lineEdit_etomo_input_folder.textChanged.connect(self.reload_table)

        self.lineEdit_aretomo_input_folder.textChanged.connect(self.aretomo_count_tomo)
        self.lineEdit_aretomo_input_folder.textChanged.connect(self.reload_table_aretomo)

        self.setting_file ="Recon/recon.setting"
        
        self.read_setting()

        self.fileSystemWatcher = QtCore.QFileSystemWatcher(self)
        self.fileSystemWatcher.addPath(self.log_file)
        self.fileSystemWatcher.fileChanged.connect(self.update_log_window)  

        self.comboBox_display_range_etomo.currentIndexChanged.connect(self.range_changed_etomo)
        self.comboBox_display_range_aretomo.currentIndexChanged.connect(self.range_changed_aretomo)

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
        self.comboBox_flip_axis.setMaximumWidth(120)
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
        
        self.horizontalLayout_3_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_2.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_3_2.setObjectName("horizontalLayout_3_2")
        
        self.label_process_odd_evn = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_process_odd_evn.sizePolicy().hasHeightForWidth())
        self.label_process_odd_evn.setSizePolicy(sizePolicy)
        self.label_process_odd_evn.setMinimumSize(QtCore.QSize(120, 0))
        self.label_process_odd_evn.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_process_odd_evn.setObjectName("label_process_odd_evn")
        self.horizontalLayout_3_2.addWidget(self.label_process_odd_evn)
        self.comboBox_process_odd_evn = QtWidgets.QComboBox(self.tab)
        self.comboBox_process_odd_evn.setObjectName("comboBox_process_odd_evn")
        self.comboBox_process_odd_evn.addItem("")
        self.comboBox_process_odd_evn.addItem("")
        #self.comboBox_process_odd_evn.setMaximumWidth(60)
        self.horizontalLayout_3_2.addWidget(self.comboBox_process_odd_evn)
        self.gridLayout_2.addLayout(self.horizontalLayout_3_2, 4, 0, 1, 1)

        self.spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(self.spacerItem1, 5, 0, 1, 1)

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
        self.gridLayout_2.addLayout(self.horizontalLayout_4, 6, 0, 1, 1)

        self.addTab(self.tab, "")
        
        # eTomo tab
        self.tab1 = QtWidgets.QWidget()
        self.tab1.setObjectName("tab")

        self.gridLayout_recon = QtWidgets.QGridLayout(self.tab1)

        self.horizontalLayout_eTomo_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_eTomo_1.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_eTomo_1.setObjectName("horizontalLayout_eTomo_1")
        self.label_etomo_input_folder = QtWidgets.QLabel(self.tab1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_etomo_input_folder.sizePolicy().hasHeightForWidth())
        self.label_etomo_input_folder.setSizePolicy(sizePolicy)
        self.label_etomo_input_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_etomo_input_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_etomo_input_folder.setObjectName("label_etomo_input_folder")
        self.horizontalLayout_eTomo_1.addWidget(self.label_etomo_input_folder)
        
        self.lineEdit_etomo_input_folder = QtWidgets.QLineEdit(self.tab1)
        self.lineEdit_etomo_input_folder.setInputMask("")
        self.lineEdit_etomo_input_folder.setObjectName("lineEdit_etomo_input_folder")
        self.horizontalLayout_eTomo_1.addWidget(self.lineEdit_etomo_input_folder)

        self.pushButton_etomo_input_folder = QtWidgets.QPushButton(self.tab1)
        self.pushButton_etomo_input_folder.setText("")
        self.pushButton_etomo_input_folder.setIcon(icon)
        self.pushButton_etomo_input_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_etomo_input_folder.setMaximumSize(QtCore.QSize(60, 24))
        self.pushButton_etomo_input_folder.setObjectName("pushButton_etomo_input_folder")
        self.horizontalLayout_eTomo_1.addWidget(self.pushButton_etomo_input_folder)

        self.label_etomo_tomoNum_detect = QtWidgets.QLabel(self.tab1)
        self.label_etomo_tomoNum_detect.setSizePolicy(sizePolicy)
        self.label_etomo_tomoNum_detect.setMinimumSize(QtCore.QSize(120, 0))
        self.label_etomo_tomoNum_detect.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_etomo_tomoNum_detect.setObjectName("label_etomo_tomoNum_detect")
        self.horizontalLayout_eTomo_1.addWidget(self.label_etomo_tomoNum_detect)
        
        self.horizontalLayout_recon = QtWidgets.QHBoxLayout()
        self.horizontalLayout_recon.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_recon.setObjectName("horizontalLayout_recon")
        #self.horizontalLayout_recon.addWidget(Color('white'))

        self.label_recon = QtWidgets.QLabel(self.tab1)
        self.label_recon.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_recon.setAlignment(QtCore.Qt.AlignCenter)
        self.label_recon.setObjectName("label_recon")
        self.label_recon.setText("Summary of 3D Reconstructions")
        self.horizontalLayout_recon.addWidget(self.label_recon)
        self.pushButton_export_recon_etomo = QtWidgets.QPushButton(self.tab1)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.label_dispaly_range_etomo = QtWidgets.QLabel(self.tab1)
        self.label_dispaly_range_etomo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_dispaly_range_etomo.setAlignment(QtCore.Qt.AlignCenter)
        self.label_dispaly_range_etomo.setMaximumSize(QtCore.QSize(80, 30))
        self.label_dispaly_range_etomo.setObjectName("label_dispaly_range_etomo")
        self.label_dispaly_range_etomo.setText("Displaying")
        self.horizontalLayout_recon.addWidget(self.label_dispaly_range_etomo)

        self.comboBox_display_range_etomo = QtWidgets.QComboBox(self.tab1)
        self.comboBox_display_range_etomo.setObjectName("comboBox_display_range_etomo")
        self.comboBox_display_range_etomo.setMaximumSize(QtCore.QSize(85, 30))
        # self.comboBox_display_range_etomo.addItem("")
        # self.comboBox_display_range_etomo.addItem("")
        self.horizontalLayout_recon.addWidget(self.comboBox_display_range_etomo)

        self.pushButton_export_recon_etomo.setSizePolicy(sizePolicy)
        self.pushButton_export_recon_etomo.setMinimumSize(QtCore.QSize(50, 20))
        self.pushButton_export_recon_etomo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_export_recon_etomo.setObjectName("pushButton_export_recon_etomo")
        self.horizontalLayout_recon.addWidget(self.pushButton_export_recon_etomo)
        
        self.gridLayout_recon.addLayout(self.horizontalLayout_eTomo_1, 0, 0, 1, 1)

        self.gridLayout_recon.addLayout(self.horizontalLayout_recon, 1, 0, 1, 1)

        self.model = QtGui.QStandardItemModel(self)

        self.tableView = QtWidgets.QTableWidget(self)
        
        header_labels = metadata.header_labels_recon
        
        self.tableView.setColumnCount(len(header_labels))
        self.tableView.setHorizontalHeaderLabels(header_labels)
        header = self.tableView.horizontalHeader()   
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        
        self.gridLayout_recon.addWidget(self.tableView, 2, 0)
        
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
        self.horizontalLayout_6.setContentsMargins(10, 1, 10, 1)
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
        self.horizontalLayout_7.setContentsMargins(10, 1, 10, 1)
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

        self.label_process_odd_evn_aretomo = QtWidgets.QLabel(self.tab_aretomo)
        self.label_process_odd_evn_aretomo.setSizePolicy(sizePolicy)
        self.label_process_odd_evn_aretomo.setMinimumSize(QtCore.QSize(120, 0))
        self.label_process_odd_evn_aretomo.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_process_odd_evn_aretomo.setObjectName("label_process_odd_evn_aretomo")
        self.horizontalLayout_7.addWidget(self.label_process_odd_evn_aretomo)
        self.comboBox_process_odd_evn_aretomo = QtWidgets.QComboBox(self.tab_aretomo)
        self.comboBox_process_odd_evn_aretomo.setObjectName("comboBox_process_odd_evn_aretomo")
        self.comboBox_process_odd_evn_aretomo.addItem("")
        self.comboBox_process_odd_evn_aretomo.addItem("")
        self.comboBox_process_odd_evn_aretomo.setMaximumWidth(60)
        self.horizontalLayout_7.addWidget(self.comboBox_process_odd_evn_aretomo)      

        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setContentsMargins(10, 1, 10, 1)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        
        self.label_PixelSize_aretomo = QtWidgets.QLabel(self.tab_aretomo)
        self.label_PixelSize_aretomo.setSizePolicy(sizePolicy)
        self.label_PixelSize_aretomo.setMinimumSize(QtCore.QSize(70, 0))
        self.label_PixelSize_aretomo.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_PixelSize_aretomo.setObjectName("label_PixelSize_aretomo")
        self.horizontalLayout_8.addWidget(self.label_PixelSize_aretomo)
        
        self.lineEdit_PixelSize_aretomo = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_PixelSize_aretomo.setInputMask("")
        #self.lineEdit_PixelSize_aretomo.setMinimumSize(QtCore.QSize(160, 0))
        self.lineEdit_PixelSize_aretomo.setObjectName("lineEdit_PixelSize_aretomo")
        self.horizontalLayout_8.addWidget(self.lineEdit_PixelSize_aretomo)

        self.label_OutImod = QtWidgets.QLabel(self.tab_aretomo)
        self.label_OutImod.setSizePolicy(sizePolicy)
        self.label_OutImod.setMinimumSize(QtCore.QSize(80, 0))
        self.label_OutImod.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_OutImod.setObjectName("label_OutImod")
        self.horizontalLayout_8.addWidget(self.label_OutImod)
        
        self.lineEdit_OutImod = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_OutImod.setInputMask("")
        #self.lineEdit_OutImod.setMinimumSize(QtCore.QSize(160, 0))
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
        self.label_UseAlnFile.setMinimumSize(QtCore.QSize(90, 0))
        self.label_UseAlnFile.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_UseAlnFile.setObjectName("label_UseAlnFile")
        self.horizontalLayout_8.addWidget(self.label_UseAlnFile)
        
        self.lineEdit_UseAlnFile = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_UseAlnFile.setInputMask("")
        self.lineEdit_UseAlnFile.setObjectName("lineEdit_UseAlnFile")
        self.horizontalLayout_8.addWidget(self.lineEdit_UseAlnFile)  

        self.label_GPU_ID = QtWidgets.QLabel(self.tab_aretomo)
        self.label_GPU_ID.setSizePolicy(sizePolicy)
        self.label_GPU_ID.setMinimumSize(QtCore.QSize(70, 0))
        self.label_GPU_ID.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_GPU_ID.setObjectName("label_GPU_ID")
        self.horizontalLayout_8.addWidget(self.label_GPU_ID)
        
        self.lineEdit_GPU_ID = QtWidgets.QLineEdit(self.tab_aretomo)
        self.lineEdit_GPU_ID.setInputMask("")
        self.lineEdit_GPU_ID.setObjectName("lineEdit_GPU_ID")
        self.horizontalLayout_8.addWidget(self.lineEdit_GPU_ID) 
        
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setContentsMargins(10, 1, 10, 1)
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
        self.lineEdit_tomo_index.setMaximumSize(QtCore.QSize(80, 30))
        self.lineEdit_tomo_index.setObjectName("lineEdit_tomo_index")
        self.horizontalLayout_9.addWidget(self.lineEdit_tomo_index)

        self.label_correct_ImodFile_format = QtWidgets.QLabel(self.tab_aretomo)
        self.label_correct_ImodFile_format.setSizePolicy(sizePolicy)
        self.label_correct_ImodFile_format.setMinimumSize(QtCore.QSize(120, 0))
        self.label_correct_ImodFile_format.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_correct_ImodFile_format.setObjectName("label_correct_ImodFile_format")
        self.horizontalLayout_9.addWidget(self.label_correct_ImodFile_format)
        self.comboBox_correct_ImodFile_format = QtWidgets.QComboBox(self.tab_aretomo)
        self.comboBox_correct_ImodFile_format.setObjectName("comboBox_correct_ImodFile_format")
        self.comboBox_correct_ImodFile_format.addItem("")
        self.comboBox_correct_ImodFile_format.addItem("")
        self.comboBox_correct_ImodFile_format.setMaximumWidth(60)
        self.horizontalLayout_9.addWidget(self.comboBox_correct_ImodFile_format) 

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
        self.pushButton_run_aretomo.setMinimumSize(QtCore.QSize(72, 36))
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

        self.horizontalLayout_header_aretomo = QtWidgets.QHBoxLayout()
        self.horizontalLayout_header_aretomo.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_header_aretomo.setObjectName("horizontalLayout_header_aretomo")

        self.label_summary_aretomo = QtWidgets.QLabel(self.tab_aretomo)
        self.label_summary_aretomo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_summary_aretomo.setAlignment(QtCore.Qt.AlignCenter)
        self.label_summary_aretomo.setObjectName("label_summary_aretomo")
        self.label_summary_aretomo.setText("Summary of AreTomo 3D Reconstructions")
        self.horizontalLayout_header_aretomo.addWidget(self.label_summary_aretomo)
        
        self.label_dispaly_range_aretomo = QtWidgets.QLabel(self.tab1)
        self.label_dispaly_range_aretomo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_dispaly_range_aretomo.setAlignment(QtCore.Qt.AlignCenter)
        self.label_dispaly_range_aretomo.setMaximumSize(QtCore.QSize(80, 30))
        self.label_dispaly_range_aretomo.setObjectName("label_dispaly_range_aretomo")
        self.label_dispaly_range_aretomo.setText("Displaying")
        self.horizontalLayout_header_aretomo.addWidget(self.label_dispaly_range_aretomo)

        self.comboBox_display_range_aretomo = QtWidgets.QComboBox(self.tab1)
        self.comboBox_display_range_aretomo.setObjectName("comboBox_display_range_aretomo")
        self.comboBox_display_range_aretomo.setMaximumSize(QtCore.QSize(85, 30))
        # self.comboBox_display_range_aretomo.addItem("")
        # self.comboBox_display_range_aretomo.addItem("")
        self.horizontalLayout_header_aretomo.addWidget(self.comboBox_display_range_aretomo)

        self.pushButton_export_recon_aretomo = QtWidgets.QPushButton(self.tab_aretomo)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.pushButton_export_recon_aretomo.setSizePolicy(sizePolicy)
        self.pushButton_export_recon_aretomo.setMinimumSize(QtCore.QSize(50, 20))
        self.pushButton_export_recon_aretomo.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_export_recon_aretomo.setObjectName("pushButton_export_recon_aretomo")
        self.horizontalLayout_header_aretomo.addWidget(self.pushButton_export_recon_aretomo)
        self.gridLayout_3.addLayout(self.horizontalLayout_header_aretomo, 5, 0, 1, 1)
        
        self.tableView_aretomo = QtWidgets.QTableWidget(self)
        
        header_labels_aretomo = metadata.header_labels_aretomo
        
        self.tableView_aretomo.setColumnCount(len(header_labels_aretomo))
        self.tableView_aretomo.setHorizontalHeaderLabels(header_labels_aretomo)
        
        header_aretomo = self.tableView_aretomo.horizontalHeader()   
        header_aretomo.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView_aretomo.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        
        self.gridLayout_3.addWidget(self.tableView_aretomo, 6, 0)

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
        
        self.label_process_odd_evn.setText(_translate("Form", "Generate ODD and EVN Tilt Series?:"))
        self.comboBox_process_odd_evn.setItemText(0, _translate("Form", "No"))
        self.comboBox_process_odd_evn.setItemText(1, _translate("Form", "Yes"))
        self.comboBox_process_odd_evn.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Select Yes to generate tilt series for ODD and EVN sums of Motion Correction frames.\
            This requires subfolders ODD_sums and EVN_sums with the corresponding files existing under the user provided Motion Corrected Images Folder.\
            Default: No.\
            </span></p></body></html>"))
        
        self.pushButton_run_ts_generation.setText(_translate("Form", "RUN"))
        
        self.setTabText(self.indexOf(self.tab), _translate("Form", "TS Generation"))

        self.label_etomo_input_folder.setText(_translate("Form", "Tilt Series Folder:"))
        self.lineEdit_etomo_input_folder.setPlaceholderText(_translate("Form", "Recon/ts_tlt"))
        self.lineEdit_etomo_input_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Folder path to your tilt series and tlt files. \
            </span></p></body></html>"))
        self.label_etomo_tomoNum_detect.setText(_translate("Form", "< 0 Tomo(s) >"))
        
        self.setTabText(self.indexOf(self.tab1), _translate("Form", "eTomo Reconstruction"))

        self.pushButton_export_recon_etomo.setText(_translate("Form", "Export Reconstructions"))

    def retranslateUi_aretomo(self):
        _translate = QtCore.QCoreApplication.translate
        self.setTabText(self.indexOf(self.tab_aretomo), _translate("Form", "AreTomo Reconstruction"))

        self.label_aretomo_input_folder.setText(_translate("Form", "Tilt Series Folder:"))
        self.lineEdit_aretomo_input_folder.setPlaceholderText(_translate("Form", "Recon/ts_tlt"))
        self.lineEdit_aretomo_input_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Folder path to your tilt series (*.st) and rawtlt files (*.rawtlt). \
            </span></p></body></html>"))
        self.label_aretomo_tomoNum_detect.setText(_translate("Form", "< 0 Tomo(s) >"))
        
        self.label_VolZ.setText(_translate("Form", "-VolZ:"))
        self.lineEdit_VolZ.setPlaceholderText(_translate("Form", "2000"))
        self.lineEdit_VolZ.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Volume height or the Z dimension to unbinned voxels. Default: 2000. \
            </span></p></body></html>"))
        
        self.label_OutBin.setText(_translate("Form", "-OutBin:"))
        self.lineEdit_OutBin.setPlaceholderText(_translate("Form", "4"))
        self.lineEdit_OutBin.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Binning of final output reconstruction map. Default: 4. \
            </span></p></body></html>"))
        
        self.label_TiltAxis.setText(_translate("Form", "-TiltAxis:"))
        self.lineEdit_TiltAxis.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_TiltAxis.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Tilt axis is relative to the Y-axis (vertical axis of tilt image) and rotates counter-clockwise. Default: 0.\
            </span></p></body></html>"))
        
        self.label_process_odd_evn_aretomo.setText(_translate("Form", "Generate ODD and EVN Recons?:"))
        self.comboBox_process_odd_evn_aretomo.setItemText(0, _translate("Form", "No"))
        self.comboBox_process_odd_evn_aretomo.setItemText(1, _translate("Form", "Yes"))
        self.comboBox_process_odd_evn_aretomo.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Select Yes to generate 3D Reconstructions for ODD and EVN tilt series if detected under sub-folder ODD and EVN.\
            Default: No.\
            </span></p></body></html>"))
        
        self.label_PixelSize_aretomo.setText(_translate("Form", "-PixSize:"))
        self.lineEdit_PixelSize_aretomo.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_PixelSize_aretomo.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            The pixel size of the input TS. If not provied, the value in the image header will be used.\
            </span></p></body></html>"))
        
        self.label_OutImod.setText(_translate("Form", "-OutImod:"))
        self.lineEdit_OutImod.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_OutImod.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            0: Disabled; 1: for Relion4; 2: Warp; 3: Global- and local-aligned tilt series. Default: 1.\
            </span></p></body></html>"))
        
        self.label_FlipVol.setText(_translate("Form", "-FlipVol:"))
        self.lineEdit_FlipVol.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_FlipVol.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            By default, the x-z slices of the reconstructed volume are saved according to their y coordinates\
            in the output MRC file. -FlipVol 1 saves x-y slices instead according to their z coordinates. Default: 1.\
            </span></p></body></html>"))
        
        self.label_UseAlnFile.setText(_translate("Form", "-UseAlnFile?"))
        self.lineEdit_UseAlnFile.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_UseAlnFile.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Should users decide to reconstruct the volume with a different setting, \
            the corresponding aln file can be loaded by means of -AlnFile to bypass the lengthy alignment process. \
            1: use Aln file if found, 0: redo the alignment. Default: 0.\
            </span></p></body></html>"))
        
        self.label_GPU_ID.setText(_translate("Form", "GPUs ID:"))
        self.lineEdit_GPU_ID.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_GPU_ID.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Use format like '0,1,2,3' to use multiple GPUs for parallel processing. Default: 0\
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
            font-size:9pt;\">Select which tomograms to perform AreTomo operation.\
            </span></p></body></html>"))
        self.lineEdit_tomo_index.setPlaceholderText(_translate("Form", "1-5,7-8,12"))
        self.lineEdit_tomo_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"font-size:9pt;\"> Different tomo indexes are seperated by comma (','); Sequential indexes are connected by hyphen ('-'). \
            </span></p></body></html>"))
        
        self.label_correct_ImodFile_format.setText(_translate("Form", "Correct Imod File Format?:"))
        self.comboBox_correct_ImodFile_format.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_correct_ImodFile_format.setItemText(1, _translate("Form", "No"))
        self.comboBox_correct_ImodFile_format.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            The Version 1.3.4 Aretomo has Imod file formating issue when use -OutImod 1, and may cause improper data processing when exported to Relion4.\
            Set this to Yes to accommodate the following 3 issues. 1. '.tlt' file has a extra empty line \
                2. In tilt.com file, if exclude view, the view's index starts from 0, but should be 1 in Imod convention.\
                3. In tilt.com file, when the images been rotate ~90 degree (related -TiltAxis), the X, Y dimensions are not consistent with the recomstruction generated.\
                If you found these issues been addressed in the newer versions, please set it to No.\
            Default: Yes.\
            </span></p></body></html>"))
        
        self.pushButton_run_aretomo.setText(_translate("Form", "RUN"))
        self.pushButton_export_recon_aretomo.setText(_translate("Form", "Export Reconstructions"))

    def generate_ts(self):
        if self.pushButton_run_ts_generation.text() == "RUN":
            if which('newstack') is None:
                self.logger.error("'newstack' cmd is not detected in the current system. Please check the 'newstack' or IMOD installation!")
                return -1
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

                tomo_lists_tmp = []
                for x in tomo_lists:
                    count_tmp = len(x)
                    if count_tmp > 0:
                        try:
                            tomo_tmp = sorted(x, key = lambda y: float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort]))
                            tomo_lists_tmp.append(tomo_tmp)
                        #tomo_lists = [sorted(x, key = lambda y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) for x in tomo_lists]
                        except:
                            
                            self.logger.warning("It looks like the Tilt Info Index ({}) is not correct for {}. Skiped {} images.".\
                                            format(key_index_sort+1, x[0], count_tmp))
                tomo_lists = tomo_lists_tmp

                try:
                    # tomo_lists = [sorted(x, key = lambda \
                    #             y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) \
                    #             for x in tomo_lists]
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

                generate_odd_even = self.comboBox_process_odd_evn.currentText()
                if generate_odd_even == "No":
                    generate_odd_even = 0
                else:
                    generate_odd_even = 1
                
                if only_process_unfinished == 1:
                    try:
                        #current_ts_list = sorted([os.path.basename(x) for x in glob.glob("{}/*.st".format(self.default_ts_folder))])
                        if os.path.exists(self._history_record):
                            with open(self._history_record, 'r') as f:
                                lines = f.readlines()
                                current_ts_list = []
                                for line in lines:
                                    seg = line.strip().split("->")
                                    if len(seg) == 2:
                                        current_ts_list.append(seg[-1])
                                if len(current_ts_list) > 0:
                                    indexes = [int(os.path.splitext(x)[0].split("_")[-1]) for x in current_ts_list]
                                    indexes = [int(x.split("_")[-1]) for x in current_ts_list]
                                    indexes.sort()
                                    last_index = indexes[-1]
                                    start_index = int(last_index) + 1
                                else:
                                    start_index = 1
                        else:
                            start_index = 1
                    except Exception as err:
                        self.logger.error("Failed reading the Recon/ts_tlt folder!")
                        self.logger.error(f"Unexpected {err=}, {type(err)=}")
                        self.cmd_finished()
                        return -1
                else:
                    start_index = 1

                self.logger.info("########Total TS # detected is {} from {} tilt images, the minimum number of tilts used is {}. Index starts from {}.########".format(len(tomo_lists), len(images_list), min_num_tilt, start_index))
                self.logger.info("########The generated tilt series will be saved under {}/.########".format(self.default_ts_folder))

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
                        key_index, self.default_ts_folder, cpus, flip_axis, only_process_unfinished, generate_odd_even)
                else:
                    self.thread_gt = Generate_TS(image_folder, tomo_lists,\
                        rawtlt_lists, target_base_name, start_index, delimiter,\
                        key_index, self.default_ts_folder, cpus, flip_axis, only_process_unfinished, generate_odd_even)

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
            data['process_odd_evn'] = "No"
            data['etomo_input_folder'] = ""

            #tab 3rd
            data['aretomo_input_folder'] = ""
            data['VolZ'] = ""
            data['OutBin'] = ""
            data['TiltAxis'] = ""
            data['process_odd_evn_aretomo'] = "No"
            data['PixelSize_aretomo'] = ""
            data['OutImod'] = ""
            data['FlipVol'] = ""
            data['UseAlnFile'] = ""
            data['GPU_ID'] = ""
            data['aretomo_addtional_param'] = ""
            data['lineEdit_tomo_index'] = ""
            data['correct_ImodFile_format'] = "Yes"
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
                self.comboBox_process_odd_evn.setCurrentText(data['process_odd_evn'])
                self.lineEdit_etomo_input_folder.setText(data['etomo_input_folder'])

                #tab 3rd
                self.lineEdit_aretomo_input_folder.setText(data['aretomo_input_folder'])
                self.lineEdit_VolZ.setText(data['VolZ'])
                self.lineEdit_OutBin.setText(data['OutBin'])
                self.lineEdit_TiltAxis.setText(data['TiltAxis'])
                self.comboBox_process_odd_evn_aretomo.setCurrentText(data['process_odd_evn_aretomo'])
                self.lineEdit_PixelSize_aretomo.setText(data['PixelSize_aretomo'])
                self.lineEdit_OutImod.setText(data['OutImod'])
                self.lineEdit_FlipVol.setText(data['FlipVol'])
                self.lineEdit_UseAlnFile.setText(data['UseAlnFile'])
                self.lineEdit_GPU_ID.setText(data['GPU_ID'])
                self.lineEdit_aretomo_addtional_param.setText(data['aretomo_addtional_param'])
                self.lineEdit_tomo_index.setText(data['lineEdit_tomo_index'])
                self.comboBox_correct_ImodFile_format.setCurrentText(data['correct_ImodFile_format'])
                
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
        param['process_odd_evn'] = self.comboBox_process_odd_evn.currentText()
        param['etomo_input_folder'] = self.lineEdit_etomo_input_folder.text()

        #tab aretomo
        param['aretomo_input_folder'] = self.lineEdit_aretomo_input_folder.text()
        param['VolZ'] = self.lineEdit_VolZ.text()
        param['OutBin'] = self.lineEdit_OutBin.text()
        param['TiltAxis'] = self.lineEdit_TiltAxis.text()
        param['process_odd_evn_aretomo'] = self.comboBox_process_odd_evn_aretomo.currentText()
        param['PixelSize_aretomo'] = self.lineEdit_PixelSize_aretomo.text()
        param['OutImod'] = self.lineEdit_OutImod.text()
        param['FlipVol'] = self.lineEdit_FlipVol.text()
        param['UseAlnFile'] = self.lineEdit_UseAlnFile.text()
        param['GPU_ID'] = self.lineEdit_GPU_ID.text()
        param['aretomo_addtional_param'] = self.lineEdit_aretomo_addtional_param.text()
        param['lineEdit_tomo_index'] = self.lineEdit_tomo_index.text()
        param['correct_ImodFile_format'] = self.comboBox_correct_ImodFile_format.currentText()
        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            pass

    def tab_changed(self, i):
        if i == 1:
            self.init_range_comboBox_etomo()
            self.reload_table()
            self.etomo_count_tomo()
        if i == 2:
            self.init_range_comboBox_aretomo()
            self.reload_table_aretomo()
            self.aretomo_count_tomo()

    def natural_keys(self, text):
        return int(text.split("_")[-1]) 

    def read_tomo(self, folder_path):
        tomoNames1 = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*.st".format(folder_path)))]
        tomoNames2 = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*.rawtlt".format(folder_path)))]

        tomoNames = sorted(list(set(tomoNames1) & set(tomoNames2)))
        try:
            tomoNames.sort(key=self.natural_keys)
        except:
            pass

        return tomoNames

    def table_click(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.tableView.item(i, 0).text()
        if j == self.etomo_preview_loc:
            current_st_link_path = "{}/{}.st".format(self.etomo_ts_folder, tomoName)
            cmd = "3dmod -b 8,1 {}".format(current_st_link_path)
            os.system(cmd)
        elif j == self.etomo_continue_loc:
            if which('etomo') is None:
                self.logger.error("'etomo' cmd is not detected in the current system. Please check the 'etomo' installation!")
                return -1
            current_tomo_folder = "{}/{}".format(self.etomo_folder, tomoName)
            if not os.path.exists(current_tomo_folder):
                os.makedirs(current_tomo_folder)
            
            edfName = "{}/{}.edf".format(current_tomo_folder, tomoName)
            #current_st_path = "{}/{}.st".format(current_tomo_folder, tomoName)
            if not os.path.exists(edfName):
                current_st_link_path = "{}/{}.st".format(self.etomo_ts_folder, tomoName)
                current_rawtlt_link_path = "{}/{}.rawtlt".format(self.etomo_ts_folder, tomoName)
                
                linked_st_path = "{}/{}.st".format(current_tomo_folder, tomoName)
                linked_rawtlt_path = "{}/{}.rawtlt".format(current_tomo_folder, tomoName)
                try:
                    os.remove(linked_st_path)
                    os.remove(linked_rawtlt_path)
                except:
                    pass
                if self.etomo_ts_folder == self.default_ts_folder:
                    cmd = "cd {} ; ln -s ../../../{} ./ ; ln -s ../../../{} ./ ; etomo".format(current_tomo_folder, current_st_link_path, current_rawtlt_link_path)
                else:
                    cmd = "cd {} ; ln -s {} ./ ; ln -s {} ./; etomo".format(current_tomo_folder, current_st_link_path, current_rawtlt_link_path)
                subprocess.check_output(cmd, shell=True)
            # elif not os.path.exists(edfName):
            #     linked_st_path = "{}/{}.st".format(current_tomo_folder, tomoName)
            #     linked_rawtlt_path = "{}/{}.rawtlt".format(current_tomo_folder, tomoName)
            #     try:
            #         os.remove(linked_st_path)
            #         os.remove(linked_rawtlt_path)
            #     except:
            #         pass
            #     cmd = "cd {}; etomo".format(current_tomo_folder)
            #     subprocess.check_output(cmd, shell=True)
            else:
                cmd = "cd {}; etomo *edf".format(current_tomo_folder)
                subprocess.check_output(cmd, shell=True)
        elif j == self.etomo_startover_loc:
            if which('etomo') is None:
                self.logger.error("'etomo' cmd is not detected in the current system. Please check the 'etomo' installation!")
                return -1
            ret = QMessageBox.question(self, 'Risky Action!', "Do you want to star over for {}? All progresses will be reset.".format(tomoName), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret == QMessageBox.Yes:
                current_tomo_folder = "{}/{}".format(self.etomo_folder, tomoName)
                mkfolder(current_tomo_folder)

                current_st_link_path = "{}/{}.st".format(self.etomo_ts_folder,tomoName)
                current_rawtlt_link_path = "{}/{}.rawtlt".format(self.etomo_ts_folder,tomoName)
                
                if self.etomo_ts_folder == self.default_ts_folder:
                    cmd = "cd {} ; ln -s ../../../{} ./ ; ln -s ../../../{} ./ ; etomo".format(current_tomo_folder, current_st_link_path, current_rawtlt_link_path)
                else:
                    cmd = "cd {} ; ln -s {} ./ ; ln -s {} ./; etomo".format(current_tomo_folder, current_st_link_path, current_rawtlt_link_path)
                subprocess.check_output(cmd, shell=True)
                self.reload_table()
        elif j == self.etomo_delete_loc:
            ret = QMessageBox.question(self, 'Risky Action!', "Do you want to move {} to trash?".format(tomoName), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret == QMessageBox.Yes:
                trash_ts_tlt = "{}/{}".format(self.etomo_ts_folder, "Trash")
                trash_ts_etomo = "{}/{}".format(self.etomo_folder, "Trash")
                if not os.path.exists(trash_ts_tlt):
                    os.makedirs(trash_ts_tlt)
                if not os.path.exists(trash_ts_etomo):
                    os.makedirs(trash_ts_etomo)
                ts_path = "{}/{}.st".format(self.etomo_ts_folder, tomoName)
                tlt_path = "{}/{}.rawtlt".format(self.etomo_ts_folder, tomoName)
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
        elif j == self.etomo_oddevn_loc:
            self.logger.warning("This function is disabled before issues get fixed. Please use newst.com and tilt.com to generate ODD and EVN reconstructions manually. Or using Aretomo option.")
            # if which('newstack') is None:
            #     self.logger.error("'newstack' cmd is not detected in the current system. Please check the 'newstack' or IMOD installation!")
            #     return -1
            # if which('tilt') is None:
            #     self.logger.error("'tilt' cmd is not detected in the current system. Please check the 'tilt' or IMOD installation!")
            #     return -1
            # if which('clip') is None:
            #     self.logger.error("'clip' cmd is not detected in the current system. Please check the 'clip' or IMOD installation!")
            #     return -1
            # #for generate ODD and EVN
            # current_ODD_st_link_path = "{}/ODD/{}_ODD.st".format(self.etomo_ts_folder, tomoName)
            # current_EVN_st_link_path = "{}/EVN/{}_EVN.st".format(self.etomo_ts_folder, tomoName)
            # current_tomo_folder = "{}/{}".format(self.etomo_folder, tomoName)

            # if self.etomo_ts_folder == self.default_ts_folder:
            #     pwd = os.getcwd()
            #     current_ODD_st_link_path = "{}/{}".format(pwd, current_ODD_st_link_path)
            #     current_EVN_st_link_path = "{}/{}".format(pwd, current_EVN_st_link_path)

            # if os.path.exists(current_ODD_st_link_path) and os.path.exists(current_EVN_st_link_path):
            #     ret = QMessageBox.question(self, 'ODD & EVN', "generate 3D reconstruction for ODD and EVN frames of {}?".format(tomoName), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            #     if ret == QMessageBox.Yes:
            #         result_ODD = self.run_ODD_EVN_Recon(current_ODD_st_link_path, current_tomo_folder, tomoName, "ODD")
            #         if not (result_ODD == 'Success'):
            #             self.logger.error(result_ODD)
            #             return
            #         result_EVN = self.run_ODD_EVN_Recon(current_EVN_st_link_path, current_tomo_folder, tomoName, "EVN")
            #         if not (result_EVN == 'Success'):
            #             self.logger.error(result_EVN)
            #             return
            #         if result_ODD == 'Success' and result_EVN == 'Success':
            #             self.logger.info("ODD & EVN Recons were performed for {}".format(tomoName))
            # else:
            #     self.logger.warning('either ODD ({}) or EVN ({}) TS file was not detected!'.format(current_ODD_st_link_path, current_EVN_st_link_path))
        elif j == self.etomo_recon_loc:
            if which('3dmod') is None:
                self.logger.error("'3dmod' cmd is not detected in the current system. Please check the '3dmod' or IMOD installation!")
                return -1
            if self.tableView.item(i, j).text().strip() == "NA":
                pass
            else:
                tomoName = self.tableView.item(i, 0).text()
                rec_path = self.read_recon_folder(tomoName, self.etomo_folder, 1)[6]
                cmd = "3dmod {}".format(rec_path)
                os.system(cmd)
                #subprocess.check_output(cmd, shell=True)
        elif j == self.etomo_notes_loc:
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
        if j == self.aretomo_preview_loc:
            if which('3dmod') is None:
                self.logger.error("'3dmod' cmd is not detected in the current system. Please check the '3dmod' or IMOD installation!")
                return -1
            current_st_link_path = "{}/{}.st".format(self.aretomo_ts_folder, tomoName)
            cmd = "3dmod -b 8,1 {}".format(current_st_link_path)
            os.system(cmd)
        elif j == self.aretomo_recon_loc:
            if which('3dmod') is None:
                self.logger.error("'3dmod' cmd is not detected in the current system. Please check the '3dmod' or IMOD installation!")
                return -1
            try:
                if self.tableView_aretomo.item(i, j).text().strip() == "NA":
                    pass
                else:
                    tomoName = self.tableView_aretomo.item(i, 0).text()
                    rec_path = self.read_recon_folder(tomoName, self.areTomo_folder, 2)[6]
                    cmd = "3dmod {}".format(rec_path)
                    os.system(cmd)
            except:
                pass
        elif j == self.aretomo_notes_loc:
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
        index = self.etomo_notes_loc if code == 1 else self.aretomo_notes_loc
        for i in range(row_count):
            params[tableView.item(i, 0).text()] = tableView.item(i, index).text()
        return params

    def read_recon_folder(self, tomoName, rec_root, tab_index=1):

        tilt_num, re_mean, re_range, binning, thickness_nm, skipped_view = ["", "", "", "", "", ""]
        recon_path = "{}/{}".format(rec_root, tomoName)

        tiltcom_path = "{}/{}".format(recon_path, "tilt.com")
        #st_path = "{}/{}.st".format(recon_path, tomoName)
        # if tab_index == 1:
        #     st_path = "{}/{}.st".format(self.etomo_ts_folder, tomoName)
        # elif tab_index == 2:
        #     st_path = "{}/{}.st".format(self.aretomo_ts_folder, tomoName)
        # else:
        #     st_path = "{}/{}.st".format(self.etomo_ts_folder, tomoName)
        rec_path = "{}/{}.rec".format(recon_path, tomoName)
        mrc_path = "{}/{}_rec.mrc".format(recon_path, tomoName)
        tlt_path = "{}/{}.tlt".format(recon_path, tomoName)
        newst_path = "{}/newst.com".format(recon_path, tomoName)

        final_rec_path = ""
        import time
        t1 = time.time()
        if os.path.exists(rec_path) or os.path.exists(mrc_path):
            try:                
                # d_st = self.read_header(st_path)
                # if os.path.exists(rec_path):
                #     d_rec = self.read_header(rec_path)
                #     final_rec_path = rec_path
                # else:
                #     d_rec = self.read_header(mrc_path)
                #     final_rec_path = mrc_path
                
                #tilt_num = str(d_st["sections"])

                # binning = str(int(np.round(d_rec["apix"]/d_st["apix"], 0)))

                # thickness_nm = str(int(d_rec["sections"] * d_rec["apix"]))
                # t2 = time.time()
                # print('t2 time consumed: {:10.4f} s'.format(t2-t1))

                try:
                    with open(tlt_path, 'r') as f:
                        lines_tlt = f.readlines()
                    tilt_num = str(len(lines_tlt))
                except:
                    tilt_num = "None"
                
                
                taError_path = "{}/{}".format(recon_path, "taError.log")
                
                if os.path.exists(newst_path):
                    with open(newst_path, 'r') as f:
                        lines = f.readlines()
                    out_line = ""
                    for line in lines:
                        if "BinByFactor" in line:
                            out_line = line
                            break
                    
                    if out_line:
                        binning = out_line.strip().split()[-1]
                    else:
                        binning = "None"

                #thickness_nm = str(int(d_rec["sections"] * d_rec["apix"]))
                
                if os.path.exists(taError_path):
                    try:
                        
                        # cmd = "cat {} | grep \"{}\"".format(taError_path, "Residual error local mean")
                        # out = subprocess.check_output(cmd, shell=True)
                        # line = out.decode('utf-8').split("\n")[0]
                        # re_mean = line.strip().split()[4]
                        # re_range = "{} - {}".format(line.split()[6],line.split()[8])
                        with open(taError_path, 'r') as f:
                            lines = f.readlines()
                        out_line = ""
                        for line in lines:
                            if "Residual error local mean" in line:
                                out_line = line
                                break
                        try:
                            re_mean = out_line.strip().split()[4]
                            re_range = "{} - {}".format(out_line.split()[6],out_line.split()[8])
                        except:
                            re_mean = "None"
                            re_range = "None"
                    except:
                        self.logger.warning("cannot reading RE mean error !")
                # t3 = time.time()
                # print('t3 time consumed: {:10.4f} s'.format(t3-t2))
                with open(tiltcom_path) as f:
                    skipped_view = ''
                    skipped_view2 = ''
                    for line in f:
                        if "EXCLUDELIST2" in line:
                            skipped_view2 = line.split('EXCLUDELIST2')[-1].strip().replace(' ','')
                        elif "EXCLUDELIST" in line:
                            skipped_view = line.split('EXCLUDELIST')[-1].strip().replace(' ','')
                    skipped_view = skipped_view2 if len(skipped_view2) > len(skipped_view) else skipped_view
                # t4 = time.time()
                # print('t4 time consumed: {:10.4f} s'.format(t4-t3))
            except:
                pass                                
        return [tilt_num, re_mean, re_range, binning, thickness_nm, skipped_view, final_rec_path]
    
    # def read_header(self, file_path):
    #     d = {}
    #     d['apix'] = 1.0
    #     cmd = "header {} ".format(file_path)
    #     out = subprocess.check_output(cmd, shell=True)
    #     lines = out.decode('utf-8').split("\n")
    #     for line in lines:
    #         if "Pixel spacing" in line:
    #             apix = line.strip().split()[-1]
    #             d['apix'] = float(apix)
    #         if "Number of columns" in line:
    #             sections = line.strip().split()[-1]
    #             d['sections'] = int(sections)  
    #     return d
    
    def init_range_comboBox_etomo(self):
        
        tomoNames = self.read_tomo(self.etomo_ts_folder)
        
        self.tomoNames_etomo = tomoNames
        total_number = len(tomoNames)
        self.total_tomo_num_etomo = total_number
        range_num = total_number // self.table_display_interval_etomo
        range_mod = total_number % self.table_display_interval_etomo
        
        self.comboBox_display_range_etomo.currentIndexChanged.disconnect(self.range_changed_etomo)
        
        self.comboBox_display_range_etomo.clear()
        for i in range(range_num):
            self.comboBox_display_range_etomo.addItem("")
            self.comboBox_display_range_etomo.setItemText(i, "[{}, {}]".format(self.table_display_interval_etomo*i+1, self.table_display_interval_etomo*(i+1)))
        if range_mod > 0:
            self.comboBox_display_range_etomo.addItem("")
            self.comboBox_display_range_etomo.setItemText(range_num, "[{}, {}]".format(self.table_display_interval_etomo*range_num+1, total_number))

        self.comboBox_display_range_etomo.currentIndexChanged.connect(self.range_changed_etomo)
        #self.range_changed_etomo()
        current_range = self.comboBox_display_range_etomo.currentText()
        if current_range:
            #print(current_range)
            min_i, max_i = current_range[1:-1].split(",")
            self.table_display_range_etomo = [int(min_i), int(max_i)]
    
    def range_changed_etomo(self):
        current_range = self.comboBox_display_range_etomo.currentText()
        if current_range:
            #print(current_range)
            min_i, max_i = current_range[1:-1].split(",")
            self.table_display_range_etomo = [int(min_i), int(max_i)]
        self.reload_table()
    
    def reload_table(self):
        #tomoNames = self.read_tomo(self.etomo_ts_folder)
        tomoNames = self.tomoNames_etomo
        self.tableView.setRowCount(0)
        #self.tableView.setRowCount(len(tomoNames))
        
        try:
            with open(self.note_json) as f:
                note_dict = json.load(f)
        except:
            note_dict = {}
        if len(tomoNames) > 0:
            self.tableView.setRowCount(self.table_display_range_etomo[1] - self.table_display_range_etomo[0] + 1)
            display_i = 0
            self.tableView.setVerticalHeaderLabels([str(x) for x in np.arange(self.table_display_range_etomo[0], self.table_display_range_etomo[1] + 1, dtype=int)])
            
            for i, tomo in enumerate(tomoNames):
                if i+1 >= self.table_display_range_etomo[0] and i < self.table_display_range_etomo[1]:
                    self.tableView.setItem(display_i, 0, QTableWidgetItem(tomo))                
                    action_check = QTableWidgetItem("View TS (Bin8)")
                    action_check.setBackground(QtGui.QColor("#a0d2eb"))
                    action_check.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(display_i, 1, action_check)
                    
                    action_continue = QTableWidgetItem("Continue")
                    action_continue.setBackground(QtGui.QColor("#4CAF50"))
                    action_continue.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(display_i, 2, action_continue)

                    action_starover = QTableWidgetItem("Start Over")
                    action_starover.setBackground(QtGui.QColor("#008CBA"))
                    action_starover.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(display_i, 3, action_starover)

                    action_delete = QTableWidgetItem("Delete")
                    action_delete.setBackground(QtGui.QColor("#f44336"))
                    action_delete.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(display_i, 4, action_delete)

                    action_ODD_EVN = QTableWidgetItem("ODD & EVN")
                    action_ODD_EVN.setBackground(QtGui.QColor("#ffb7b2"))
                    action_ODD_EVN.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(display_i, 5, action_ODD_EVN)
                    
                    items = self.read_recon_folder(tomo, self.etomo_folder, 1)

                    if len(items[6]) > 0:
                        action_view = QTableWidgetItem(os.path.basename(items[6]))
                    else:
                        action_view = QTableWidgetItem("NA")
                    
                    action_view.setBackground(QtGui.QColor("#d0bdf4"))
                    action_view.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(display_i, 6, action_view)

                    self.tableView.setItem(display_i, 7, QTableWidgetItem(items[0]))
                    self.tableView.setItem(display_i, 8, QTableWidgetItem(items[1]))
                    self.tableView.setItem(display_i, 9, QTableWidgetItem(items[2]))
                    self.tableView.setItem(display_i, 10, QTableWidgetItem(items[3]))
                    # if len(items[4]) > 0:
                    #     self.tableView.setItem(display_i, 11, QTableWidgetItem("{} nm".format(str(int(items[4])/10))))
                    # else:
                    #     self.tableView.setItem(display_i, 11, QTableWidgetItem(""))
                    self.tableView.setItem(display_i, 11, QTableWidgetItem(items[5]))
                    notes_i = note_dict[tomo] if tomo in note_dict.keys() else ""
                    self.tableView.setItem(display_i, 12, QTableWidgetItem(notes_i))

                    display_i+=1

    def init_range_comboBox_aretomo(self):
        
        tomoNames = self.read_tomo(self.aretomo_ts_folder)
        self.tomoNames_aretomo = tomoNames
        total_number = len(tomoNames)
        self.total_tomo_num_aretomo = total_number
        range_num = total_number // self.table_display_interval_aretomo
        range_mod = total_number % self.table_display_interval_aretomo
        
        self.comboBox_display_range_aretomo.currentIndexChanged.disconnect(self.range_changed_aretomo)
        
        self.comboBox_display_range_aretomo.clear()
        for i in range(range_num):
            self.comboBox_display_range_aretomo.addItem("")
            self.comboBox_display_range_aretomo.setItemText(i, "[{}, {}]".format(self.table_display_interval_aretomo*i+1, self.table_display_interval_aretomo*(i+1)))
        if range_mod > 0:
            self.comboBox_display_range_aretomo.addItem("")
            self.comboBox_display_range_aretomo.setItemText(range_num, "[{}, {}]".format(self.table_display_interval_aretomo*range_num+1, total_number))

        #self.range_changed_aretomo()
        current_range = self.comboBox_display_range_aretomo.currentText()
        if current_range:
            #print(current_range)
            min_i, max_i = current_range[1:-1].split(",")
            self.table_display_range_aretomo = [int(min_i), int(max_i)]

        self.comboBox_display_range_aretomo.currentIndexChanged.connect(self.range_changed_aretomo)
    
    def range_changed_aretomo(self):
        current_range = self.comboBox_display_range_aretomo.currentText()
        if current_range:
            #print(current_range)
            min_i, max_i = current_range[1:-1].split(",")
            self.table_display_range_aretomo = [int(min_i), int(max_i)]
        self.reload_table_aretomo()

    def reload_table_aretomo(self):
        self.aretomo_ts_folder = self.lineEdit_aretomo_input_folder.text() if len(self.lineEdit_aretomo_input_folder.text().strip()) > 0 else self.default_ts_folder
        #tomoNames = self.read_tomo(self.aretomo_ts_folder)
        tomoNames = self.tomoNames_aretomo
        self.tableView_aretomo.setRowCount(0)
        #self.tableView_aretomo.setRowCount(len(tomoNames))
        try:
            with open(self.note_json) as f:
                note_dict = json.load(f)
        except:
            note_dict = {}
        if len(tomoNames) > 0:
            self.tableView_aretomo.setRowCount(self.table_display_range_aretomo[1] - self.table_display_range_aretomo[0] + 1)
            display_i = 0
            self.tableView_aretomo.setVerticalHeaderLabels([str(x) for x in np.arange(self.table_display_range_aretomo[0], self.table_display_range_aretomo[1] + 1, dtype=int)])

            # import time
            # t1 = time.time()
            for i, tomo in enumerate(tomoNames):
                if i+1 >= self.table_display_range_aretomo[0] and i < self.table_display_range_aretomo[1]:
                    self.tableView_aretomo.setItem(display_i, 0, QTableWidgetItem(tomo))                
                    action_check = QTableWidgetItem("View TS (Bin8)")
                    action_check.setBackground(QtGui.QColor("#a0d2eb"))
                    action_check.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView_aretomo.setItem(display_i, 1, action_check)
                    
                    items = self.read_recon_folder(tomo, self.areTomo_folder, 2)

                    if len(items[6]) > 0:
                        action_view = QTableWidgetItem(os.path.basename(items[6]))
                    else:
                        action_view = QTableWidgetItem("NA")
                    
                    action_view.setBackground(QtGui.QColor("#d0bdf4"))
                    action_view.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView_aretomo.setItem(display_i, 2, action_view)

                    self.tableView_aretomo.setItem(display_i, 3, QTableWidgetItem(items[0]))
                    self.tableView_aretomo.setItem(display_i, 4, QTableWidgetItem(items[3]))
                    # if len(items[4]) > 0:
                    #     self.tableView_aretomo.setItem(display_i, 5, QTableWidgetItem("{} nm".format(str(int(items[4])/10))))
                    # else:
                    #     self.tableView_aretomo.setItem(display_i, 5, QTableWidgetItem(""))
                    self.tableView_aretomo.setItem(display_i, 5, QTableWidgetItem(items[5]))
                    notes_i = note_dict[tomo] if tomo in note_dict.keys() else ""
                    self.tableView_aretomo.setItem(display_i, 6, QTableWidgetItem(notes_i))

                    display_i+=1

        # t2 = time.time()
        # self.logger.info('time consumed: {:10.4f} s'.format(t2-t1))

        self.current_tomoNames_aretomo = tomoNames
    
    def list_row_changed(self, i):
        if i == 1:
            if self.currentIndex() == 1:
                self.init_range_comboBox_etomo()
                self.reload_table()
                self.etomo_count_tomo()
            if self.currentIndex() == 2:
                self.init_range_comboBox_aretomo()
                self.reload_table_aretomo()
                self.aretomo_count_tomo()
    
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
            self.logger.error("No specified images are detected! Please make sure the images exist and the parameters are correctly set.")
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
        
        tomo_lists_tmp = []
        for x in tomo_lists:
            count_tmp = len(x)
            if count_tmp > 0:
                try:
                    tomo_tmp = sorted(x, key = lambda y: float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort]))
                    tomo_lists_tmp.append(tomo_tmp)
                #tomo_lists = [sorted(x, key = lambda y:float(y.split(image_file_suffix)[0].split(delimiter)[key_index_sort])) for x in tomo_lists]
                except:
                    self.logger.warning("It looks like the Tilt Info Index ({}) is not correct for {}. Skiped {} images.".\
                                    format(key_index_sort+1, x[0], count_tmp))
        tomo_lists = tomo_lists_tmp

        if len(tomo_lists) > 0:
            try:
                rawtlt_lists = [[float(x.split(image_file_suffix)[0].split(delimiter)[key_index_sort]) for x in y] for y in tomo_lists]
            except Exception as err:
                self.logger.error(f"Unexpected {err=}, {type(err)=}")
                return -1
        else:
            self.logger.error("No specified images are detected! Please make sure the images exist and the parameters are correctly set.")
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
                return -1

        tomo_lists = [x for x in tomo_lists if len(x) >= min_num_tilt]
        rawtlt_lists = [x for x in rawtlt_lists if len(x) >= min_num_tilt]    

        self.logger.info("Check result: Total TS # is {} from {} images".format(len(tomo_lists), len(images_list)))

    ############# for AreTomo tab ###########################
    def aretomo_count_tomo(self):
        self.aretomo_ts_folder = self.lineEdit_aretomo_input_folder.text() if len(self.lineEdit_aretomo_input_folder.text().strip()) > 0 else self.default_ts_folder

        if os.path.exists(self.aretomo_ts_folder):
            self.current_ts_list = sorted([os.path.basename(x) for x in glob.glob("{}/*.st".format(self.aretomo_ts_folder))])
            if self.current_ts_list and len(self.current_ts_list) > 0:
                self.label_aretomo_tomoNum_detect.setText("< {} Tomo(s)>".format(len(self.current_ts_list)))
            else:
                self.label_aretomo_tomoNum_detect.setText("< 0 Tomo(s)>")
        else:
            self.label_aretomo_tomoNum_detect.setText("< 0 Tomo(s)>")

    def etomo_count_tomo(self):
        self.etomo_ts_folder = self.lineEdit_etomo_input_folder.text() if len(self.lineEdit_etomo_input_folder.text().strip()) > 0 else self.default_ts_folder

        if os.path.exists(self.etomo_ts_folder):
            self.current_ts_list = sorted([os.path.basename(x) for x in glob.glob("{}/*.st".format(self.etomo_ts_folder))])
            if self.current_ts_list and len(self.current_ts_list) > 0:
                self.label_etomo_tomoNum_detect.setText("< {} Tomo(s)>".format(len(self.current_ts_list)))
            else:
                self.label_etomo_tomoNum_detect.setText("< 0 Tomo(s)>")
        else:
            self.label_etomo_tomoNum_detect.setText("< 0 Tomo(s)>")

    def get_aretomo_param(self):
        params = {}

        if not len(self.lineEdit_aretomo_input_folder.text().strip()) > 0:
            #return "Please specify the tilt series folder as input!"
            aretomo_input_folder = self.default_ts_folder
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

        generate_odd_even_aretomo = self.comboBox_process_odd_evn_aretomo.currentText()
        if generate_odd_even_aretomo == "No":
            generate_odd_even_aretomo = 0
        else:
            generate_odd_even_aretomo = 1    
        
        params['generate_odd_even_aretomo'] = generate_odd_even_aretomo 

        if len(self.lineEdit_PixelSize_aretomo.text()) > 0 :
            pixelSize_aretomo = string2float(self.lineEdit_PixelSize_aretomo.text(), 5)
            if pixelSize_aretomo == None or pixelSize_aretomo < 0:
                return "please use correct format for pixel size (positive real number)!"
        else: 
            pixelSize_aretomo = -1
        
        params['pixelSize_aretomo'] = pixelSize_aretomo 
        
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

        correct_ImodFile_format = self.comboBox_correct_ImodFile_format.currentText()
        if correct_ImodFile_format == "No":
            correct_ImodFile_format = 0
        else:
            correct_ImodFile_format = 1    
        params['correct_ImodFile_format'] = correct_ImodFile_format 
        
        if len(self.lineEdit_tomo_index.text().strip()) > 0:
            try:
                tomo_index = list(set([string2int(x) for x in idx2list(self.lineEdit_tomo_index.text().strip())]))
                
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
            return "No tomo index provided!"

        params['current_ts_list_selected'] = self.current_ts_list_selected
        
        return params
    
    def run_aretomo(self):
        
        d = self.get_aretomo_param()
        
        if (not self.current_ts_list) or len(self.current_ts_list) == 0:
            self.logger.error("No Tomogram has detected yet! Please adjust your tilt series folder!")
        elif type(d) is dict:
            
            if self.pushButton_run_aretomo.text() == "RUN":
                install_well_1 = True
                install_well_2 = True
                if not (which('AreTomo2') is None):
                    d['aretomo_name'] = 'AreTomo2'
                    cmd = '{} --version'.format(d['aretomo_name'])
                    try:
                        result_output = subprocess.check_output(cmd, shell=True).decode()
                        try: 
                            result_output = result_output.split('\n')[0]
                        except:
                            pass

                        self.logger.info("{} detected: {}.\n Note that if you want to use AreTomo instead, you need to disable AreTomo2 first.".format(d['aretomo_name'], result_output))
                    except:
                        self.logger.error("AreTomo2 is detected, but is not working properly.")
                        install_well_2 = False
                elif not (which('AreTomo') is None):
                    d['aretomo_name'] = 'AreTomo'
                    cmd = '{} --version'.format(d['aretomo_name'])
                    try:
                        result_output = subprocess.check_output(cmd, shell=True).decode()
                        try: 
                            result_output = result_output.split('\n')[0]
                        except:
                            pass
                        self.logger.info("{} detected: {}".format(d['aretomo_name'], result_output))
                    except:
                        self.logger.error("AreTomo is detected, but is not working properly.")
                        install_well_1 = False
                else:
                    self.logger.error("Either AreTomo or AreTomo2 is detected, Please check the installation and make sure `which AreTomo` gives right print out.")
                    return -1
                
                if not install_well_1 or not install_well_2:
                    self.logger.error("Either AreTomo or AreTomo2 is well installed, Please check the installation and make sure `which AreTomo` or `which AreTomo2` gives right print out.")
                    return -1
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

    def run_ODD_EVN_Recon(self, path_ts, target_folder, tomoName, type):
        # check if newst.com exist and valid
        newst_com_file = "{}/newst.com".format(target_folder)
        if not os.path.exists(newst_com_file):
            return "{} was not found!".format(newst_com_file)
                
        ODD_EVN_folder_path = "{}/{}".format(target_folder, type)

        output_mrc = "{}/{}_{}_ali.mrc".format(type, tomoName, type)
        newst_cmd = self.get_newst_cmd(newst_com_file, target_folder, tomoName, path_ts, output_mrc)
        
        mkfolder_ifnotexist(ODD_EVN_folder_path)
        # if not newst_cmd == None:
        #     try:
        #         subprocess.check_output(newst_cmd, shell=True)
        #         #subprocess.run(newst_cmd, capture_output=True)
        #     except Exception as err:
        #         self.logger.error(f"Unexpected {err=}, {type(err)=}")
        #         return "Fail"
        
        tilt_com_file = "{}/tilt.com".format(target_folder)
        if not os.path.exists(tilt_com_file):
            return "{} was not found!".format(tilt_com_file)
        
        inputProjection = output_mrc
        output_recon_mrc = "{}/{}_{}_full_rec.mrc".format(type, tomoName, type)
        tilt_cmd = self.get_tilt_cmd(tilt_com_file, target_folder, tomoName, inputProjection, output_recon_mrc)

        # if not (tilt_cmd == None):
        #     try:
        #         subprocess.check_output(tilt_cmd, shell=True)
        #         #subprocess.run(tilt_cmd, capture_output=True)
        #     except Exception as err:
        #         self.logger.error(f"Unexpected {err=}, {type(err)=}")
        #         return "Fail"
        
        output_recon_rotx_mrc = "{}/{}_{}_rec.mrc".format(type, tomoName, type)
        
        edf_file = "{}/{}.edf".format(target_folder, tomoName)
        clip_cmd = 'clip rotx {} {}'.format(output_recon_mrc, output_recon_rotx_mrc)
        if os.path.exists(edf_file):
            with open(edf_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('Setup.Post.Trimvol.RotateX') and 'false' in line.strip().split('=')[-1]:
                        clip_cmd = 'clip flipyz {} {}'.format(output_recon_mrc, output_recon_rotx_mrc)

        ODD_EVN_folder_path_log = "{}/run_recon.log".format(type)
        ODD_EVN_folder_path_cmd = "{}/run_recon.cmd".format(ODD_EVN_folder_path)
        
        combined_cmd = "{} > {} ; {} >> {} ; {} >> {}".format(newst_cmd, ODD_EVN_folder_path_log, tilt_cmd, ODD_EVN_folder_path_log, clip_cmd, ODD_EVN_folder_path_log)
        with open(ODD_EVN_folder_path_cmd, 'w') as w:
            w.write(combined_cmd)
        #self.logger.info(combined_cmd)
        try:
            cmd = 'sh {} &'.format(ODD_EVN_folder_path_cmd)
            #subprocess.check_output(combined_cmd, shell=True)
            #subprocess.run(combined_cmd, shell=True)
            os.system(cmd)
        except Exception as err:
            self.logger.info(err)
            self.logger.error(f"Unexpected {err=}, {type(err)=}")
            return "Fail"
        
        return "Success"

    def get_newst_cmd(self, newst_com_file, target_folder, tomoName, path_ts, output_mrc):
        params_list = metadata.newst_com_params
        inputFile = path_ts
        outputFile = output_mrc
        
        newst_cmd = 'cd {}; newstack -InputFile {} -OutputFile {}'.format(target_folder, inputFile, outputFile)
        try:
            with open(newst_com_file, 'r') as f:
                lines = f.readlines()
        
            for line in lines:
                if (not line.startswith('#')) and (not line.startswith('$')):
                    seg = line.split()
                    if seg[0] in params_list:
                        if len(seg) == 1:
                            newst_cmd = "{} -{}".format(newst_cmd, seg[0])
                        elif len(seg) == 2:
                            newst_cmd = "{} -{} {}".format(newst_cmd, seg[0], seg[1])
                            if seg[1].endswith('.xf'):
                                xf_file = "{}/{}".format(target_folder, seg[1])
                                if not os.path.exists(xf_file):
                                    self.logger.error("Missing alignment file {} for TS {}".format(xf_file, tomoName))
                                    return None
                        else:
                            combine_param = line.split(seg[0])[-1].strip()
                            newst_cmd = "{} -{} '{}'".format(newst_cmd, seg[0], combine_param)
            return newst_cmd
        except:
            return None
    
    def get_tilt_cmd(self, tilt_com_file, target_folder, tomoName, path_align_ts, output_recon_mrc):
        params_list = metadata.tilt_com_params
        inputProjections = path_align_ts
        outputFile = output_recon_mrc
        #tilt_cmd = 'cd {}; tilt -InputProjections {} -OutputFile {}'.format(target_folder, inputProjections, outputFile)
        tilt_cmd = 'tilt -InputProjections {} -OutputFile {}'.format(inputProjections, outputFile)
        try:
            with open(tilt_com_file, 'r') as f:
                lines = f.readlines()
            for line in lines:
                if (not line.startswith('#')) and (not line.startswith('$')):
                    seg = line.split()
                    if seg[0] in params_list:
                        if len(seg) == 1:
                            tilt_cmd = "{} -{}".format(tilt_cmd, seg[0])
                        elif len(seg) == 2:
                            tilt_cmd = "{} -{} {}".format(tilt_cmd, seg[0], seg[1])
                            if seg[1].endswith(('.tlt', '.xf', 'xtilt')):
                                align_file = "{}/{}".format(target_folder, seg[1])
                                if not os.path.exists(align_file):
                                    self.logger.error("Missing alignment file {} for TS {}".format(align_file, tomoName))
                                    return None
                        else:
                            combine_param = line.split(seg[0])[-1].strip()
                            tilt_cmd = "{} -{} '{}'".format(tilt_cmd, seg[0], combine_param)
            return tilt_cmd
        except:
            return None
        
    def export_recons(self, type):
        if type == 'etomo':
            recon_target_folder = self.etomo_recon_folder
            recon_folder = self.etomo_folder
        elif type == 'aretomo':
            recon_target_folder = self.aretomo_recon_folder
            recon_folder = self.areTomo_folder
        else:
            self.logger.error("unexpected input type of reconstruction!")
            return -1
        ret = QMessageBox.question(self, 'Export eTomo Reconstruction', \
                    "Linking all Reconstruction maps to folder {}?".format(recon_target_folder)\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.logger.info("Linking processed reconstructions to folder {}, links already exist will not be changed."\
                             .format(recon_target_folder))
            tomo_folder_path = "{}/*".format(recon_folder)
            mkfolder_ifnotexist(recon_target_folder)
            tomo_recon_folder_ODD = "{}/ODD".format(recon_target_folder)
            tomo_recon_folder_EVN = "{}/EVN".format(recon_target_folder)
            mkfolder_ifnotexist(tomo_recon_folder_ODD)
            mkfolder_ifnotexist(tomo_recon_folder_EVN)
            list_dir = [ x for x in glob.glob(tomo_folder_path) if os.path.isdir(x)]
            for f in list_dir:
                basename = os.path.basename(f)
                recon_name_1 = "{}.rec".format(basename)
                recon_name_ODD_1 = "{}_ODD.rec".format(basename)
                recon_name_EVN_1 = "{}_EVN.rec".format(basename)
                recon_name_2 = "{}_rec.mrc".format(basename)
                recon_name_ODD_2 = "{}_ODD_rec.mrc".format(basename)
                recon_name_EVN_2 = "{}_EVN_rec.mrc".format(basename)
                if os.path.exists("{}/{}".format(f, recon_name_1)):
                    if not os.path.exists("{}/{}".format(recon_target_folder, recon_name_1)):
                        try:
                            cmd = "cd {}; ln -s ../../{}/{} .".format(recon_target_folder, f, recon_name_1)
                            subprocess.check_output(cmd, shell=True)
                        except:
                            pass
                    if os.path.exists("{}/ODD/{}".format(f, recon_name_ODD_1)) \
                                        and not os.path.exists("{}/{}".format(tomo_recon_folder_ODD, recon_name_ODD_1)):
                        try:
                            cmd = "cd {}; ln -s ../../../{}/ODD/{} .".format(tomo_recon_folder_ODD, f, recon_name_ODD_1)
                            subprocess.check_output(cmd, shell=True)
                        except:
                            pass
                    if os.path.exists("{}/EVN/{}".format(f, recon_name_EVN_1)) \
                                        and not os.path.exists("{}/{}".format(tomo_recon_folder_EVN, recon_name_EVN_1)):
                        try:
                            cmd = "cd {}; ln -s ../../../{}/EVN/{} .".format(tomo_recon_folder_EVN, f, recon_name_EVN_1)
                            subprocess.check_output(cmd, shell=True)
                        except:
                            pass
                if os.path.exists("{}/{}".format(f, recon_name_2)):
                    if not os.path.exists("{}/{}".format(recon_target_folder, recon_name_2)):
                        try:
                            cmd = "cd {}; ln -s ../../{}/{} .".format(recon_target_folder, f, recon_name_2)
                            subprocess.check_output(cmd, shell=True)
                        except:
                            pass
                    if os.path.exists("{}/ODD/{}".format(f, recon_name_ODD_2)) \
                                        and not os.path.exists("{}/{}".format(tomo_recon_folder_ODD, recon_name_ODD_2)):
                        try:
                            cmd = "cd {}; ln -s ../../../{}/ODD/{} .".format(tomo_recon_folder_ODD, f, recon_name_ODD_2)
                            subprocess.check_output(cmd, shell=True)
                        except:
                            pass
                    if os.path.exists("{}/EVN/{}".format(f, recon_name_EVN_2)) \
                                        and not os.path.exists("{}/{}".format(tomo_recon_folder_EVN, recon_name_EVN_2)):
                        try:
                            cmd = "cd {}; ln -s ../../../{}/EVN/{} .".format(tomo_recon_folder_EVN, f, recon_name_EVN_2)
                            subprocess.check_output(cmd, shell=True)
                        except:
                            pass
