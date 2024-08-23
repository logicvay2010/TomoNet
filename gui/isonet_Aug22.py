import logging
import os
import os.path
import glob
import shutil

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTabWidget, QMessageBox, QHeaderView, QTableWidgetItem, QInputDialog

from TomoNet.util.utils import check_log_file, getLogContent, string2float, string2int
from TomoNet.util import metadata
from TomoNet.util.metadata import MetaData, Label, Item
from TomoNet.process.bash_isonet_deconv import Deconvolve
from TomoNet.process.bash_isonet_generate_mask import MaskGeneration
from TomoNet.process.bash_isonet_extract_subtomos import ExtractSubtomos

class IsoNet(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="IsoNet/isonet.setting"
        
        self.log_file = "IsoNet/isonet.log"

        self.isonet_folder = "IsoNet"

        self.tomogram_star = "{}/{}".format(os.getcwd(), "IsoNet/tomograms.star")

        self.md = None

        self.pwd = os.getcwd().replace("\\","/")
        
        check_log_file(self.log_file, "IsoNet")

        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        self.table_header = []

        self.read_star()
        
        self.thread_deconvolve = None
        self.thread_generate_mask = None
        self.thread_subtomos = None

        self.fileSystemWatcher = QtCore.QFileSystemWatcher(self)
        self.fileSystemWatcher.addPath(self.log_file)
        self.fileSystemWatcher.fileChanged.connect(self.update_log_window)
        
        self.setupUi()        

        if os.path.exists(self.tomogram_star):
            self.read_star()
            self.setTableWidget(self.tableWidget, self.md)
            self.setTableWidget(self.tableWidget_2, self.md)
            self.logger.info("loading tomogram star file {}".format(self.tomogram_star))
        else:
            self.logger.warning("failed loading tomogram star file {}".format(self.tomogram_star))
            self.tomogram_star = "{}/{}".format(os.getcwd(), "IsoNet/tomograms.star")
            self.logger.info("loading default tomogram star file {}".format(self.tomogram_star))

    def setupUi(self):
        scriptDir = os.path.dirname(os.path.realpath(__file__))

        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.icon_trashCan = QtGui.QIcon()
        self.icon_trashCan.addPixmap(QtGui.QPixmap("{}/icons/trash_can.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.setUI_deconvolve()
        #self.setUI_tab2()
        
        self.addTab(self.tab, "CTF Deconvolve")

        self.setUI_preparation()
        self.addTab(self.tab_2, "Preparation")
        
        self.setTableWidget(self.tableWidget, self.md)

        self.setTableWidget(self.tableWidget_2, self.md)
        
        self.tableWidget.cellDoubleClicked[int, int].connect(self.browseSlotTable)
        self.tableWidget.cellChanged[int,int].connect(self.updateMDItem) 

        self.tableWidget_2.cellDoubleClicked[int, int].connect(self.browseSlotTable)
        self.tableWidget_2.cellChanged[int,int].connect(self.updateMDItem) 

        self.pushButton_insert.clicked.connect(self.copyRow)
        self.pushButton_delete.clicked.connect(self.removeRow)
        self.pushButton_generate_star.clicked.connect(self.new_star)
        self.pushButton_open_star.clicked.connect(self.open_star)
        self.pushButton_3dmod.clicked.connect(self.view_3dmod)

        self.pushButton_insert_2.clicked.connect(self.copyRow)
        self.pushButton_delete_2.clicked.connect(self.removeRow)
        self.pushButton_3dmod_2.clicked.connect(self.view_3dmod)
        
        self.pushButton_3dmod.clicked.connect(self.view_3dmod)
        
        for child in self.findChildren(QtWidgets.QLineEdit):
           child.textChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QCheckBox):
            child.stateChanged.connect(self.save_setting)

        self.pushButton_deconv.clicked.connect(self.deconvolve)
        self.pushButton_generate_mask.clicked.connect(self.generate_mask)
        self.pushButton_extract_subtomo.clicked.connect(self.extract_subtomos)

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        
        self.retranslateUi_deconvolve()
        self.retranslateUi_preparation()
        self.currentChanged.connect(self.tab_changed)
        self.read_settting()

    def setUI_deconvolve(self):
        #tab 1
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 5, 10, 5)

        self.tableWidget = QtWidgets.QTableWidget(self.tab)
        self.tableWidget.setMinimumSize(QtCore.QSize(0, 300))
        self.tableWidget.setMaximumSize(QtCore.QSize(16777215, 960))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.tableWidget.setFont(font)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)

        self.horizontalLayout_1.addWidget(self.tableWidget)

        self.verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_1.setObjectName("verticalLayout_1")
        
        self.pushButton_generate_star = QtWidgets.QPushButton(self.tab)
        self.pushButton_generate_star.setObjectName("pushButton_generate_star")
        self.verticalLayout_1.addWidget(self.pushButton_generate_star)

        self.pushButton_open_star = QtWidgets.QPushButton(self.tab)
        self.pushButton_open_star.setObjectName("pushButton_open_star")
        self.verticalLayout_1.addWidget(self.pushButton_open_star)
        
        self.pushButton_insert = QtWidgets.QPushButton(self.tab)
        self.pushButton_insert.setObjectName("pushButton_insert")
        self.verticalLayout_1.addWidget(self.pushButton_insert)
        
        self.pushButton_delete = QtWidgets.QPushButton(self.tab)
        self.pushButton_delete.setObjectName("pushButton_delete")
        self.verticalLayout_1.addWidget(self.pushButton_delete)
        
        self.pushButton_3dmod = QtWidgets.QPushButton(self.tab)
        self.pushButton_3dmod.setObjectName("pushButton_3dmod")
        self.verticalLayout_1.addWidget(self.pushButton_3dmod)
        
        self.horizontalLayout_1.addLayout(self.verticalLayout_1)

        self.gridLayout_deconvolve = QtWidgets.QGridLayout(self.tab)

        # group widget deconvolution
        self.groupBox_deconv = QtWidgets.QGroupBox(self.tab)
        self.groupBox_deconv.setMinimumSize(QtCore.QSize(0, 120))
        self.groupBox_deconv.setMaximumSize(QtCore.QSize(16777215, 180))
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
        
        self.label_deconv_dir = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_deconv_dir.setMinimumSize(QtCore.QSize(150, 0))
        self.label_deconv_dir.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_deconv_dir.setObjectName("label_deconv_dir")
        self.horizontalLayout_7.addWidget(self.label_deconv_dir)

        self.lineEdit_deconv_dir = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_deconv_dir.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_deconv_dir.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_deconv_dir.setObjectName("lineEdit_deconv_dir")
        self.horizontalLayout_7.addWidget(self.lineEdit_deconv_dir)
        
        self.label_voltage = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_voltage.setMinimumSize(QtCore.QSize(60, 0))
        self.label_voltage.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_voltage.setObjectName("label_voltage")
        self.horizontalLayout_7.addWidget(self.label_voltage)
        
        self.lineEdit_voltage = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_voltage.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_voltage.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_voltage.setObjectName("lineEdit_voltage")
        self.horizontalLayout_7.addWidget(self.lineEdit_voltage)
        
        self.label_cs = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_cs.setMinimumSize(QtCore.QSize(30, 0))
        self.label_cs.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_cs.setObjectName("label_cs")
        self.horizontalLayout_7.addWidget(self.label_cs)
        
        self.lineEdit_cs = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_cs.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_cs.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_cs.setObjectName("lineEdit_cs")
        self.horizontalLayout_7.addWidget(self.lineEdit_cs)
        
        self.label_tomo_index_deconv = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_tomo_index_deconv.setMinimumSize(QtCore.QSize(90, 0))
        self.label_tomo_index_deconv.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index_deconv.setObjectName("label_tomo_index_deconv")
        self.horizontalLayout_7.addWidget(self.label_tomo_index_deconv)
        
        self.lineEdit_tomo_index_deconv = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_tomo_index_deconv.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_tomo_index_deconv.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_tomo_index_deconv.setObjectName("lineEdit_tomo_index_deconv")
        self.horizontalLayout_7.addWidget(self.lineEdit_tomo_index_deconv)
        
        self.gridLayout_3.addLayout(self.horizontalLayout_7, 0, 0, 1, 1)
        
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        
        self.label_chunk_size = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_chunk_size.setMinimumSize(QtCore.QSize(80, 0))
        self.label_chunk_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_chunk_size.setObjectName("label_chunk_size")
        self.horizontalLayout_8.addWidget(self.label_chunk_size)
        
        self.lineEdit_chunk_size = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_chunk_size.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_chunk_size.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_chunk_size.setObjectName("lineEdit_chunk_size")
        self.horizontalLayout_8.addWidget(self.lineEdit_chunk_size)
                
        self.label_highpassnyquist = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_highpassnyquist.setMinimumSize(QtCore.QSize(140, 0))
        self.label_highpassnyquist.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_highpassnyquist.setObjectName("label_highpassnyquist")
        self.horizontalLayout_8.addWidget(self.label_highpassnyquist)
        
        self.lineEdit_highpassnyquist = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_highpassnyquist.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_highpassnyquist.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_highpassnyquist.setObjectName("lineEdit_highpassnyquist")
        self.horizontalLayout_8.addWidget(self.lineEdit_highpassnyquist)
        
        self.label_overlap = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_overlap.setMinimumSize(QtCore.QSize(100, 0))
        self.label_overlap.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_overlap.setObjectName("label_overlap")
        self.horizontalLayout_8.addWidget(self.label_overlap)
        
        self.lineEdit_overlap = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_overlap.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_overlap.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_overlap.setObjectName("lineEdit_overlap")
        self.horizontalLayout_8.addWidget(self.lineEdit_overlap)
        
        self.label_ncpu = QtWidgets.QLabel(self.groupBox_deconv)
        self.label_ncpu.setMinimumSize(QtCore.QSize(50, 0))
        self.label_ncpu.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_ncpu.setObjectName("label_ncpu")
        self.horizontalLayout_8.addWidget(self.label_ncpu)
        
        self.lineEdit_ncpu = QtWidgets.QLineEdit(self.groupBox_deconv)
        # self.lineEdit_ncpu.setMinimumSize(QtCore.QSize(60, 25))
        # self.lineEdit_ncpu.setMaximumSize(QtCore.QSize(120, 25))
        self.lineEdit_ncpu.setObjectName("lineEdit_ncpu")
        self.horizontalLayout_8.addWidget(self.lineEdit_ncpu)

        self.gridLayout_3.addLayout(self.horizontalLayout_8, 1, 0, 1, 1)

        self.gridLayout_deconvolve.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_deconvolve.addWidget(self.groupBox_deconv, 1, 0, 1, 1)
        # self.gridLayout_deconvolve.addLayout(self.horizontalLayout_1_2, 1, 0, 1, 1)
        # self.gridLayout_deconvolve.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)
        # self.gridLayout_deconvolve.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)
        # self.gridLayout_deconvolve.addWidget(self.groupBox_2, 4, 0, 1, 1)

        self.spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_deconvolve.addItem(self.spacerItem3, 2, 0, 1, 1)

        self.horizontalLayout_17 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_17.setObjectName("horizontalLayout_17")
        self.pushButton_deconv = QtWidgets.QPushButton(self.tab)
        self.pushButton_deconv.setEnabled(True)
        self.pushButton_deconv.setMinimumSize(QtCore.QSize(120, 48))
        self.pushButton_deconv.setMaximumSize(QtCore.QSize(120, 48))
        self.pushButton_deconv.setObjectName("run")
        self.horizontalLayout_17.addWidget(self.pushButton_deconv)
        
        self.gridLayout_deconvolve.addLayout(self.horizontalLayout_17, 3, 0, 1, 1)
    
    def setUI_preparation(self):
        
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab")

        self.gridLayout_preparation = QtWidgets.QGridLayout(self.tab_2)
        
        self.horizontalLayout_2_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_1.setContentsMargins(10, 5, 10, 5)
        
        self.tableWidget_2 = QtWidgets.QTableWidget(self.tab_2)
        self.tableWidget_2.setMinimumSize(QtCore.QSize(0, 280))
        self.tableWidget_2.setMaximumSize(QtCore.QSize(16777215, 600))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.tableWidget_2.setFont(font)
        self.tableWidget_2.setObjectName("tableWidget")
        self.tableWidget_2.setColumnCount(0)
        self.tableWidget_2.setRowCount(0)

        self.horizontalLayout_2_1.addWidget(self.tableWidget_2)

        self.verticalLayout_2_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2_1.setObjectName("verticalLayout_2_1")
        
        self.pushButton_insert_2 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_insert_2.setObjectName("pushButton_insert")
        self.verticalLayout_2_1.addWidget(self.pushButton_insert_2)
        
        self.pushButton_delete_2 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_delete_2.setObjectName("pushButton_delete")
        self.verticalLayout_2_1.addWidget(self.pushButton_delete_2)
        
        self.pushButton_3dmod_2 = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_3dmod_2.setObjectName("pushButton_3dmod")
        self.verticalLayout_2_1.addWidget(self.pushButton_3dmod_2)
        
        self.horizontalLayout_2_1.addLayout(self.verticalLayout_2_1)

        self.gridLayout_preparation.addLayout(self.horizontalLayout_2_1, 0, 0, 1, 1)

        self.groupBox_generate_mask = QtWidgets.QGroupBox(self.tab_2)
        self.groupBox_generate_mask.setMinimumSize(QtCore.QSize(0, 60))
        self.groupBox_generate_mask.setMaximumSize(QtCore.QSize(16777215, 80))
        self.groupBox_generate_mask.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_generate_mask.setFlat(False)
        self.groupBox_generate_mask.setObjectName("groupBox_generate_mask")
        
        self.horizontalLayout_2_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_7.setObjectName("horizontalLayout_2_7")
        
        self.label_mask_dir = QtWidgets.QLabel(self.groupBox_generate_mask)
        self.label_mask_dir.setMinimumSize(QtCore.QSize(120, 0))
        self.label_mask_dir.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_mask_dir.setObjectName("label_mask_dir")
        self.horizontalLayout_2_7.addWidget(self.label_mask_dir)
        
        self.lineEdit_mask_dir = QtWidgets.QLineEdit(self.groupBox_generate_mask)
        self.lineEdit_mask_dir.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_mask_dir.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_mask_dir.setObjectName("lineEdit_mask_dir")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_mask_dir)

        self.label_patch_size_mask = QtWidgets.QLabel(self.groupBox_generate_mask)
        self.label_patch_size_mask.setMinimumSize(QtCore.QSize(80, 0))
        self.label_patch_size_mask.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_patch_size_mask.setObjectName("label_patch_size_mask")
        self.horizontalLayout_2_7.addWidget(self.label_patch_size_mask)
        
        self.lineEdit_patch_size_mask = QtWidgets.QLineEdit(self.groupBox_generate_mask)
        self.lineEdit_patch_size_mask.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_patch_size_mask.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_patch_size_mask.setObjectName("lineEdit_patch_size_mask")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_patch_size_mask)

        self.label_zAxis_crop_mask = QtWidgets.QLabel(self.groupBox_generate_mask)
        self.label_zAxis_crop_mask.setMinimumSize(QtCore.QSize(80, 0))
        self.label_zAxis_crop_mask.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_zAxis_crop_mask.setObjectName("label_zAxis_crop_mask")
        self.horizontalLayout_2_7.addWidget(self.label_zAxis_crop_mask)
        
        self.lineEdit_zAxis_crop_mask = QtWidgets.QLineEdit(self.groupBox_generate_mask)
        self.lineEdit_zAxis_crop_mask.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_zAxis_crop_mask.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_zAxis_crop_mask.setObjectName("lineEdit_zAxis_crop_mask")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_zAxis_crop_mask)

        self.label_tomo_index_mask = QtWidgets.QLabel(self.groupBox_generate_mask)
        self.label_tomo_index_mask.setMinimumSize(QtCore.QSize(90, 0))
        self.label_tomo_index_mask.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index_mask.setObjectName("label_tomo_index_mask")
        self.horizontalLayout_2_7.addWidget(self.label_tomo_index_mask)
        
        self.lineEdit_tomo_index_mask = QtWidgets.QLineEdit(self.groupBox_generate_mask)
        self.lineEdit_tomo_index_mask.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_tomo_index_mask.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_tomo_index_mask.setObjectName("lineEdit_tomo_index_mask")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_tomo_index_mask)

        self.checkBox_use_deconv_mask = QtWidgets.QCheckBox(self.groupBox_generate_mask)
        self.checkBox_use_deconv_mask.setChecked(True)
        self.checkBox_use_deconv_mask.setObjectName("checkBox_use_deconv_mask")
        self.horizontalLayout_2_7.addWidget(self.checkBox_use_deconv_mask)
        
        self.groupBox_generate_mask.setLayout(self.horizontalLayout_2_7)

        self.gridLayout_preparation.addWidget(self.groupBox_generate_mask, 1, 0, 1, 1)

        self.groupBox_extract = QtWidgets.QGroupBox(self.tab_2)
        self.groupBox_extract.setMinimumSize(QtCore.QSize(0, 120))
        self.groupBox_extract.setMaximumSize(QtCore.QSize(16777215, 150))
        self.groupBox_extract.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_extract.setFlat(False)
        self.groupBox_extract.setObjectName("groupBox_extract")
        
        
        self.verticalLayout_2_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2_2.setObjectName("verticalLayout_2_2")

        self.horizontalLayout_2_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_7.setObjectName("horizontalLayout_2_7")
        
        self.label_subtomo_dir = QtWidgets.QLabel(self.groupBox_extract)
        self.label_subtomo_dir.setMinimumSize(QtCore.QSize(140, 0))
        self.label_subtomo_dir.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_subtomo_dir.setObjectName("label_subtomo_dir")
        self.horizontalLayout_2_7.addWidget(self.label_subtomo_dir)
        
        self.lineEdit_subtomo_dir = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_subtomo_dir.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_subtomo_dir.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_subtomo_dir.setObjectName("lineEdit_subtomo_dir")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_subtomo_dir)
                
        # self.label_subtomo_star_file = QtWidgets.QLabel(self.groupBox_extract)
        # self.label_subtomo_star_file.setMinimumSize(QtCore.QSize(100, 0))
        # self.label_subtomo_star_file.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        # self.label_subtomo_star_file.setObjectName("label_subtomo_star_file")
        # self.horizontalLayout_2_7.addWidget(self.label_subtomo_star_file)
        
        # self.lineEdit_subtomo_star_file = QtWidgets.QLineEdit(self.groupBox_extract)
        # self.lineEdit_subtomo_star_file.setMinimumSize(QtCore.QSize(100, 25))
        # self.lineEdit_subtomo_star_file.setMaximumSize(QtCore.QSize(16777215, 25))
        # self.lineEdit_subtomo_star_file.setObjectName("lineEdit_subtomo_star_file")
        # self.horizontalLayout_2_7.addWidget(self.lineEdit_subtomo_star_file)

        self.label_subtomo_cube_size = QtWidgets.QLabel(self.groupBox_extract)
        self.label_subtomo_cube_size.setMinimumSize(QtCore.QSize(70, 0))
        self.label_subtomo_cube_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_subtomo_cube_size.setObjectName("label_subtomo_cube_size")
        self.horizontalLayout_2_7.addWidget(self.label_subtomo_cube_size)
        
        self.lineEdit_subtomo_cube_size = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_subtomo_cube_size.setMinimumSize(QtCore.QSize(30, 25))
        self.lineEdit_subtomo_cube_size.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_subtomo_cube_size.setObjectName("lineEdit_subtomo_cube_size")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_subtomo_cube_size)

        self.checkBox_use_deconv_subtomo = QtWidgets.QCheckBox(self.groupBox_extract)
        self.checkBox_use_deconv_subtomo.setChecked(True)
        self.checkBox_use_deconv_subtomo.setObjectName("checkBox_use_deconv_subtomo")
        self.horizontalLayout_2_7.addWidget(self.checkBox_use_deconv_subtomo)
        
        self.verticalLayout_2_2.addLayout(self.horizontalLayout_2_7)

        self.horizontalLayout_2_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_8.setObjectName("horizontalLayout_2_8")
        
        self.label_tilt_range = QtWidgets.QLabel(self.groupBox_extract)
        self.label_tilt_range.setMinimumSize(QtCore.QSize(80, 0))
        self.label_tilt_range.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tilt_range.setObjectName("label_tilt_range")
        self.horizontalLayout_2_8.addWidget(self.label_tilt_range)
        
        self.lineEdit_tilt_range = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_tilt_range.setMinimumSize(QtCore.QSize(30, 25))
        self.lineEdit_tilt_range.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_tilt_range.setObjectName("lineEdit_tilt_range")
        self.horizontalLayout_2_8.addWidget(self.lineEdit_tilt_range)

        self.label_target_tilt_range = QtWidgets.QLabel(self.groupBox_extract)
        self.label_target_tilt_range.setMinimumSize(QtCore.QSize(140, 0))
        self.label_target_tilt_range.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_target_tilt_range.setObjectName("label_target_tilt_range")
        self.horizontalLayout_2_8.addWidget(self.label_target_tilt_range)
        
        self.lineEdit_target_tilt_range = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_target_tilt_range.setMinimumSize(QtCore.QSize(30, 25))
        self.lineEdit_target_tilt_range.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_target_tilt_range.setObjectName("lineEdit_target_tilt_range")
        self.horizontalLayout_2_8.addWidget(self.lineEdit_target_tilt_range)

        self.label_tomo_index_subtomo_plus = QtWidgets.QLabel(self.groupBox_extract)
        self.label_tomo_index_subtomo_plus.setMinimumSize(QtCore.QSize(120, 0))
        self.label_tomo_index_subtomo_plus.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index_subtomo_plus.setObjectName("label_tomo_index_subtomo_plus")
        self.horizontalLayout_2_8.addWidget(self.label_tomo_index_subtomo_plus)
        
        self.lineEdit_tomo_index_subtomo_plus = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_tomo_index_subtomo_plus.setMinimumSize(QtCore.QSize(30, 25))
        self.lineEdit_tomo_index_subtomo_plus.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_tomo_index_subtomo_plus.setObjectName("lineEdit_tomo_index_subtomo_plus")
        self.horizontalLayout_2_8.addWidget(self.lineEdit_tomo_index_subtomo_plus)

        self.label_tomo_index_subtomo_minus = QtWidgets.QLabel(self.groupBox_extract)
        self.label_tomo_index_subtomo_minus.setMinimumSize(QtCore.QSize(120, 0))
        self.label_tomo_index_subtomo_minus.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index_subtomo_minus.setObjectName("label_tomo_index_subtomo_minus")
        self.horizontalLayout_2_8.addWidget(self.label_tomo_index_subtomo_minus)
        
        self.lineEdit_tomo_index_subtomo_minus = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_tomo_index_subtomo_minus.setMinimumSize(QtCore.QSize(30, 25))
        self.lineEdit_tomo_index_subtomo_minus.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_tomo_index_subtomo_minus.setObjectName("lineEdit_tomo_index_subtomo_minus")
        self.horizontalLayout_2_8.addWidget(self.lineEdit_tomo_index_subtomo_minus)

        self.verticalLayout_2_2.addLayout(self.horizontalLayout_2_8)

        self.groupBox_extract.setLayout(self.verticalLayout_2_2)

        self.gridLayout_preparation.addWidget(self.groupBox_extract, 2, 0, 1, 1)

        self.spacerItem2_3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_preparation.addItem(self.spacerItem2_3, 3, 0, 1, 1)

        self.horizontalLayout_2_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_2.setObjectName("horizontalLayout_2_2")
        self.pushButton_generate_mask = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_generate_mask.setEnabled(True)
        self.pushButton_generate_mask.setMinimumSize(QtCore.QSize(160, 48))
        self.pushButton_generate_mask.setMaximumSize(QtCore.QSize(160, 48))
        self.pushButton_generate_mask.setObjectName("run")
        self.horizontalLayout_2_2.addWidget(self.pushButton_generate_mask)

        self.pushButton_extract_subtomo = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_extract_subtomo.setEnabled(True)
        self.pushButton_extract_subtomo.setMinimumSize(QtCore.QSize(170, 48))
        self.pushButton_extract_subtomo.setMaximumSize(QtCore.QSize(170, 48))
        self.pushButton_extract_subtomo.setObjectName("run")
        self.horizontalLayout_2_2.addWidget(self.pushButton_extract_subtomo)
        
        self.gridLayout_preparation.addLayout(self.horizontalLayout_2_2, 4, 0, 1, 1)
       
    def retranslateUi_deconvolve(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.pushButton_generate_star.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Generate a new star file containing tomograms from a folder.</span></p></body></html>"))
        self.pushButton_generate_star.setText(_translate("Form", "New STAR file"))
        self.pushButton_open_star.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Open a saved star file.</span></p></body></html>"))
        self.pushButton_open_star.setText(_translate("Form", "Open STAR file"))
        self.pushButton_insert.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Add new items to the star file.</span></p></body></html>"))
        self.pushButton_insert.setText(_translate("Form", "Insert Row(s)"))
        self.pushButton_delete.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Delete items from the star file</span></p></body></html>"))
        self.pushButton_delete.setText(_translate("Form", "Delete Row(s)"))
        self.pushButton_3dmod.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">open selected maps in 3dmod view.</span></p></body></html>"))
        self.pushButton_3dmod.setText(_translate("Form", "3dmod view"))

        self.groupBox_deconv.setTitle(_translate("Form", "Settings"))
        self.label_deconv_dir.setText(_translate("Form", "deconvolve directory"))
        self.lineEdit_deconv_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">a folder path to save your deconvolved maps.</span></p><p><span style=\" font-size:9pt;\"><br/></span></p></body></html>"))
        self.lineEdit_deconv_dir.setPlaceholderText(_translate("Form", "deconv"))
        self.label_tomo_index_deconv.setText(_translate("Form", "tomo index"))
        self.lineEdit_tomo_index_deconv.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If this value is set, process only the tomograms listed in this index. e.g. 1,2,3,4</span></p></body></html>"))

        self.label_chunk_size.setText(_translate("Form", "chunk size"))
        self.lineEdit_chunk_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">(None) When your computer has enough memory, please keep the chunk_size as the default value: None . Otherwise, you can let the program crop the tomogram into multiple chunks for multiprocessing and assembly them into one. The chunk_size defines the size of individual chunk. This option may induce artifacts along edges of chunks. When that happen, you may use larger overlap_rate.</span></p></body></html>"))
        self.lineEdit_chunk_size.setPlaceholderText(_translate("Form", "None"))
        self.label_highpassnyquist.setText(_translate("Form", "high pass nyquist"))
        self.lineEdit_highpassnyquist.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">(0.02) Highpass filter at very low resolution.</span></p></body></html>"))
        self.lineEdit_highpassnyquist.setPlaceholderText(_translate("Form", "0.02"))
        self.label_overlap.setText(_translate("Form", "overlap ratio"))
        self.lineEdit_overlap.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The overlapping rate for adjecent tiles.</span></p></body></html>"))
        self.lineEdit_overlap.setPlaceholderText(_translate("Form", "0.25"))

        self.label_ncpu.setText(_translate("Form", "ncpu"))
        self.lineEdit_ncpu.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">number of gpu to use in deconvolve</span></p></body></html>"))
        self.lineEdit_ncpu.setPlaceholderText(_translate("Form", "4"))

        self.label_voltage.setText(_translate("Form", "voltage"))
        self.lineEdit_voltage.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">voltage</span></p></body></html>"))
        self.lineEdit_voltage.setPlaceholderText(_translate("Form", "300"))

        self.label_cs.setText(_translate("Form", "CS"))
        self.lineEdit_cs.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">spherical aberration coefficient </span></p></body></html>"))
        self.lineEdit_cs.setPlaceholderText(_translate("Form", "2.7"))

        self.pushButton_deconv.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">click to run isonet deconvolve</span></p></body></html>"))
        self.pushButton_deconv.setText(_translate("Form", "Deconvolve"))

    def retranslateUi_preparation(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.pushButton_insert_2.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Add new items to the star file.</span></p></body></html>"))
        self.pushButton_insert_2.setText(_translate("Form", "Insert Row(s)"))
        self.pushButton_delete_2.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Delete items from the star file</span></p></body></html>"))
        self.pushButton_delete_2.setText(_translate("Form", "Delete Row(s)"))
        self.pushButton_3dmod_2.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">open selected maps in 3dmod view.</span></p></body></html>"))
        self.pushButton_3dmod_2.setText(_translate("Form", "3dmod view"))

        self.pushButton_generate_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">click to run isonet mask generation</span></p></body></html>"))
        self.pushButton_generate_mask.setText(_translate("Form", "Generate Mask"))

        self.pushButton_extract_subtomo.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">click to run isonet subtomo extraction which will be used for neural network training</span></p></body></html>"))
        self.pushButton_extract_subtomo.setText(_translate("Form", "Extract Subtomos"))
        
        self.groupBox_generate_mask.setTitle(_translate("Form", "Generate Mask Settings"))

        self.label_patch_size_mask.setText(_translate("Form", "patch size"))
        self.lineEdit_patch_size_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The size of the box from which the max-filter and std-filter are calculated.</span></p></body></html>"))
        self.lineEdit_patch_size_mask.setPlaceholderText(_translate("Form", "4"))
        self.label_zAxis_crop_mask.setText(_translate("Form", "z axis crop"))
        self.lineEdit_zAxis_crop_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If exclude the top and bottom regions of tomograms along z axis. For example, &quot;--z_crop 0.2&quot; will mask out the top 20% and bottom 20% region along z axis.</span></p></body></html>"))
        self.lineEdit_zAxis_crop_mask.setPlaceholderText(_translate("Form", "0"))
        self.label_mask_dir.setText(_translate("Form", "mask directory"))
        self.lineEdit_mask_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">a folder path to save your mask for each tomograms.</span></p><p><br/></p></body></html>"))
        self.lineEdit_mask_dir.setPlaceholderText(_translate("Form", "mask"))
        self.label_tomo_index_mask.setText(_translate("Form", "tomo index"))
        self.lineEdit_tomo_index_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If this value is set, process only the tomograms listed in this index. </span></p></body></html>"))
        self.checkBox_use_deconv_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If CTF deconvolved tomogram is found in tomogram.star, use that tomogram instead.</span></p></body></html>"))
        self.checkBox_use_deconv_mask.setText(_translate("Form", "use deconv map"))

        self.groupBox_extract.setTitle(_translate("Form", "Extract Subtomograms Settings"))
        self.label_subtomo_dir.setText(_translate("Form", "subtomo directory"))
        self.lineEdit_subtomo_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">a folder path to save your mask for each tomograms.</span></p><p><br/></p></body></html>"))
        self.lineEdit_subtomo_dir.setPlaceholderText(_translate("Form", "subtomo"))
        #self.label_subtomo_star_file.setText(_translate("Form", "subtomo star"))
        # self.lineEdit_subtomo_star_file.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">(subtomo.star) star file for output subtomograms.</span></p></body></html>"))
        # self.lineEdit_subtomo_star_file.setPlaceholderText(_translate("Form", "subtomo.star"))
        self.checkBox_use_deconv_subtomo.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If CTF deconvolved tomogram is found in tomogram.star, use that tomogram instead.</span></p></body></html>"))
        self.checkBox_use_deconv_subtomo.setText(_translate("Form", "use deconv map"))
        self.label_subtomo_cube_size.setText(_translate("Form", "cube size"))
        self.lineEdit_subtomo_cube_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Size of cubes for training, should be divisible by 8, eg. 32, 64. The actual sizes of extracted subtomograms are this value add 16.</span></p></body></html>"))
        self.lineEdit_subtomo_cube_size.setPlaceholderText(_translate("Form", "64"))
        self.label_tomo_index_subtomo_plus.setText(_translate("Form", "tomo index (+)"))
        self.lineEdit_tomo_index_subtomo_plus.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Mandatory, tomograms used to train the plus part. </span></p></body></html>"))
        self.label_tomo_index_subtomo_minus.setText(_translate("Form", "tomo index (-)"))
        self.lineEdit_tomo_index_subtomo_minus.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Mandatory, tomograms used to train the minus part. </span></p></body></html>"))
        
        self.label_tilt_range.setText(_translate("Form", "tilt range"))
        self.lineEdit_tilt_range.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Tilt range of the tilt series.</span></p></body></html>"))
        self.lineEdit_tilt_range.setPlaceholderText(_translate("Form", "-60,60"))
        self.label_target_tilt_range.setText(_translate("Form", "target tilt range"))
        self.lineEdit_target_tilt_range.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Target tilt range for Network training.</span></p></body></html>"))
        self.lineEdit_target_tilt_range.setPlaceholderText(_translate("Form", "-90,90"))

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
        data['tomogram_starfile'] = "{}/{}".format(os.getcwd(), "IsoNet/tomograms.star")
        data['deconv_dir'] = ""
        data['tomo_index_deconv'] = ""
        data['ncpu'] = ""
        data['chunk_size'] = ""
        data['highpassnyquist'] = ""
        data['overlap'] = ""
        data['voltage'] = ""
        data['cs'] = ""

        data['mask_dir'] = ""
        data['patch_size_mask'] = ""
        data['tomo_index_mask'] = ""
        data['zAxis_crop_mask'] = ""
        data['use_deconv_mask'] = True
        
        data['subtomo_dir'] = ""
        #data['subtomo_star_file'] = ""
        data['subtomo_cube_size'] = ""
        data['tomo_index_subtomo_minus'] = ""
        data['tomo_index_subtomo_plus'] = ""
        data['use_deconv_subtomo'] = True
        data['tilt_range'] = ""
        data['target_tilt_range'] = ""

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
        self.tomogram_star = data['tomogram_starfile']
        self.lineEdit_deconv_dir.setText(data['deconv_dir'])
        self.lineEdit_tomo_index_deconv.setText(data['tomo_index_deconv'])
        self.lineEdit_ncpu.setText(data['ncpu'])
        self.lineEdit_chunk_size.setText(data['chunk_size'])
        self.lineEdit_highpassnyquist.setText(data['highpassnyquist'])
        self.lineEdit_overlap.setText(data['overlap'])
        self.lineEdit_voltage.setText(data['voltage'])
        self.lineEdit_cs.setText(data['cs'])


        self.lineEdit_mask_dir.setText(data['mask_dir'])
        self.lineEdit_patch_size_mask.setText(data['patch_size_mask'])
        self.lineEdit_tomo_index_mask.setText(data['tomo_index_mask'])
        self.lineEdit_zAxis_crop_mask.setText(data['zAxis_crop_mask'])
        self.checkBox_use_deconv_mask.setChecked(data['use_deconv_mask'])
        
        self.lineEdit_subtomo_dir.setText(data['subtomo_dir'])
        #self.lineEdit_subtomo_star_file.setText(data['subtomo_star_file'])
        self.lineEdit_subtomo_cube_size.setText(data['subtomo_cube_size'])
        self.lineEdit_tomo_index_subtomo_minus.setText(data['tomo_index_subtomo_minus'])
        self.lineEdit_tomo_index_subtomo_plus.setText(data['tomo_index_subtomo_plus'])
        self.checkBox_use_deconv_subtomo.setChecked(data['use_deconv_subtomo'])
        self.lineEdit_tilt_range.setText(data['tilt_range'])
        self.lineEdit_target_tilt_range.setText(data['target_tilt_range'])
    
    def save_setting(self):
        param = {}
        param['tomogram_starfile'] = self.tomogram_star
        param['deconv_dir'] = self.lineEdit_deconv_dir.text()
        param['tomo_index_deconv'] = self.lineEdit_tomo_index_deconv.text()
        param['ncpu'] = self.lineEdit_ncpu.text()
        param['chunk_size'] = self.lineEdit_chunk_size.text()
        param['highpassnyquist'] = self.lineEdit_highpassnyquist.text()
        param['overlap'] = self.lineEdit_overlap.text()
        param['voltage'] = self.lineEdit_voltage.text()
        param['cs'] = self.lineEdit_cs.text()

        param['mask_dir'] = self.lineEdit_mask_dir.text()
        param['patch_size_mask'] = self.lineEdit_patch_size_mask.text()
        param['zAxis_crop_mask'] = self.lineEdit_zAxis_crop_mask.text()
        param['tomo_index_mask'] = self.lineEdit_tomo_index_mask.text()
        param['use_deconv_mask'] = self.checkBox_use_deconv_mask.isChecked()
        
        param['subtomo_dir'] = self.lineEdit_subtomo_dir.text()
        #param['subtomo_star_file'] = self.lineEdit_subtomo_star_file.text()
        param['subtomo_cube_size'] = self.lineEdit_subtomo_cube_size.text()
        param['tomo_index_subtomo_minus'] = self.lineEdit_tomo_index_subtomo_minus.text()
        param['tomo_index_subtomo_plus'] = self.lineEdit_tomo_index_subtomo_plus.text()
        param['use_deconv_subtomo'] = self.checkBox_use_deconv_subtomo.isChecked()
        param['tilt_range'] = self.lineEdit_tilt_range.text()
        param['target_tilt_range'] = self.lineEdit_target_tilt_range.text()

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
            simple_name = self.model.sim_path(pwd, fileName)
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
        current_tab_index = self.currentIndex()
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
                    if current_tab_index == 0:
                        fileName = self.tableWidget.item(i, j).text()
                    elif current_tab_index == 1:
                        fileName = self.tableWidget_2.item(i, j).text()
                    else:
                        return
                #pwd = os.getcwd().replace("\\","/")
                simple_path = self.sim_path(self.pwd, fileName)
                self.tableWidget.setItem(i, j, QTableWidgetItem(simple_path))
                self.tableWidget_2.setItem(i, j, QTableWidgetItem(simple_path))
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
    
    def updateMD(self, table_index=0):        
        star_file = self.tomogram_star
        if table_index == 1:
            current_table = self.tableWidget_2
        else:
            current_table = self.tableWidget
        
        rowCount = current_table.rowCount()
        columnCount = current_table.columnCount()
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
                    #if len(self.tableWidget.item(i, j).text()) < 1:
                    if len(current_table.item(i, j).text()) < 1:

                        if self.table_header[j+1] != "rlnMaskBoundary":
                            previous_value = getattr(data[i], self.table_header[j+1])
                        else:
                            previous_value = "None"

                        self.md._setItemValue(it, Label(self.table_header[j+1]), previous_value)
                        self.tableWidget.setItem(i, j, QTableWidgetItem(str(previous_value)))
                        self.tableWidget_2.setItem(i, j, QTableWidgetItem(str(previous_value)))
                    else:
                        self.md._setItemValue(it, Label(self.table_header[j+1]), current_table.item(i, j).text())
                except:
                    previous_value = getattr(data[i], self.table_header[j+1])
                    self.md._setItemValue(it, Label(self.table_header[j+1]), previous_value)
                    self.tableWidget.setItem(i, j, QTableWidgetItem(str(previous_value)))
                    self.tableWidget_2.setItem(i, j, QTableWidgetItem(str(previous_value)))
                    #print("error in seeting values for {}! set it to previous value automatically.".format(self.tableWidget.horizontalHeaderItem(j).text()))
        self.md.write(star_file)

    def tab_changed(self, table_index):
        if table_index == 0:
            self.setTableWidget(self.tableWidget, self.md)
        if table_index == 1:
            self.setTableWidget(self.tableWidget_2, self.md)

    def updateMDItem(self, i, j):
        try:
            #current_value = self.tableWidget.item(i, j).text()
            current_tab_index = self.currentIndex()
            self.updateMD(table_index=current_tab_index)
        except:
            pass
    
    def copyRow(self):
        tw_index = self.currentIndex()
        if tw_index == 0:
            current_tw = self.tableWidget
        elif tw_index == 1:
            current_tw = self.tableWidget_2
        else:
            return
        
        rowCount = current_tw.rowCount()
        columnCount = current_tw.columnCount()
        if rowCount <=0 :
            current_tw.insertRow(current_tw.rowCount())
            for j in range(columnCount):
                #self.model.md._setItemValue(it,Label(self.table_header[j+1]),current_tw.item(i, j).text())
                #print(self.default_value(self.table_header[j+1]))
                current_tw.setItem(0, j, QTableWidgetItem(self.default_value(self.table_header[j+1])))
                #print(current_tw.item(0, j).text())
        else:
            indices = current_tw.selectionModel().selectedRows() 

            if indices:
                for index in sorted(indices):
                    current_tw.insertRow(current_tw.rowCount())
                    rowCount = current_tw.rowCount()
                    for j in range(columnCount):
                        if self.table_header[j+1] in ["rlnDeconvTomoName","rlnMaskName","rlnCorrectedTomoName","rlnMaskBoundary"]:
                            current_tw.setItem(rowCount-1, j, QTableWidgetItem("None"))
                        #current_tw.cellChanged[rowCount-1, j].connect(self.updateMD)  
                        else:
                            current_tw.setItem(rowCount-1, j, QTableWidgetItem(current_tw.item(index.row(), j).text()))
            else:
                current_tw.insertRow(current_tw.rowCount())
                rowCount = current_tw.rowCount()
                for j in range(columnCount):
                    if self.table_header[j+1] in ["rlnDeconvTomoName","rlnMaskName","rlnCorrectedTomoName","rlnMaskBoundary"]:
                            current_tw.setItem(rowCount-1, j, QTableWidgetItem("None"))
                    elif not current_tw.item(rowCount-2, j) is None:
                        current_tw.setItem(rowCount-1, j, QTableWidgetItem(current_tw.item(rowCount-2, j).text()))
        
        # tw_index = self.currentIndex()
        self.updateMD(table_index=tw_index)
        #self.updateMD(table_index=1-tw_index)
        # self.updateMD()
        # if tw_index == 1:
        #     self.updateMD(table_index=1)
        self.save_setting()
    
    def removeRow(self):
        tw_index = self.currentIndex()
        if tw_index == 0:
            current_tw = self.tableWidget
        elif tw_index == 1:
            current_tw = self.tableWidget_2
        else:
            return
        indices = current_tw.selectionModel().selectedRows() 
        if indices:
            for index in sorted(indices,reverse=True):
                current_tw.removeRow(index.row()) 
        
        #self.updateMD(table_index=tw_index)

        self.updateMD(table_index=tw_index)
        #self.updateMD(table_index=1-tw_index)
        self.save_setting()

    def new_star(self):
        pwd = os.getcwd().replace("\\","/") 
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Choose Directory", pwd)
        try:
            md = MetaData()
            md.addLabels('rlnIndex','rlnMicrographName','rlnPixelSize','rlnDefocus','rlnNumberSubtomo','rlnMaskBoundary')
            try:
                tomo_list = sorted(os.listdir(dir_path))
            except:
                self.logger("error reading folder {}".format(dir_path))
                return 1
            i = 0
            for tomo in tomo_list:
                if tomo[-4:] == '.rec' or tomo[-4:] == '.mrc':
                    i+=1
                    continue
            if i < 1:
                self.logger.warning("No .rec or .mrc files detected in folder {}".format(dir_path))
                return

            output_star = "tomograms.star"
            text, ok = QInputDialog().getText(self, "output star filename",
                                     "output star filename:", text="tomograms.star")
            if ok and text:
                output_star = "{}/{}".format(self.isonet_folder, text)
            else:
                return
            
            if os.path.exists(output_star):
                ret = QMessageBox.question(self, 'Overwrite warning!', \
                        "Continue Overwrite existing file {}?\n".format(output_star)\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)   
                if not ret == QMessageBox.Yes:
                    return
                
            pixel_size = 1.0

            text, ok = QInputDialog().getText(self, "Positive float number",
                                     "Map Pixel Size:", text="1.0")
            if ok :
                if string2float(text) and string2float(text) > 0:
                    pixel_size = string2float(text)
                else:
                    pixel_size = 1.0
                    self.logger.warning("wrong format for pixel size {}, the default value 1.0 is used.".format(text))
            else:
                return
            
            defocus = 3.0
            text, ok = QInputDialog().getText(self, "Positive float number",
                                     "Defocus (µm):", text="3.0")
            if ok :
                if string2float(text, 6) and string2float(text, 6) > 0:
                    defocus = string2float(text, 6)*1e4
                else:
                    defocus = 3.0*1e4
                    self.logger.warning("wrong format for defocus {}, the default value 3.0 µm is used.".format(text))
            else:
                return
            
            subtomo_num = 100
            text, ok = QInputDialog().getText(self, "Positive int number",
                                     "subtomos #:", text="100")
            if ok :
                if string2int(text) and string2int(text) > 0:
                    subtomo_num = string2int(text)
                else:
                    subtomo_num = 100
                    self.logger.warning("wrong format for subtomos # {}, the default value 100 is used.".format(text))
            else:
                return
            
            i = 0
            for tomo in tomo_list:
                if tomo[-4:] == '.rec' or tomo[-4:] == '.mrc':
                    i+=1
                    it = Item()
                    md.addItem(it)
                    md._setItemValue(it,Label('rlnIndex'),str(i))
                    md._setItemValue(it,Label('rlnMicrographName'), self.sim_path(pwd, os.path.join(dir_path, tomo)))
                    md._setItemValue(it,Label('rlnPixelSize'), pixel_size)
                    md._setItemValue(it,Label('rlnDefocus'), defocus)
                    md._setItemValue(it,Label('rlnNumberSubtomo'), subtomo_num)
                    md._setItemValue(it,Label('rlnMaskBoundary'),None)
            
            md.write(output_star)
            self.open_star_fileName(output_star)
            self.logger.info("{} is gernerated and loaded.".format(output_star))
            self.save_setting()
        except:
            ##TODO: record to log.
            self.logger.info("error generate new star file")
            pass
    
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
                #tomo_file = self.sim_path(self.pwd, fileName)
                tomo_file = fileName
                read_result = self.read_star_gui(tomo_file)
                if read_result == 1:
                    self.warn_window("The input star file is not legid!")
                else:
                    self.setTableWidget(self.tableWidget, self.md)
                    self.setTableWidget(self.tableWidget_2, self.md)
            except:
                self.logger.error("The input star file {} is not legid!".format(fileName))
                pass
        self.save_setting()

    def open_star_fileName(self, fileName):
        try:
            #tomo_file = self.sim_path(self.pwd, fileName)
            tomo_file = fileName
            read_result = self.read_star_gui(tomo_file)
            if read_result == 1:
                self.logger.error("The input star file {} is not legid!".format(tomo_file))
            else:
                if self.currentIndex() == 0:
                    self.setTableWidget(self.tableWidget, self.md)
                    self.setTableWidget(self.tableWidget_2, self.md)
                else:
                    self.setTableWidget(self.tableWidget_2, self.md)
                    self.setTableWidget(self.tableWidget, self.md)
            self.save_setting()
        except:
            self.logger.error("cannot read file {}".format(fileName))
            pass

    def view_3dmod(self):
        tw_index = self.currentIndex()
        if tw_index == 1:
            slected_items = self.tableWidget_2.selectedItems()
        else:
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
                if tw_index == 1:
                    item_text = self.tableWidget_2.item(i, j).text()
                else:
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
            #return "Please define tomo index for Ctf deconvolution."
            tomo_idx = None
        
        if self.lineEdit_ncpu.text():
            if not string2int(self.lineEdit_ncpu.text()) == None:
                ncpu = string2int(self.lineEdit_ncpu.text())
                if ncpu < 1:
                    return "Please use the valid format for the ncpu #!"
            else:
                return "Please use the valid format for the ncpu #!"
        else:
            ncpu = 6

        if self.lineEdit_highpassnyquist.text():
            if not string2float(self.lineEdit_highpassnyquist.text()) == None:
                highpassnyquist = string2float(self.lineEdit_highpassnyquist.text())
                if not highpassnyquist > 0:
                    return "Please use the valid format for the high pass nyquist!"
            else:
                return "Please use the valid format for the high pass nyquist!"
        else:
            highpassnyquist = 0.02
        
        if self.lineEdit_chunk_size.text():
            if not string2int(self.lineEdit_chunk_size.text()) == None:
                chunk_size = string2int(self.lineEdit_chunk_size.text())
                if not chunk_size > 0:
                    return "Please use the valid format for the chunk size!"
            else:
                return "Please use the valid format for the chunk size!"
        else:
            chunk_size = 200
        
        if self.lineEdit_overlap.text():
            if not string2float(self.lineEdit_overlap_rate.text()) == None:
                overlap_rate = string2float(self.lineEdit_overlap_rate.text())
                if not (overlap_rate >= 0 and overlap_rate <= 1 ):
                    return "Please use the valid format for the overlap rate!"
            else:
                return "Please use the valid format for the overlap rate!"
        else:
            overlap_rate = 0.25
        
        if self.lineEdit_voltage.text():
            if not string2float(self.lineEdit_voltage.text()) == None:
                voltage = string2float(self.lineEdit_voltage.text())
                if not voltage > 0:
                    return "Please use the valid format for the voltage!"
            else:
                return "Please use the valid format for the voltage!"
        else:
            voltage = 300.0

        if self.lineEdit_cs.text():
            if not string2float(self.lineEdit_cs.text()) == None:
                cs = string2float(self.lineEdit_cs.text())
                if not cs > 0:
                    return "Please use the valid format for the cs!"
            else:
                return "Please use the valid format for the cs!"
        else:
            cs = 2.7

        params = {}
        params['tomogram_star'] = tomogram_star
        params['deconv_folder'] = deconv_folder
        params['tomo_idx'] = tomo_idx
        params['ncpu'] = ncpu
        params['highpassnyquist'] = highpassnyquist
        params['chunk_size'] = chunk_size
        params['overlap_rate'] = overlap_rate

        params['voltage'] = voltage
        params['cs'] = cs
        return params
    
    def deconvolve(self):
        params = self.get_deconv_params()
        if type(params) is str:
            QMessageBox.warning(self, 'Error!', \
                "Error! {}"\
                .format(params))
            self.cmd_finished(button=self.pushButton_deconv, text="Deconvolve")
        elif type(params) is dict:
            if self.pushButton_deconv.text() == "Deconvolve":
                ret = QMessageBox.question(self, 'CTF Deconvolution!', \
                        "Perform CTF Deconvolution?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)   
                if ret == QMessageBox.Yes:
                    
                    self.pushButton_deconv.setText("STOP")
                    
                    self.pushButton_deconv.setStyleSheet('QPushButton {color: red;}')

                    self.thread_deconvolve = Deconvolve(params)                

                    self.thread_deconvolve.finished.connect(lambda: self.cmd_finished(self.pushButton_deconv, "Deconvolve"))
                    
                    self.thread_deconvolve.start()
                else:
                    self.cmd_finished(button=self.pushButton_deconv, text="Deconvolve")
            else:
                ret = QMessageBox.question(self, 'Warning!', \
                    "Stop Ctf Deconvolution! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.pushButton_deconv.setText("Deconvolve")
                    self.pushButton_deconv.setStyleSheet("QPushButton {color: black;}")
                    self.thread_deconvolve.stop_process()
                    self.open_star_fileName(self.tomogram_star)
    
    def get_generate_mask_params(self):
        
        tomogram_star = self.tomogram_star

        if self.lineEdit_mask_dir.text():
            mask_folder = "{}/{}".format(self.isonet_folder, self.lineEdit_mask_dir.text())
        else:
            mask_folder = "{}/{}".format(self.isonet_folder, "mask")
        
        if self.lineEdit_patch_size_mask.text():
            if not string2int(self.lineEdit_patch_size_mask.text()) == None:
                patch_size_mask = string2int(self.lineEdit_patch_size_mask.text())
                if not patch_size_mask > 0:
                    return "Please use the valid format for the patch size!"
            else:
                return "Please use the valid format for the patch size!"
        else:
            patch_size_mask = 4

        if self.lineEdit_zAxis_crop_mask.text():
            if not string2float(self.lineEdit_zAxis_crop_mask.text()) == None:
                zAxis_crop_mask = string2float(self.lineEdit_zAxis_crop_mask.text())
                if not (zAxis_crop_mask >= 0 and zAxis_crop_mask < 1):
                    return "Please use the valid format for the z axis crop ratio!"
            else:
                return "Please use the valid format for the z axis crop ratio!"
        else:
            zAxis_crop_mask = 0

        if self.lineEdit_tomo_index_mask.text():
            tomo_idx = self.lineEdit_tomo_index_mask.text()
        else:
            tomo_idx = None

        params = {}
        params['tomogram_star'] = tomogram_star
        params['mask_folder'] = mask_folder
        params['tomo_idx'] = tomo_idx
        params['patch_size_mask'] = patch_size_mask
        params['zAxis_crop_mask'] = zAxis_crop_mask
        params['use_deconv_mask'] = 1 if self.checkBox_use_deconv_mask.isChecked() else 0

        return params
    
    def generate_mask(self):
        params = self.get_generate_mask_params()
        
        if type(params) is str:
            QMessageBox.warning(self, 'Error!', \
                "Error! {}"\
                .format(params))
            self.cmd_finished(button=self.pushButton_generate_mask, text="Generate Mask")
        elif type(params) is dict:
            if self.pushButton_generate_mask.text() == "Generate Mask":
                ret = QMessageBox.question(self, 'Generate Mask!', \
                        "Perform Generate Mask?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)   
                if ret == QMessageBox.Yes:
                    
                    self.pushButton_generate_mask.setText("STOP")
                    
                    self.pushButton_generate_mask.setStyleSheet('QPushButton {color: red;}')

                    self.thread_generate_mask = MaskGeneration(params)                

                    self.thread_generate_mask.finished.connect(lambda: self.cmd_finished(self.pushButton_generate_mask, "Generate Mask"))
                    
                    self.thread_generate_mask.start()
                else:
                    self.cmd_finished(button=self.pushButton_generate_mask, text="Generate Mask")
            else:
                ret = QMessageBox.question(self, 'Warning!', \
                    "Stop Generate Mask! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.pushButton_generate_mask.setText("Generate Mask")
                    self.pushButton_generate_mask.setStyleSheet("QPushButton {color: black;}")
                    self.thread_generate_mask.stop_process()
                    self.open_star_fileName(self.tomogram_star)
    
    def get_extract_subtomos_params(self):
        param = {}
        
        tomogram_star = self.tomogram_star

        if self.lineEdit_subtomo_dir.text():
            subtomo_dir = "{}/{}".format(self.isonet_folder, self.lineEdit_subtomo_dir.text())
        else:
            subtomo_dir = "{}/{}".format(self.isonet_folder, "subtomos")
        
        if self.lineEdit_subtomo_cube_size.text():
            if not string2int(self.lineEdit_subtomo_cube_size.text()) == None:
                subtomo_cube_size = string2int(self.lineEdit_subtomo_cube_size.text())
                if not subtomo_cube_size > 0:
                    return "Please use the valid format for the patch size!"
            else:
                return "Please use the valid format for the patch size!"
        else:
            subtomo_cube_size = 64

        if self.lineEdit_tilt_range.text():
            line = self.lineEdit_tilt_range.text()
            try:
                split = line.split(',')
                if len(split) == 2 and string2int(split[0]) is not None and string2int(split[1]) is not None:
                    t1 = string2int(split[0])
                    t2 = string2int(split[1])
                    tilt_range = [min(t1,t2), max(t1,t2)]
                else:
                    return "Please check the format of tilt range is correct. two integers seperated by ','!"
            except:
                return "Please check the format of tilt range is correct. two integers seperated by ','!"
        else:
            tilt_range = [-60,60]
            #return "Please specify tilt range!"
        
        if self.lineEdit_target_tilt_range.text():
            line = self.lineEdit_target_tilt_range.text()
            try:
                split = line.split(',')
                if len(split) == 2 and string2int(split[0]) is not None and string2int(split[1]) is not None:
                    t1 = string2int(split[0])
                    t2 = string2int(split[1])
                    target_tilt_range = [min(t1,t2), max(t1,t2)]
                else:
                    return "Please check the format of target tilt range is correct. two integers seperated by ','!"
            except:
                return "Please check the format of target tilt range is correct. two integers seperated by ','!"
        else:
            return "Please specify target tilt range!"
        
        if self.lineEdit_tomo_index_subtomo_minus.text():
            tomo_index_subtomo_minus = self.lineEdit_tomo_index_subtomo_minus.text()
        else:
            return "Please specify tomo_index_subtomo_minus!"

        if self.lineEdit_tomo_index_subtomo_plus.text():
            tomo_index_subtomo_plus = self.lineEdit_tomo_index_subtomo_plus.text()
        else:
            return "Please specify tomo_index_subtomo_plus!"

        param['tomogram_star'] = tomogram_star
        param['subtomo_dir'] = subtomo_dir
        param['tilt_range'] = tilt_range
        param['subtomo_cube_size'] = subtomo_cube_size
        param['target_tilt_range'] = target_tilt_range
        param['tomo_index_subtomo_minus'] = tomo_index_subtomo_minus
        param['tomo_index_subtomo_plus'] = tomo_index_subtomo_plus
        param['use_deconv_subtomo'] = 1 if self.checkBox_use_deconv_subtomo.isChecked() else 0
        return param

    def extract_subtomos(self):
        params = self.get_extract_subtomos_params()
        if type(params) is str:
            QMessageBox.warning(self, 'Error!', \
                "Error! {}"\
                .format(params))
            self.cmd_finished(button=self.pushButton_extract_subtomo, text="Extract Subtomos")
        elif type(params) is dict:
            if self.pushButton_extract_subtomo.text() == "Extract Subtomos":
                ret = QMessageBox.question(self, 'Extract Subtomos!', \
                        "Perform Extract Subtomos?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)   
                if ret == QMessageBox.Yes:
                    
                    self.pushButton_extract_subtomo.setText("STOP")
                    
                    self.pushButton_extract_subtomo.setStyleSheet('QPushButton {color: red;}')

                    self.thread_subtomos = ExtractSubtomos(params)                

                    self.thread_subtomos.finished.connect(lambda: self.cmd_finished(self.pushButton_extract_subtomo, "Extract Subtomos"))
                    
                    self.thread_subtomos.start()
                else:
                    self.cmd_finished(button=self.pushButton_extract_subtomo, text="Extract Subtomos")
            else:
                ret = QMessageBox.question(self, 'Warning!', \
                    "Stop Extract Subtomos! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.pushButton_extract_subtomo.setText("Extract Subtomos")
                    self.pushButton_extract_subtomo.setStyleSheet("QPushButton {color: black;}")
                    self.thread_subtomos.stop_process()
                    #self.open_star_fileName(self.tomogram_star)
    
    def cmd_finished(self, button, text="Run"):
        button.setText(text)
        button.setStyleSheet("QPushButton {color: black;}")  
        self.open_star_fileName(self.tomogram_star)
