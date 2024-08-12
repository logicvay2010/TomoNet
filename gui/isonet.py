import logging
import os
import traceback
import os.path
import glob
import shutil

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTabWidget, QMessageBox, QHeaderView, QTableWidgetItem
from PyQt5.QtGui import QFont

from TomoNet.util.utils import check_log_file, getLogContent
from TomoNet.util import metadata
from TomoNet.util.metadata import MetaData, Label, Item

from TomoNet.process.deconvolution import deconv_one
from TomoNet.util.dict2attr import idx2list

class IsoNet(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="IsoNet/isonet.setting"
        
        self.log_file = "IsoNet/isonet.log"

        self.isonet_folder = "IsoNet"

        self.tomogram_star = "IsoNet/tomograms.star"

        self.md = None

        self.pwd = os.getcwd().replace("\\","/")

        self.table_header = []

        self.read_star()
        
        check_log_file(self.log_file, "IsoNet")

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
        
    def setupUi(self):
        scriptDir = os.path.dirname(os.path.realpath(__file__))

        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.icon_trashCan = QtGui.QIcon()
        self.icon_trashCan.addPixmap(QtGui.QPixmap("{}/icons/trash_can.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.setUI_preparation()
        #self.setUI_tab2()
        
        self.addTab(self.tab, "Preparation")

        self.setTableWidget(self.tableWidget, self.md)
        
        self.tableWidget.cellDoubleClicked[int, int].connect(self.browseSlotTable)
        self.tableWidget.cellChanged[int,int].connect(self.updateMDItem) 

        self.pushButton_insert.clicked.connect(self.copyRow)
        self.pushButton_delete.clicked.connect(self.removeRow)
        self.pushButton_open_star.clicked.connect(self.open_star)
        self.pushButton_3dmod.clicked.connect(self.view_3dmod)

        #self.addTab(self.tab_2, "Predict Particles")
        
        for child in self.findChildren(QtWidgets.QLineEdit):
           child.textChanged.connect(self.save_setting)

        # self.lineEdit_input_model.textChanged.connect(self.model_folder_changed)
        # self.pushButton_input_folder_train.clicked.connect\
        #     (lambda: browse.browseFolderSlot(self.lineEdit_input_folder_train)) 
        
        # self.pushButton_continue_from_model.clicked.connect\
        #     (lambda: browse.browseSlot(self.lineEdit_continue_from_model, 'h5')) 

        # self.pushButton_input_folder_predict.clicked.connect\
        #     (lambda: browse.browseFolderSlot(self.lineEdit_input_folder_predict)) 
        # self.pushButton_input_model.clicked.connect\
        #     (lambda: browse.browseSlot(self.lineEdit_input_model, 'h5')) 
        
        # self.pushButton_train_network.clicked.connect(self.train_network)

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QCheckBox):
            child.stateChanged.connect(self.save_setting)

        # self.comboBox_prediction_condition.currentIndexChanged.connect(self.reload_table)

        # self.tableView_prediction.doubleClicked.connect(self.table_click)

        # self.pushButton_predict_network.clicked.connect(self.predict_network)

        # self.pushButton_delete_condition.clicked.connect(self.remove_condition)

        self.pushButton_deconv.clicked.connect(self.deconvolve)

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        
        self.retranslateUi_preparation()
        # self.retranslateUi_tab2()
        self.read_settting()
        # self.model_folder_changed()
        # self.reload_table()

    def setUI_preparation(self):
        #tab 1
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 5, 10, 5)

        self.tableWidget = QtWidgets.QTableWidget(self.tab)
        self.tableWidget.setMinimumSize(QtCore.QSize(0, 180))
        self.tableWidget.setMaximumSize(QtCore.QSize(16777215, 600))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.tableWidget.setFont(font)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)

        self.horizontalLayout_1.addWidget(self.tableWidget)

        self.verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_1.setObjectName("verticalLayout_1")
        self.pushButton_open_star = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton_open_star.setFont(font)
        self.pushButton_open_star.setObjectName("pushButton_open_star")
        self.verticalLayout_1.addWidget(self.pushButton_open_star)
        
        self.pushButton_insert = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton_insert.setFont(font)
        self.pushButton_insert.setObjectName("pushButton_insert")
        self.verticalLayout_1.addWidget(self.pushButton_insert)
        
        self.pushButton_delete = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton_delete.setFont(font)
        self.pushButton_delete.setObjectName("pushButton_delete")
        self.verticalLayout_1.addWidget(self.pushButton_delete)
        
        self.pushButton_3dmod = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton_3dmod.setFont(font)
        self.pushButton_3dmod.setObjectName("pushButton_3dmod")
        self.verticalLayout_1.addWidget(self.pushButton_3dmod)
        
        self.horizontalLayout_1.addLayout(self.verticalLayout_1)

        self.gridLayout_preparation = QtWidgets.QGridLayout(self.tab)

        # group widget deconvolution
        self.groupBox_deconv = QtWidgets.QGroupBox(self.tab)
        self.groupBox_deconv.setMinimumSize(QtCore.QSize(0, 120))
        self.groupBox_deconv.setMaximumSize(QtCore.QSize(16777215, 120))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.groupBox_deconv.setFont(font)
        self.groupBox_deconv.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_deconv.setFlat(False)
        self.groupBox_deconv.setObjectName("groupBox_deconv")
        
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_deconv)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        
        self.label_deconv_dir = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_deconv_dir.setMinimumSize(QtCore.QSize(140, 0))
        self.label_deconv_dir.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_deconv_dir.setObjectName("label_deconv_dir")
        self.horizontalLayout_9.addWidget(self.label_deconv_dir)
        
        self.lineEdit_deconv_dir = QtWidgets.QLineEdit(self.groupBox_deconv)
        self.lineEdit_deconv_dir.setMinimumSize(QtCore.QSize(200, 25))
        self.lineEdit_deconv_dir.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_deconv_dir.setObjectName("lineEdit_deconv_dir")
        self.horizontalLayout_9.addWidget(self.lineEdit_deconv_dir)
        
        self.button_deconov_dir = QtWidgets.QPushButton(self.groupBox_deconv)
        self.button_deconov_dir.setStyleSheet("background-color:rgb(255, 255, 255)")
        self.button_deconov_dir.setText("")
        self.button_deconov_dir.setIcon(self.icon)
        self.button_deconov_dir.setIconSize(QtCore.QSize(36, 20))
        self.button_deconov_dir.setObjectName("button_deconov_dir")
        self.horizontalLayout_9.addWidget(self.button_deconov_dir)
        
        self.horizontalLayout_7.addLayout(self.horizontalLayout_9)
        
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.label_tomo_index_deconv = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_tomo_index_deconv.setMinimumSize(QtCore.QSize(100, 0))
        self.label_tomo_index_deconv.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index_deconv.setObjectName("label_tomo_index_deconv")
        self.horizontalLayout_6.addWidget(self.label_tomo_index_deconv)
        self.lineEdit_tomo_index_deconv = QtWidgets.QLineEdit(self.groupBox_deconv)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.lineEdit_tomo_index_deconv.sizePolicy().hasHeightForWidth())
        self.lineEdit_tomo_index_deconv.setSizePolicy(sizePolicy)
        self.lineEdit_tomo_index_deconv.setMinimumSize(QtCore.QSize(0, 25))
        self.lineEdit_tomo_index_deconv.setMaximumSize(QtCore.QSize(16777215, 25))

        self.lineEdit_tomo_index_deconv.setStyleSheet("")
        self.lineEdit_tomo_index_deconv.setPlaceholderText("")
        self.lineEdit_tomo_index_deconv.setObjectName("lineEdit_tomo_index_deconv")
        self.horizontalLayout_6.addWidget(self.lineEdit_tomo_index_deconv)
        
        self.horizontalLayout_7.addLayout(self.horizontalLayout_6)
        
        self.gridLayout_3.addLayout(self.horizontalLayout_7, 0, 0, 1, 1)
        
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        
        self.label_ncpu = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_ncpu.setMinimumSize(QtCore.QSize(60, 0))
        self.label_ncpu.setWhatsThis("")
        self.label_ncpu.setStyleSheet("")
        self.label_ncpu.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_ncpu.setObjectName("label_ncpu")
        self.horizontalLayout_4.addWidget(self.label_ncpu)
        
        self.lineEdit_ncpu = QtWidgets.QLineEdit(self.groupBox_deconv)
        self.lineEdit_ncpu.setMinimumSize(QtCore.QSize(60, 25))
        self.lineEdit_ncpu.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_ncpu.setObjectName("lineEdit_ncpu")
        self.horizontalLayout_4.addWidget(self.lineEdit_ncpu)
        
        self.horizontalLayout_8.addLayout(self.horizontalLayout_4)
        
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        
        self.label_chunk_size = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_chunk_size.setMinimumSize(QtCore.QSize(100, 0))
        self.label_chunk_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_chunk_size.setObjectName("label_chunk_size")
        self.horizontalLayout_3.addWidget(self.label_chunk_size)
        
        self.lineEdit_chunk_size = QtWidgets.QLineEdit(self.groupBox_deconv)
        self.lineEdit_chunk_size.setMinimumSize(QtCore.QSize(60, 25))
        self.lineEdit_chunk_size.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_chunk_size.setObjectName("lineEdit_chunk_size")
        self.horizontalLayout_3.addWidget(self.lineEdit_chunk_size)
        
        self.horizontalLayout_8.addLayout(self.horizontalLayout_3)
        
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_highpassnyquist = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_highpassnyquist.setMinimumSize(QtCore.QSize(140, 0))
        self.label_highpassnyquist.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_highpassnyquist.setObjectName("label_highpassnyquist")
        self.horizontalLayout_2.addWidget(self.label_highpassnyquist)
        
        self.lineEdit_highpassnyquist = QtWidgets.QLineEdit(self.groupBox_deconv)
        self.lineEdit_highpassnyquist.setMinimumSize(QtCore.QSize(60, 25))
        self.lineEdit_highpassnyquist.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_highpassnyquist.setObjectName("lineEdit_highpassnyquist")
        self.horizontalLayout_2.addWidget(self.lineEdit_highpassnyquist)
        
        self.horizontalLayout_8.addLayout(self.horizontalLayout_2)
        
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_overlap = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_overlap.setMinimumSize(QtCore.QSize(80, 0))
        self.label_overlap.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_overlap.setObjectName("label_overlap")
        self.horizontalLayout_5.addWidget(self.label_overlap)
        
        self.lineEdit_overlap = QtWidgets.QLineEdit(self.groupBox_deconv)
        self.lineEdit_overlap.setMinimumSize(QtCore.QSize(60, 25))
        self.lineEdit_overlap.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_overlap.setObjectName("lineEdit_overlap")
        self.horizontalLayout_5.addWidget(self.lineEdit_overlap)
        
        self.horizontalLayout_8.addLayout(self.horizontalLayout_5)
        
        self.gridLayout_3.addLayout(self.horizontalLayout_8, 1, 0, 1, 1)
        

        self.gridLayout_preparation.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_preparation.addWidget(self.groupBox_deconv, 1, 0, 1, 1)
        # self.gridLayout_preparation.addLayout(self.horizontalLayout_1_2, 1, 0, 1, 1)
        # self.gridLayout_preparation.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)
        # self.gridLayout_preparation.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)
        # self.gridLayout_preparation.addWidget(self.groupBox_2, 4, 0, 1, 1)

        self.spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_preparation.addItem(self.spacerItem3, 2, 0, 1, 1)

        self.horizontalLayout_17 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_17.setObjectName("horizontalLayout_17")
        self.pushButton_deconv = QtWidgets.QPushButton(self.tab)
        self.pushButton_deconv.setEnabled(True)
        self.pushButton_deconv.setMinimumSize(QtCore.QSize(120, 48))
        self.pushButton_deconv.setMaximumSize(QtCore.QSize(120, 48))
        self.pushButton_deconv.setObjectName("run")
        self.horizontalLayout_17.addWidget(self.pushButton_deconv)
        
        self.gridLayout_preparation.addLayout(self.horizontalLayout_17, 3, 0, 1, 1)
        #self.gridLayout_preparation.addLayout(self.horizontalLayout_last, 6, 0, 1, 1)
    
    def setUI_tab2(self):
        #tab 2
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab")

        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(10, 5, 10, 5)

        self.label_input_folder_predict = QtWidgets.QLabel(self.tab_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_input_folder_predict.sizePolicy().hasHeightForWidth())
        self.label_input_folder_predict.setSizePolicy(sizePolicy)
        self.label_input_folder_predict.setMinimumSize(QtCore.QSize(120, 0))
        self.label_input_folder_predict.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_input_folder_predict.setObjectName("label_input_folder_predict")
        self.horizontalLayout_4.addWidget(self.label_input_folder_predict)

        self.lineEdit_input_folder_predict = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_input_folder_predict.setInputMask("")
        self.lineEdit_input_folder_predict.setObjectName("lineEdit_input_folder_predict")
        self.horizontalLayout_4.addWidget(self.lineEdit_input_folder_predict)

        self.pushButton_input_folder_predict = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_input_folder_predict.setText("")
        self.pushButton_input_folder_predict.setIcon(self.icon)
        self.pushButton_input_folder_predict.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_input_folder_predict.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_input_folder_predict.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_input_folder_predict.setObjectName("pushButton_input_folder_predict")
        self.horizontalLayout_4.addWidget(self.pushButton_input_folder_predict)

        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setContentsMargins(10, 5, 10, 5)

        self.label_input_model = QtWidgets.QLabel(self.tab_2)
        self.label_input_model.setSizePolicy(sizePolicy)
        self.label_input_model.setMinimumSize(QtCore.QSize(120, 0))
        self.label_input_model.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_input_model.setObjectName("label_input_model")
        self.horizontalLayout_5.addWidget(self.label_input_model)

        self.lineEdit_input_model = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_input_model.setInputMask("")
        self.lineEdit_input_model.setObjectName("lineEdit_input_model")
        self.horizontalLayout_5.addWidget(self.lineEdit_input_model)

        self.pushButton_input_model = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_input_model.setText("")
        self.pushButton_input_model.setIcon(self.icon)
        self.pushButton_input_model.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_input_model.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_input_model.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_input_model.setObjectName("pushButton_input_model")
        self.horizontalLayout_5.addWidget(self.pushButton_input_model)

        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setContentsMargins(10, 5, 10, 5)
        
        self.label_box_size_predict = QtWidgets.QLabel(self.tab_2)
        self.label_box_size_predict.setSizePolicy(sizePolicy)
        self.label_box_size_predict.setMinimumSize(QtCore.QSize(130, 0))
        self.label_box_size_predict.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_box_size_predict.setObjectName("label_box_size_predict")
        self.horizontalLayout_7.addWidget(self.label_box_size_predict)

        self.lineEdit_box_size_predict = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_box_size_predict.setInputMask("")
        self.lineEdit_box_size_predict.setObjectName("lineEdit_box_size_predict")
        self.horizontalLayout_7.addWidget(self.lineEdit_box_size_predict)

        self.label_unit_size_predict = QtWidgets.QLabel(self.tab_2)
        self.label_unit_size_predict.setSizePolicy(sizePolicy)
        self.label_unit_size_predict.setMinimumSize(QtCore.QSize(170, 0))
        self.label_unit_size_predict.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_unit_size_predict.setObjectName("label_unit_size_predict")
        self.horizontalLayout_7.addWidget(self.label_unit_size_predict)

        self.lineEdit_unit_size_predict = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_unit_size_predict.setInputMask("")
        self.lineEdit_unit_size_predict.setObjectName("lineEdit_unit_size_predict")
        self.horizontalLayout_7.addWidget(self.lineEdit_unit_size_predict)

        self.label_min_patch_size_predict = QtWidgets.QLabel(self.tab_2)
        self.label_min_patch_size_predict.setSizePolicy(sizePolicy)
        self.label_min_patch_size_predict.setMinimumSize(QtCore.QSize(120, 0))
        self.label_min_patch_size_predict.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_patch_size_predict.setObjectName("label_min_patch_size_predict")
        self.horizontalLayout_7.addWidget(self.label_min_patch_size_predict)

        self.lineEdit_min_patch_size_predict = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_min_patch_size_predict.setInputMask("")
        self.lineEdit_min_patch_size_predict.setObjectName("lineEdit_min_patch_size_predict")
        self.horizontalLayout_7.addWidget(self.lineEdit_min_patch_size_predict)

        self.label_y_label_size_predict = QtWidgets.QLabel(self.tab_2)
        self.label_y_label_size_predict.setSizePolicy(sizePolicy)
        self.label_y_label_size_predict.setMinimumSize(QtCore.QSize(90, 0))
        self.label_y_label_size_predict.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_y_label_size_predict.setObjectName("label_y_label_size_predict")
        self.horizontalLayout_7.addWidget(self.label_y_label_size_predict)

        self.lineEdit_y_label_size_predict = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_y_label_size_predict.setInputMask("")
        self.lineEdit_y_label_size_predict.setObjectName("lineEdit_y_label_size_predict")
        self.horizontalLayout_7.addWidget(self.lineEdit_y_label_size_predict)

        self.groupBox_1 = QtWidgets.QGroupBox()

        self.verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_1.setContentsMargins(5, 5, 5, 5)

        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setContentsMargins(10, 5, 10, 5)

        self.label_tolerance = QtWidgets.QLabel(self.tab_2)
        self.label_tolerance.setSizePolicy(sizePolicy)
        self.label_tolerance.setMinimumSize(QtCore.QSize(120, 0))
        self.label_tolerance.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tolerance.setObjectName("label_tolerance")
        self.horizontalLayout_8.addWidget(self.label_tolerance)

        self.lineEdit_tolerance = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_tolerance.setInputMask("")
        self.lineEdit_tolerance.setObjectName("lineEdit_tolerance")

        self.horizontalLayout_8.addWidget(self.lineEdit_tolerance)

        self.label_margin = QtWidgets.QLabel(self.tab_2)
        self.label_margin.setSizePolicy(sizePolicy)
        self.label_margin.setMinimumSize(QtCore.QSize(120, 0))
        self.label_margin.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_margin.setObjectName("label_margin")
        self.horizontalLayout_8.addWidget(self.label_margin)

        self.lineEdit_margin = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_margin.setInputMask("")
        self.lineEdit_margin.setObjectName("lineEdit_margin")

        self.horizontalLayout_8.addWidget(self.lineEdit_margin)

        self.label_save_seg_map = QtWidgets.QLabel(self.tab_2)
        self.label_save_seg_map.setSizePolicy(sizePolicy)
        self.label_save_seg_map.setMinimumSize(QtCore.QSize(120, 0))
        self.label_save_seg_map.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_save_seg_map.setObjectName("label_save_seg_map")
        self.horizontalLayout_8.addWidget(self.label_save_seg_map)

        self.comboBox_save_seg_map = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_save_seg_map.setObjectName("comboBox_save_seg_map")
        self.comboBox_save_seg_map.addItem("")
        self.comboBox_save_seg_map.addItem("")
        self.horizontalLayout_8.addWidget(self.comboBox_save_seg_map)

        self.verticalLayout_1.addLayout(self.horizontalLayout_8)
        
        self.groupBox_1.setLayout(self.verticalLayout_1)

        self.horizontalLayout_last_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last_2.setObjectName("horizontalLayout_last")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last_2.addItem(spacerItem1)

        self.label_print_only_predict_network = QtWidgets.QLabel(self.tab_2)
        self.label_print_only_predict_network.setSizePolicy(sizePolicy)
        self.label_print_only_predict_network.setMinimumSize(QtCore.QSize(120, 0))
        self.label_print_only_predict_network.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_print_only_predict_network.setObjectName("label_print_only_predict_network")
        self.horizontalLayout_last_2.addWidget(self.label_print_only_predict_network)

        self.checkBox_print_only_predict_network = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_print_only_predict_network.setChecked(False)
        self.checkBox_print_only_predict_network.setObjectName("checkBox_print_only_predict_network")
        self.horizontalLayout_last_2.addWidget(self.checkBox_print_only_predict_network)

        self.pushButton_predict_network = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_predict_network.setSizePolicy(sizePolicy)
        self.pushButton_predict_network.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_predict_network.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_predict_network.setObjectName("run")
        self.horizontalLayout_last_2.addWidget(self.pushButton_predict_network)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last_2.addItem(spacerItem2)

        self.gridLayout_prediction = QtWidgets.QGridLayout(self.tab_2)

        self.gridLayout_prediction.addLayout(self.horizontalLayout_4, 0, 0, 1, 1)
        self.gridLayout_prediction.addLayout(self.horizontalLayout_5, 1, 0, 1, 1)
        self.gridLayout_prediction.addLayout(self.horizontalLayout_7, 3, 0, 1, 1)
        self.gridLayout_prediction.addWidget(self.groupBox_1, 4, 0, 1, 1)

        #self.spacerItem4 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #self.gridLayout_prediction.addItem(self.spacerItem4, 5, 0, 1, 1)

        self.gridLayout_prediction.addLayout(self.horizontalLayout_last_2, 5, 0, 1, 1)

        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setContentsMargins(10, 5, 10, 5)

        self.label_prediction_condition = QtWidgets.QLabel(self.tab_2)
        self.label_prediction_condition.setSizePolicy(sizePolicy)
        self.label_prediction_condition.setMinimumSize(QtCore.QSize(60, 0))
        self.label_prediction_condition.setMaximumSize(QtCore.QSize(80, 30))
        self.label_prediction_condition.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_prediction_condition.setObjectName("label_prediction_condition")
        
        self.horizontalLayout_10.addWidget(self.label_prediction_condition)

        self.comboBox_prediction_condition = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_prediction_condition.setObjectName("comboBox_prediction_condition")
        #self.comboBox_prediction_condition.addItem("")
        #self.comboBox_prediction_condition.addItem("")
        self.horizontalLayout_10.addWidget(self.comboBox_prediction_condition)

        self.pushButton_delete_condition = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_delete_condition.setSizePolicy(sizePolicy)
        self.pushButton_delete_condition.setIcon(self.icon_trashCan)
        self.pushButton_delete_condition.setMaximumSize(QtCore.QSize(40, 30))
        self.pushButton_delete_condition.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_delete_condition.setObjectName("delete_condition")
        
        self.horizontalLayout_10.addWidget(self.pushButton_delete_condition)
        
        self.gridLayout_prediction.addLayout(self.horizontalLayout_10, 6, 0, 1, 1)

        self.tableView_prediction = QtWidgets.QTableWidget(self)
        
        header_labels_prediction = metadata.header_labels_prediction
        
        self.tableView_prediction.setColumnCount(len(header_labels_prediction))
        self.tableView_prediction.setHorizontalHeaderLabels(header_labels_prediction)
        
        header_prediction = self.tableView_prediction.horizontalHeader()   
        header_prediction.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView_prediction.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        
        self.gridLayout_prediction.addWidget(self.tableView_prediction, 7, 0)
       
    def retranslateUi_preparation(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.pushButton_open_star.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Open a saved star file.</span></p></body></html>"))
        self.pushButton_open_star.setText(_translate("Form", "Open STAR file"))
        self.pushButton_insert.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Add new items to the star file.</span></p></body></html>"))
        self.pushButton_insert.setText(_translate("Form", "Insert"))
        self.pushButton_delete.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Delete items from the star file</span></p></body></html>"))
        self.pushButton_delete.setText(_translate("Form", "Delete"))
        self.pushButton_3dmod.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">open selected maps in 3dmod view.</span></p></body></html>"))
        self.pushButton_3dmod.setText(_translate("Form", "3dmod view"))

        self.groupBox_deconv.setTitle(_translate("Form", "Deconvolve ctf"))
        self.label_deconv_dir.setText(_translate("Form", "deconvolve directory"))
        self.lineEdit_deconv_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">a folder path to save your deconvolved maps.</span></p><p><span style=\" font-size:9pt;\"><br/></span></p></body></html>"))
        self.lineEdit_deconv_dir.setPlaceholderText(_translate("Form", "deconv"))
        self.label_tomo_index_deconv.setText(_translate("Form", "tomo index"))
        self.lineEdit_tomo_index_deconv.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If this value is set, process only the tomograms listed in this index. e.g. 1,2,3,4</span></p></body></html>"))
        self.label_ncpu.setText(_translate("Form", "ncpu"))
        self.lineEdit_ncpu.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">number of gpu to use in deconvolve</span></p></body></html>"))
        self.lineEdit_ncpu.setPlaceholderText(_translate("Form", "4"))
        self.label_chunk_size.setText(_translate("Form", "chunk size"))
        self.lineEdit_chunk_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">(None) When your computer has enough memory, please keep the chunk_size as the default value: None . Otherwise, you can let the program crop the tomogram into multiple chunks for multiprocessing and assembly them into one. The chunk_size defines the size of individual chunk. This option may induce artifacts along edges of chunks. When that happen, you may use larger overlap_rate.</span></p></body></html>"))
        self.lineEdit_chunk_size.setPlaceholderText(_translate("Form", "None"))
        self.label_highpassnyquist.setText(_translate("Form", "highpassnyquist"))
        self.lineEdit_highpassnyquist.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">(0.02) Highpass filter at very low resolution.</span></p></body></html>"))
        self.lineEdit_highpassnyquist.setPlaceholderText(_translate("Form", "0.02"))
        self.label_overlap.setText(_translate("Form", "overlap"))
        self.lineEdit_overlap.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The overlapping rate for adjecent tiles.</span></p></body></html>"))
        self.lineEdit_overlap.setPlaceholderText(_translate("Form", "0.25"))

        self.pushButton_deconv.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">click to run isonet deconvolve</span></p></body></html>"))
        self.pushButton_deconv.setText(_translate("Form", "Deconvolve"))

    def retranslateUi_tab2(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))

        self.label_print_only_predict_network.setText(_translate("Form", "print cmd only:"))

        self.label_input_folder_predict.setText(_translate("Form", "Input Folder:"))
        self.label_input_folder_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        
        self.pushButton_predict_network.setText(_translate("Form", "Predict"))
                   
    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 3:
                    in_current_page = False
            elif x.objectName() == "log_window":
                if in_current_page:
                    self.log_window = x
                    self.log_window.setText(getLogContent(txt))
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
        data['deconv_dir'] = ""
        data['tomo_index_deconv'] = ""
        data['ncpu'] = ""
        data['chunk_size'] = ""
        data['highpassnyquist'] = ""
        data['overlap'] = ""

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
        self.lineEdit_deconv_dir.setText(data['deconv_dir'])
        self.lineEdit_tomo_index_deconv.setText(data['tomo_index_deconv'])
        self.lineEdit_ncpu.setText(data['ncpu'])
        self.lineEdit_chunk_size.setText(data['chunk_size'])
        self.lineEdit_highpassnyquist.setText(data['highpassnyquist'])
        self.lineEdit_overlap.setText(data['overlap'])
    
    def save_setting(self):
        param = {}
        param['deconv_dir'] = self.lineEdit_deconv_dir.text()
        param['tomo_index_deconv'] = self.lineEdit_tomo_index_deconv.text()
        param['ncpu'] = self.lineEdit_ncpu.text()
        param['chunk_size'] = self.lineEdit_chunk_size.text()
        param['highpassnyquist'] = self.lineEdit_highpassnyquist.text()
        param['overlap'] = self.lineEdit_overlap.text()

        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))     

    def get_display_name(self, label):
        
        switcher = {
            "rlnMicrographName": "MicrographName",
            "rlnPixelSize": "PixelSize (A)",
            "rlnDefocus": "Defocus (A)",
            "rlnNumberSubtomo":"NumberSubtomo",
            "rlnSnrFalloff":"SnrFalloff",
            "rlnDeconvStrength": "DeconvStrength",
            "rlnDeconvTomoName":"DeconvTomoName",
            "rlnCorrectedTomoName":"CorrectedTomoName",
            "rlnMaskBoundary":"MaskBoundary",
            "rlnMaskDensityPercentage": "MaskDensityPercentage",
            "rlnMaskStdPercentage": "MaskStdPercentage",
            "rlnMaskName": "MaskName"
        }
        return switcher.get(label, "Unkown header")

    def get_toolTip(self, label):
        switcher = {
            "rlnMicrographName": "Your tomogram filenames",
            "rlnPixelSize": "pixel size of your input tomograms",
            "rlnDefocus": "estimated defocus value around 0 degree",
            "rlnNumberSubtomo":"number of subtomograms to be extraced",
            "rlnSnrFalloff":"SNR fall rate with the frequency",
            "rlnDeconvStrength": "(1.0) Strength of the deconvolution",
            "rlnDeconvTomoName":"automaticly saved deconved tomogram filename",
            "rlnMaskBoundary":"model file that define your mask boundary(optional)",
            "rlnMaskDensityPercentage": "The approximate percentage of pixels to keep based on their local pixel density",
            "rlnMaskStdPercentage": "The approximate percentage of pixels to keep based on their local standard deviation",
            "rlnMaskName": "automaticly saved mask tomogram filename"
        }
        return switcher.get(label, "None")
    
    def setTableWidget(self, tw, md):
        
        nRows = len(md)
        labels = md.getLabels()
        nColumns = len(labels)
        tw.setColumnCount(nColumns- 1) 
        tw.setRowCount(nRows)

        label_2 = [label for label in labels]
        for i, lab in enumerate(label_2):
            #tw.horizontalHeaderItem(i).setToolTip(get_toolTip(lab))
            label_2[i] = self.get_display_name(lab)
            #if lab == 'Defocus' or lab == 'PixelSize':
            #    label_2[i] =  lab+" (A)"

        tw.setHorizontalHeaderLabels(label_2[1:])
        tw.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        for i, lab in enumerate(labels):
            if i > 0:
                tw.horizontalHeaderItem(i-1).setToolTip(self.get_toolTip(lab))
        # data insertion
        for i, it in enumerate(md):
            for j in range(tw.columnCount()):
                tw.setItem(i, j, QTableWidgetItem(str(getattr(it,labels[j+1]))))
    
    def read_star(self):
        if not self.isValid(self.tomogram_star):
            self.md = MetaData()
            #self.md.addLabels('rlnIndex','rlnMicrographName','rlnPixelSize','rlnDefocus','rlnNumberSubtomo')
            self.md.addLabels('rlnIndex','rlnMicrographName','rlnPixelSize','rlnDefocus','rlnNumberSubtomo','rlnSnrFalloff','rlnDeconvStrength','rlnDeconvTomoName','rlnMaskBoundary','rlnMaskDensityPercentage','rlnMaskStdPercentage','rlnMaskName')
            self.md.write(self.tomogram_star)
        else:
            self.md = MetaData()
            self.md.read(self.tomogram_star)

        self.table_header = self.md.getLabels()
    
    def read_star_gui(self, star_file):

        if self.isValid(star_file):
            md_cad = MetaData()
            md_cad.read(star_file)
            if "rlnMicrographName" not in md_cad.getLabels():
                return 1
            else:
                self.tomogram_star = star_file
                self.md = MetaData()
                self.md.read(self.tomogram_star)
                self.table_header = self.md.getLabels()
            return 0
    
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

    def isValidPath(self, path):
        '''
        returns True if the file exists and can be
        opened.  Returns False otherwise.
        '''
        try:
            isDir = os.path.isdir(path)
            return isDir
        except:
            return False
    
    def switch_btn(self, btn):
        switcher = {
            "mask_dir": self.lineEdit_mask_dir,
            "deconv_dir": self.lineEdit_deconv_dir,
            "subtomo_dir": self.lineEdit_subtomo_dir,
            "result_dir_refine": self.lineEdit_result_dir_refine,
            "result_dir_predict": self.lineEdit_result_dir_predict,
            "subtomo_star_refine":self.lineEdit_subtomo_star_refine,
            "pretrain_model_refine":self.lineEdit_pretrain_model_refine,
            "tomo_star_predict": self.lineEdit_tomo_star_predict,
            "pretrain_model_predict":self.lineEdit_pretrain_model_predict,
            "continue_from": self.lineEdit_continue_iter
        }
        return switcher.get(btn, "Invaid btn name")
    
    def browseSlot(self, btn):
        ''' Called when the user presses the Browse button
        '''
        lineEdit = self.switch_btn(btn)
        
        pwd = os.getcwd().replace("\\","/")
        
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        
        flt = "All Files (*)"
        if btn == "continue_from":
            flt = "json file (*.json);;All Files (*)"
        if btn == "subtomo_star_refine" or btn == "tomo_star_predict":
            flt = "star file (*.star);;All Files (*)"
        if btn == "pretrain_model_refine" or btn == "pretrain_model_predict":
            flt = "model file (*.h5);;All Files (*)"
            
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                        None,
                        "Choose File",
                        "",
                        flt,
                        options=options)
        if fileName:
            simple_name = self.model.sim_path(pwd,fileName)
            lineEdit.setText(simple_name)

    def file_types(self, item):
        switcher = {
            "rlnMicrographName":"mrc or rec file (*.mrc *.rec) ;; All Files (*)",
            "rlnDeconvTomoName":"mrc or rec file (*.mrc *.rec) ;; All Files (*)",
            "rlnMaskName":"mrc or rec file (*.mrc *.rec) ;; All Files (*)",
            "rlnMaskBoundary": "mod file (*.mod) ;; All Files (*)" 
        }
        return switcher.get(item, "Invaid file types")
    
    def browseSlotTable(self, i, j):
        ''' Called when the user presses the Browse folder button
        '''
        if self.table_header[j+1] in ["rlnMicrographName", "rlnMaskBoundary", "rlnDeconvTomoName", "rlnMaskName"]:
            try:
                options = QtWidgets.QFileDialog.Options()
                options |= QtWidgets.QFileDialog.DontUseNativeDialog
                fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                                None,
                                "Choose File",
                                "",
                                self.file_types(self.table_header[j+1]), options=options)
                if not fileName:
                    fileName = self.tableWidget.item(i, j).text()
                #pwd = os.getcwd().replace("\\","/")
                simple_path = self.sim_path(self.pwd, fileName)
                self.tableWidget.setItem(i, j, QTableWidgetItem(simple_path))
            except:
                ##TODO: record to log.
                pass
        else:
            pass
    
    def sim_path(self, pwd, path):
        if pwd in path:
            return "." + path[len(pwd):]
        else:
            return path
    
    def updateMD(self):        
        star_file = self.tomogram_star
        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()
        data = self.md._data
        self.md = MetaData()
        self.md.addLabels('rlnIndex')
        for j in range(columnCount):
            self.md.addLabels(self.table_header[j+1])
            #self.model.md.addLabels(self.tableWidget.horizontalHeaderItem(j).text())

        for i in range(rowCount):
            #TODO check the folder contains only tomograms.
            it = Item()
            self.md.addItem(it)
            self.md._setItemValue(it,Label('rlnIndex'),str(i+1))
            for j in range(columnCount):
                try:
                    #print("update:",Label(self.table_header[j+1]),self.tableWidget.item(i, j).text())
                    if len(self.tableWidget.item(i, j).text()) <1:
                        
                        if self.table_header[j+1] != "rlnMaskBoundary":
                            previous_value = getattr(data[i], self.table_header[j+1])
                        else:
                            previous_value = "None"

                        self.md._setItemValue(it, Label(self.table_header[j+1]), previous_value)
                        self.tableWidget.setItem(i, j, QTableWidgetItem(str(previous_value)))
                    else:
                        self.md._setItemValue(it, Label(self.table_header[j+1]),self.tableWidget.item(i, j).text())
                     
                    #self.model.md._setItemValue(it,Label(self.tableWidget.horizontalHeaderItem(j).text()),self.tableWidget.item(i, j).text())
                except:
                    previous_value = getattr(data[i],self.table_header[j+1])
                    self.md._setItemValue(it, Label(self.table_header[j+1]),previous_value)
                    self.tableWidget.setItem(i, j, QTableWidgetItem(str(previous_value)))
                    #print("error in seeting values for {}! set it to previous value automatically.".format(self.tableWidget.horizontalHeaderItem(j).text()))
        self.md.write(star_file)

    def updateMDItem(self, i, j):
        try:
            current_value = self.tableWidget.item(i, j).text()
            self.updateMD()
        except:
            pass
    
    def copyRow(self):
        rowCount = self.tableWidget.rowCount()
        columnCount = self.tableWidget.columnCount()
        if rowCount <=0 :
            self.tableWidget.insertRow(self.tableWidget.rowCount())
            for j in range(columnCount):
                #self.model.md._setItemValue(it,Label(self.table_header[j+1]),self.tableWidget.item(i, j).text())
                #print(self.default_value(self.table_header[j+1]))
                self.tableWidget.setItem(0, j, QTableWidgetItem(self.default_value(self.table_header[j+1])))
                #print(self.tableWidget.item(0, j).text())
        else:
            indices = self.tableWidget.selectionModel().selectedRows() 

            if indices:
                for index in sorted(indices):
                    self.tableWidget.insertRow(self.tableWidget.rowCount())
                    rowCount = self.tableWidget.rowCount()
                    for j in range(columnCount):
                        if self.table_header[j+1] in ["rlnDeconvTomoName","rlnMaskName","rlnCorrectedTomoName","rlnMaskBoundary"]:
                            self.tableWidget.setItem(rowCount-1, j, QTableWidgetItem("None"))
                        #self.tableWidget.cellChanged[rowCount-1, j].connect(self.updateMD)  
                        else:
                            self.tableWidget.setItem(rowCount-1, j, QTableWidgetItem(self.tableWidget.item(index.row(), j).text()))
            else:
                self.tableWidget.insertRow(self.tableWidget.rowCount())
                rowCount = self.tableWidget.rowCount()
                for j in range(columnCount):
                    if self.table_header[j+1] in ["rlnDeconvTomoName","rlnMaskName","rlnCorrectedTomoName","rlnMaskBoundary"]:
                            self.tableWidget.setItem(rowCount-1, j, QTableWidgetItem("None"))
                    elif not self.tableWidget.item(rowCount-2, j) is None:
                        self.tableWidget.setItem(rowCount-1, j, QTableWidgetItem(self.tableWidget.item(rowCount-2, j).text()))
        self.updateMD()
    
    def removeRow(self):
        #print(self.tableWidget.selectionModel().selectedIndexes()[0].row())
        #print(self.tableWidget.selectionModel().selectedIndexes()[0].column())

        indices = self.tableWidget.selectionModel().selectedRows() 
        if indices:
            for index in sorted(indices,reverse=True):
                self.tableWidget.removeRow(index.row()) 
        self.updateMD()

    def open_star(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                        None,
                        "Choose File",
                        "",
                        "Star file (*.star)",
                        options=options)
        if fileName:
            try:
                tomo_file = self.sim_path(self.pwd, fileName)
                read_result = self.read_star_gui(tomo_file)
                if read_result == 1:
                    self.warn_window("The input star file is not legid!")
                else:
                    self.setTableWidget(self.tableWidget, self.md)
            except:
                print("warning")
                pass

    def view_3dmod(self):
        slected_items = self.tableWidget.selectedItems()
        if len(slected_items) > 0:
            cmd = "3dmod"
            model_file=""
            previous_i = -1
            for item in slected_items:
                i = item.row()
                j = item.column()
                if previous_i != -1 and i != previous_i:
                    cmd = "{} {} {}".format(cmd,model_file,"; 3dmod")
                    model_file=""
                item_text = self.tableWidget.item(i, j).text()
                if item_text[-4:] == '.mrc' or item_text[-4:] == '.rec':
                    cmd = "{} {}".format(cmd,item_text)
                if self.table_header[j+1]=="rlnMaskBoundary" and item_text != "None":
                    model_file = "{}".format(item_text)
                previous_i = i
            
            cmd = "{} {}".format(cmd, model_file)
            #print(cmd)

            if cmd != "3dmod":
                os.system(cmd)
            else:
                self.warn_window("selected items are not mrc or rec file(s)")
    
    def default_value(self, label):
        switcher = {
            "rlnMicrographName": "None",
            "rlnPixelSize": "1",
            "rlnDefocus": "0",
            "rlnNumberSubtomo":"100",
            "rlnSnrFalloff":"1",
            "rlnDeconvStrength": "1",
            "rlnDeconvTomoName":"None",
            "rlnMaskBoundary":"None",
            "rlnMaskDensityPercentage": "50",
            "rlnMaskStdPercentage": "50",
            "rlnMaskName": "None"

        }
        return switcher.get(label, "None")
    
    def get_deconv_params(self):
        tomogram_star = self.tomogram_star

        if self.lineEdit_deconv_dir.text():
            deconv_folder = "{}/{}".format(self.isonet_folder, self.lineEdit_deconv_dir.text())
        else:
            deconv_folder = "{}/{}".format(self.isonet_folder, "deconv")
        if self.lineEdit_tomo_index_deconv.text():
            tomo_idx = self.lineEdit_tomo_index_deconv.text()
        else:
            return "Please define tomo index for Ctf deconvolution."
        if self.lineEdit_ncpu.text():
            ncpu = int(self.lineEdit_ncpu.text())
        else:
            ncpu = 6
        if self.lineEdit_highpassnyquist.text():
            highpassnyquist = float(self.lineEdit_highpassnyquist.text())
        else:
            highpassnyquist = 0.02
        if self.lineEdit_chunk_size.text():
            chunk_size = float(self.lineEdit_chunk_size.text())
        else:
            chunk_size = 200
        if self.lineEdit_overlap.text():
            overlap_rate = float(self.lineEdit_overlap.text())
        else:
            overlap_rate = 0.25
        
        snrfalloff = 1.0
        deconvstrength = 1.0
        voltage = 300.0
        cs = 2.7

        params = {}
        params['tomogram_star'] = tomogram_star
        params['deconv_folder'] = deconv_folder
        params['tomo_idx'] = tomo_idx
        params['ncpu'] = ncpu
        params['highpassnyquist'] = highpassnyquist
        params['chunk_size'] = chunk_size
        params['overlap_rate'] = overlap_rate
        params['snrfalloff'] = snrfalloff
        params['deconvstrength'] = deconvstrength
        params['voltage'] = voltage
        params['cs'] = cs

        return params
    
    def deconvolve(self):
        params = self.get_deconv_params()
        if type(params) is str:
            self.logger.error(params)
        elif type(params) is dict:
            ret = QMessageBox.question(self, 'CTF Deconvolution!', \
                    "Perform CTF Deconvolution?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)   
            if ret == QMessageBox.Yes:
                
                tomogram_star = params['tomogram_star']
                deconv_folder = params['deconv_folder'] 
                tomo_idx = params['tomo_idx']
                ncpu = params['ncpu'] 
                highpassnyquist  = params['highpassnyquist']
                chunk_size = params['chunk_size']
                overlap_rate = params['overlap_rate'] 
                snrfalloff = params['snrfalloff'] 
                deconvstrength = params['deconvstrength'] 
                voltage = params['voltage'] 
                cs = params['cs'] 
                
                try:
                    md = MetaData()
                    md.read(tomogram_star)
                    if not 'rlnSnrFalloff' in md.getLabels():
                        md.addLabels('rlnSnrFalloff','rlnDeconvStrength','rlnDeconvTomoName')
                        for it in md:
                            md._setItemValue(it,Label('rlnSnrFalloff'),1.0)
                            md._setItemValue(it,Label('rlnDeconvStrength'),1.0)
                            md._setItemValue(it,Label('rlnDeconvTomoName'),None)

                    if not os.path.isdir(deconv_folder):
                        os.mkdir(deconv_folder)

                    tomo_idx = idx2list(tomo_idx)
                    for it in md:
                        if tomo_idx is None or str(it.rlnIndex) in tomo_idx:
                            if snrfalloff is not None:
                                md._setItemValue(it,Label('rlnSnrFalloff'), snrfalloff)
                            if deconvstrength is not None:
                                md._setItemValue(it,Label('rlnDeconvStrength'),deconvstrength)

                            tomo_file = it.rlnMicrographName
                            base_name = os.path.basename(tomo_file)
                            deconv_tomo_name = '{}/{}'.format(deconv_folder,base_name)

                            deconv_one(it.rlnMicrographName, deconv_tomo_name, self.isonet_folder, voltage=voltage, cs=cs, defocus=it.rlnDefocus/10000.0, \
                                    pixel_size=it.rlnPixelSize,snrfalloff=it.rlnSnrFalloff, deconvstrength=it.rlnDeconvStrength, \
                                        highpassnyquist=highpassnyquist, chunk_size=chunk_size, overlap_rate=overlap_rate, ncpu=ncpu)
                            md._setItemValue(it,Label('rlnDeconvTomoName'),deconv_tomo_name)
                        md.write(tomogram_star)
                    self.logger.info('\n######Isonet done ctf deconvolve######\n')

                except Exception:
                    error_text = traceback.format_exc()
                    f =open('log.txt','a+')
                    f.write(error_text)
                    f.close()
                    self.logger.error(error_text)
                
                self.updateMD()

    def cmd_finished(self, button, text="Run"):
        button.setText(text)
        button.setStyleSheet("QPushButton {color: black;}")
