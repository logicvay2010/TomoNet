import logging, os, json

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTabWidget, QMessageBox, QHeaderView, QTableWidgetItem, QInputDialog

from TomoNet.util import browse
from TomoNet.util.utils import check_log_file, getLogContent, string2float, string2int
from TomoNet.util.io import mkfolder
from TomoNet.util.metadata import MetaData, Label, Item
from TomoNet.process.bash_isonet_deconv import Deconvolve
from TomoNet.process.bash_isonet_generate_mask import MaskGeneration
from TomoNet.process.bash_isonet_extract_subtomos import ExtractSubtomos
from TomoNet.process.bash_isonet_train_network import TrainIsoNet
from TomoNet.process.bash_isonet_predict_network import PredictIsoNet

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

        #self.read_star()
        
        self.thread_deconvolve = None
        self.thread_generate_mask = None
        self.thread_subtomos = None
        self.thread_train = None
        self.thread_predict = None

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
        self.addTab(self.tab, "CTF Deconvolve")

        self.setUI_preparation()
        self.addTab(self.tab_2, "Preparation")

        self.setUI_train()
        self.addTab(self.tab_3, "Train Neural Network (beta)")

        self.setUI_predict()
        self.addTab(self.tab_4, "Missing-Wedge Compensation (beta)")
        
        if self.md:
            self.setTableWidget(self.tableWidget, self.md)
        if self.md:
            self.setTableWidget(self.tableWidget_2, self.md)
        
        self.tableWidget.cellDoubleClicked[int, int].connect(self.browseSlotTable)
        self.tableWidget.cellChanged[int,int].connect(self.updateMDItem) 
        self.tableWidget.setSortingEnabled(False)

        self.tableWidget_2.cellDoubleClicked[int, int].connect(self.browseSlotTable)
        self.tableWidget_2.cellChanged[int,int].connect(self.updateMDItem) 
        self.tableWidget_2.setSortingEnabled(False)

        self.pushButton_insert.clicked.connect(self.copyRow)
        self.pushButton_delete.clicked.connect(self.removeRow)
        self.pushButton_generate_star.clicked.connect(self.new_star)
        self.pushButton_open_star.clicked.connect(self.open_star)
        self.pushButton_3dmod.clicked.connect(self.view_3dmod)
        self.pushButton_update_defocus.clicked.connect(self.update_defocus)

        self.pushButton_insert_2.clicked.connect(self.copyRow)
        self.pushButton_delete_2.clicked.connect(self.removeRow)
        self.pushButton_3dmod_2.clicked.connect(self.view_3dmod)
        
        #self.pushButton_3dmod.clicked.connect(self.view_3dmod)
        
        for child in self.findChildren(QtWidgets.QLineEdit):
           child.textChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        for child in self.findChildren(QtWidgets.QCheckBox):
            child.stateChanged.connect(self.save_setting)

        self.pushButton_deconv.clicked.connect(self.deconvolve)
        self.pushButton_generate_mask.clicked.connect(self.generate_mask)
        self.pushButton_extract_subtomo.clicked.connect(self.extract_subtomos)
        self.pushButton_train.clicked.connect(self.train)
        self.pushButton_predict.clicked.connect(self.predict)

        self.pushButton_train_subtomos_star.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_train_subtomos_star, 'star', location=self.isonet_folder)) 
        # self.pushButton_train_pretrained_model.clicked.connect\
        #     (lambda: browse.browseSlot(self.lineEdit_train_pretrained_model, 'h5', location=self.isonet_folder)) 
        self.pushButton_continue_from_iter.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_continue_from_iter, 'json', location=self.isonet_folder)) 
        
        self.pushButton_predict_tomo_star.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_predict_tomo_star, 'star', location=self.isonet_folder))
        self.pushButton_predict_input_model.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_predict_input_model, 'h5', location=self.isonet_folder)) 

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        
        self.retranslateUi_deconvolve()
        self.retranslateUi_preparation()
        self.retranslateUi_train()
        self.retranslateUi_predict()

        self.currentChanged.connect(self.tab_changed)
        self.read_settting()

    def setUI_deconvolve(self):
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

        self.pushButton_update_defocus = QtWidgets.QPushButton(self.tab)
        self.pushButton_update_defocus.setObjectName("pushButton_update_defocus")
        self.verticalLayout_1.addWidget(self.pushButton_update_defocus)
        
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
        self.groupBox_generate_mask.setMinimumSize(QtCore.QSize(0, 80))
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
        self.label_zAxis_crop_mask.setMinimumSize(QtCore.QSize(100, 0))
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
        self.groupBox_extract.setMinimumSize(QtCore.QSize(0, 80))
        self.groupBox_extract.setMaximumSize(QtCore.QSize(16777215, 80))
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

        self.label_tomo_index_subtomo = QtWidgets.QLabel(self.groupBox_extract)
        self.label_tomo_index_subtomo.setMinimumSize(QtCore.QSize(80, 0))
        self.label_tomo_index_subtomo.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index_subtomo.setObjectName("label_tomo_index_subtomo")
        self.horizontalLayout_2_7.addWidget(self.label_tomo_index_subtomo)
        
        self.lineEdit_tomo_index_subtomo = QtWidgets.QLineEdit(self.groupBox_extract)
        self.lineEdit_tomo_index_subtomo.setMinimumSize(QtCore.QSize(30, 25))
        self.lineEdit_tomo_index_subtomo.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_tomo_index_subtomo.setObjectName("lineEdit_tomo_index_subtomo")
        self.horizontalLayout_2_7.addWidget(self.lineEdit_tomo_index_subtomo)

        self.checkBox_use_deconv_subtomo = QtWidgets.QCheckBox(self.groupBox_extract)
        self.checkBox_use_deconv_subtomo.setChecked(True)
        self.checkBox_use_deconv_subtomo.setObjectName("checkBox_use_deconv_subtomo")
        self.horizontalLayout_2_7.addWidget(self.checkBox_use_deconv_subtomo)
        
        self.verticalLayout_2_2.addLayout(self.horizontalLayout_2_7)

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
       
    def setUI_train(self):
        
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.tab_3 = QtWidgets.QWidget()
        self.tab_3.setObjectName("tab")

        self.gridLayout_train = QtWidgets.QGridLayout(self.tab_3)

        self.groupBox_train_general = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_train_general.setMinimumSize(QtCore.QSize(0, 120))
        self.groupBox_train_general.setMaximumSize(QtCore.QSize(16777215, 150))
        self.groupBox_train_general.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_train_general.setFlat(False)
        self.groupBox_train_general.setObjectName("groupBox_train_general")

        self.verticalLayout_3_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3_1.setObjectName("verticalLayout_3_1")
        
        self.horizontalLayout_3_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_1.setObjectName("horizontalLayout_3_1")
        
        self.label_train_subtomos_star = QtWidgets.QLabel(self.groupBox_train_general)
        self.label_train_subtomos_star.setMinimumSize(QtCore.QSize(120, 0))
        self.label_train_subtomos_star.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_subtomos_star.setObjectName("label_train_subtomos_star")
        self.horizontalLayout_3_1.addWidget(self.label_train_subtomos_star)
        
        self.lineEdit_train_subtomos_star = QtWidgets.QLineEdit(self.groupBox_train_general)
        self.lineEdit_train_subtomos_star.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_subtomos_star.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_train_subtomos_star.setObjectName("lineEdit_train_subtomos_star")
        self.horizontalLayout_3_1.addWidget(self.lineEdit_train_subtomos_star)

        self.pushButton_train_subtomos_star = QtWidgets.QPushButton(self.tab_3)
        self.pushButton_train_subtomos_star.setText("")
        self.pushButton_train_subtomos_star.setIcon(icon)
        self.pushButton_train_subtomos_star.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_train_subtomos_star.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_train_subtomos_star.setMinimumSize(QtCore.QSize(48, 24))
        self.pushButton_train_subtomos_star.setObjectName("pushButton_train_subtomos_star")
        self.horizontalLayout_3_1.addWidget(self.pushButton_train_subtomos_star)

        self.verticalLayout_3_1.addLayout(self.horizontalLayout_3_1)

        self.horizontalLayout_3_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_2.setObjectName("horizontalLayout_3_2")

        # self.label_train_pretrained_model = QtWidgets.QLabel(self.groupBox_train_general)
        # self.label_train_pretrained_model.setMinimumSize(QtCore.QSize(80, 0))
        # self.label_train_pretrained_model.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        # self.label_train_pretrained_model.setObjectName("label_train_pretrained_model")
        # self.horizontalLayout_3_2.addWidget(self.label_train_pretrained_model)
        
        # self.lineEdit_train_pretrained_model = QtWidgets.QLineEdit(self.groupBox_train_general)
        # self.lineEdit_train_pretrained_model.setMinimumSize(QtCore.QSize(80, 25))
        # self.lineEdit_train_pretrained_model.setMaximumSize(QtCore.QSize(16777215, 25))
        # self.lineEdit_train_pretrained_model.setObjectName("lineEdit_train_pretrained_model")
        # self.horizontalLayout_3_2.addWidget(self.lineEdit_train_pretrained_model)

        # self.pushButton_train_pretrained_model = QtWidgets.QPushButton(self.tab_3)
        # self.pushButton_train_pretrained_model.setText("")
        # self.pushButton_train_pretrained_model.setIcon(icon)
        # self.pushButton_train_pretrained_model.setIconSize(QtCore.QSize(24, 24))
        # self.pushButton_train_pretrained_model.setMaximumSize(QtCore.QSize(160, 24))
        # self.pushButton_train_pretrained_model.setMinimumSize(QtCore.QSize(48, 24))
        # self.pushButton_train_pretrained_model.setObjectName("pushButton_train_pretrained_model")
        # self.horizontalLayout_3_2.addWidget(self.pushButton_train_pretrained_model)

        self.label_continue_from_iter = QtWidgets.QLabel(self.groupBox_train_general)
        self.label_continue_from_iter.setMinimumSize(QtCore.QSize(150, 0))
        self.label_continue_from_iter.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_continue_from_iter.setObjectName("label_continue_from_iter")
        self.horizontalLayout_3_2.addWidget(self.label_continue_from_iter)
        
        self.lineEdit_continue_from_iter = QtWidgets.QLineEdit(self.groupBox_train_general)
        self.lineEdit_continue_from_iter.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_continue_from_iter.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_continue_from_iter.setObjectName("lineEdit_continue_from_iter")
        self.horizontalLayout_3_2.addWidget(self.lineEdit_continue_from_iter)
        
        self.pushButton_continue_from_iter = QtWidgets.QPushButton(self.tab_3)
        self.pushButton_continue_from_iter.setText("")
        self.pushButton_continue_from_iter.setIcon(icon)
        self.pushButton_continue_from_iter.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_continue_from_iter.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_continue_from_iter.setMinimumSize(QtCore.QSize(48, 24))
        self.pushButton_continue_from_iter.setObjectName("pushButton_continue_from_iter")
        self.horizontalLayout_3_2.addWidget(self.pushButton_continue_from_iter)

        self.verticalLayout_3_1.addLayout(self.horizontalLayout_3_2)

        self.horizontalLayout_3_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_3.setObjectName("horizontalLayout_3_3")

        self.label_tilt_range = QtWidgets.QLabel(self.groupBox_train_general)
        self.label_tilt_range.setMinimumSize(QtCore.QSize(80, 0))
        self.label_tilt_range.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tilt_range.setObjectName("label_tilt_range")
        self.horizontalLayout_3_3.addWidget(self.label_tilt_range)
        
        self.lineEdit_tilt_range = QtWidgets.QLineEdit(self.groupBox_train_general)
        self.lineEdit_tilt_range.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_tilt_range.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_tilt_range.setObjectName("lineEdit_tilt_range")
        self.horizontalLayout_3_3.addWidget(self.lineEdit_tilt_range)

        self.label_train_result_folder = QtWidgets.QLabel(self.groupBox_train_general)
        self.label_train_result_folder.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_result_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_result_folder.setObjectName("label_train_result_folder")
        self.horizontalLayout_3_3.addWidget(self.label_train_result_folder)
        
        self.lineEdit_train_result_folder = QtWidgets.QLineEdit(self.groupBox_train_general)
        self.lineEdit_train_result_folder.setMinimumSize(QtCore.QSize(100, 25))
        #self.lineEdit_train_result_folder.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_result_folder.setObjectName("lineEdit_train_result_folder")
        self.horizontalLayout_3_3.addWidget(self.lineEdit_train_result_folder)

        self.label_train_ncpu = QtWidgets.QLabel(self.groupBox_train_general)
        self.label_train_ncpu.setMinimumSize(QtCore.QSize(50, 0))
        self.label_train_ncpu.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_ncpu.setObjectName("label_train_ncpu")
        self.horizontalLayout_3_3.addWidget(self.label_train_ncpu)
        
        self.lineEdit_train_ncpu = QtWidgets.QLineEdit(self.groupBox_train_general)
        self.lineEdit_train_ncpu.setMinimumSize(QtCore.QSize(40, 25))
        #self.lineEdit_train_ncpu.setMaximumSize(QtCore.QSize(40, 25))
        self.lineEdit_train_ncpu.setObjectName("lineEdit_train_ncpu")
        self.horizontalLayout_3_3.addWidget(self.lineEdit_train_ncpu)

        self.label_train_gpuID = QtWidgets.QLabel(self.groupBox_train_general)
        self.label_train_gpuID.setMinimumSize(QtCore.QSize(50, 0))
        self.label_train_gpuID.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_gpuID.setObjectName("label_train_gpuID")
        self.horizontalLayout_3_3.addWidget(self.label_train_gpuID)
        
        self.lineEdit_train_gpuID = QtWidgets.QLineEdit(self.groupBox_train_general)
        self.lineEdit_train_gpuID.setMinimumSize(QtCore.QSize(80, 25))
        #self.lineEdit_train_gpuID.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_gpuID.setObjectName("lineEdit_train_gpuID")
        self.horizontalLayout_3_3.addWidget(self.lineEdit_train_gpuID)

        self.verticalLayout_3_1.addLayout(self.horizontalLayout_3_3)
        
        self.groupBox_train_general.setLayout(self.verticalLayout_3_1)

        self.gridLayout_train.addWidget(self.groupBox_train_general, 1, 0, 1, 1)

        self.groupBox_train_refinement = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_train_refinement.setMinimumSize(QtCore.QSize(0, 80))
        self.groupBox_train_refinement.setMaximumSize(QtCore.QSize(16777215, 80))
        self.groupBox_train_refinement.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_train_refinement.setFlat(False)
        self.groupBox_train_refinement.setObjectName("groupBox_train_refinement")

        self.verticalLayout_3_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3_2.setObjectName("verticalLayout_3_2")
        
        self.horizontalLayout_3_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_4.setObjectName("horizontalLayout_3_4")

        self.label_train_iteration = QtWidgets.QLabel(self.groupBox_train_refinement)
        self.label_train_iteration.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_iteration.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_iteration.setObjectName("label_train_iteration")
        self.horizontalLayout_3_4.addWidget(self.label_train_iteration)
        
        self.lineEdit_train_iteration = QtWidgets.QLineEdit(self.groupBox_train_refinement)
        self.lineEdit_train_iteration.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_iteration.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_iteration.setObjectName("lineEdit_train_iteration")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_train_iteration)

        self.label_train_batch_size = QtWidgets.QLabel(self.groupBox_train_refinement)
        self.label_train_batch_size.setMinimumSize(QtCore.QSize(80, 0))
        self.label_train_batch_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_batch_size.setObjectName("label_train_batch_size")
        self.horizontalLayout_3_4.addWidget(self.label_train_batch_size)
        
        self.lineEdit_train_batch_size = QtWidgets.QLineEdit(self.groupBox_train_refinement)
        self.lineEdit_train_batch_size.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_batch_size.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_batch_size.setObjectName("lineEdit_train_batch_size")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_train_batch_size)

        self.label_train_epoch = QtWidgets.QLabel(self.groupBox_train_refinement)
        self.label_train_epoch.setMinimumSize(QtCore.QSize(70, 0))
        self.label_train_epoch.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_epoch.setObjectName("label_train_epoch")
        self.horizontalLayout_3_4.addWidget(self.label_train_epoch)
        
        self.lineEdit_train_epoch = QtWidgets.QLineEdit(self.groupBox_train_refinement)
        self.lineEdit_train_epoch.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_epoch.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_epoch.setObjectName("lineEdit_train_epoch")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_train_epoch)

        self.label_train_step_per_epoch = QtWidgets.QLabel(self.groupBox_train_refinement)
        self.label_train_step_per_epoch.setMinimumSize(QtCore.QSize(130, 0))
        self.label_train_step_per_epoch.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_step_per_epoch.setObjectName("label_train_step_per_epoch")
        self.horizontalLayout_3_4.addWidget(self.label_train_step_per_epoch)
        
        self.lineEdit_train_step_per_epoch = QtWidgets.QLineEdit(self.groupBox_train_refinement)
        self.lineEdit_train_step_per_epoch.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_step_per_epoch.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_step_per_epoch.setObjectName("lineEdit_train_step_per_epoch")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_train_step_per_epoch)
        
        self.label_train_learning_rate = QtWidgets.QLabel(self.groupBox_train_refinement)
        self.label_train_learning_rate.setMinimumSize(QtCore.QSize(110, 0))
        self.label_train_learning_rate.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_learning_rate.setObjectName("label_train_learning_rate")
        self.horizontalLayout_3_4.addWidget(self.label_train_learning_rate)
        
        self.lineEdit_train_learning_rate = QtWidgets.QLineEdit(self.groupBox_train_refinement)
        self.lineEdit_train_learning_rate.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_learning_rate.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_train_learning_rate.setObjectName("lineEdit_train_learning_rate")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_train_learning_rate)

        self.verticalLayout_3_2.addLayout(self.horizontalLayout_3_4)

        self.groupBox_train_refinement.setLayout(self.verticalLayout_3_2)
        self.gridLayout_train.addWidget(self.groupBox_train_refinement, 2, 0, 1, 1)

        self.groupBox_train_network = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_train_network.setMinimumSize(QtCore.QSize(0, 120))
        self.groupBox_train_network.setMaximumSize(QtCore.QSize(16777215, 140))
        self.groupBox_train_network.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_train_network.setFlat(False)
        self.groupBox_train_network.setObjectName("groupBox_train_network")

        self.verticalLayout_3_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3_3.setObjectName("verticalLayout_3_3")
        
        self.horizontalLayout_3_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_5.setObjectName("horizontalLayout_3_5")

        self.label_train_depth = QtWidgets.QLabel(self.groupBox_train_network)
        self.label_train_depth.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_depth.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_depth.setObjectName("label_train_depth")
        self.horizontalLayout_3_5.addWidget(self.label_train_depth)
        
        self.lineEdit_train_depth = QtWidgets.QLineEdit(self.groupBox_train_network)
        self.lineEdit_train_depth.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_depth.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_depth.setObjectName("lineEdit_train_depth")
        self.horizontalLayout_3_5.addWidget(self.lineEdit_train_depth)

        self.label_train_conv_layer_per_depth = QtWidgets.QLabel(self.groupBox_train_network)
        self.label_train_conv_layer_per_depth.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_conv_layer_per_depth.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_conv_layer_per_depth.setObjectName("label_train_conv_layer_per_depth")
        self.horizontalLayout_3_5.addWidget(self.label_train_conv_layer_per_depth)
        
        self.lineEdit_train_conv_layer_per_depth = QtWidgets.QLineEdit(self.groupBox_train_network)
        self.lineEdit_train_conv_layer_per_depth.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_conv_layer_per_depth.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_conv_layer_per_depth.setObjectName("lineEdit_train_conv_layer_per_depth")
        self.horizontalLayout_3_5.addWidget(self.lineEdit_train_conv_layer_per_depth)

        self.label_train_kernel_size = QtWidgets.QLabel(self.groupBox_train_network)
        self.label_train_kernel_size.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_kernel_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_kernel_size.setObjectName("label_train_kernel_size")
        self.horizontalLayout_3_5.addWidget(self.label_train_kernel_size)
        
        self.lineEdit_train_kernel_size = QtWidgets.QLineEdit(self.groupBox_train_network)
        self.lineEdit_train_kernel_size.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_kernel_size.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_kernel_size.setObjectName("lineEdit_train_kernel_size")
        self.horizontalLayout_3_5.addWidget(self.lineEdit_train_kernel_size)

        self.label_train_filter_base_size = QtWidgets.QLabel(self.groupBox_train_network)
        self.label_train_filter_base_size.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_filter_base_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_filter_base_size.setObjectName("label_train_filter_base_size")
        self.horizontalLayout_3_5.addWidget(self.label_train_filter_base_size)
        
        self.lineEdit_train_filter_base_size = QtWidgets.QLineEdit(self.groupBox_train_network)
        self.lineEdit_train_filter_base_size.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_filter_base_size.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_filter_base_size.setObjectName("lineEdit_train_filter_base_size")
        self.horizontalLayout_3_5.addWidget(self.lineEdit_train_filter_base_size)

        self.label_train_dropout = QtWidgets.QLabel(self.groupBox_train_network)
        self.label_train_dropout.setMinimumSize(QtCore.QSize(90, 0))
        self.label_train_dropout.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_train_dropout.setObjectName("label_train_dropout")
        self.horizontalLayout_3_5.addWidget(self.label_train_dropout)
        
        self.lineEdit_train_dropout = QtWidgets.QLineEdit(self.groupBox_train_network)
        self.lineEdit_train_dropout.setMinimumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_dropout.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_train_dropout.setObjectName("lineEdit_train_dropout")
        self.horizontalLayout_3_5.addWidget(self.lineEdit_train_dropout)

        self.horizontalLayout_3_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_6.setObjectName("horizontalLayout_3_6")
        self.horizontalLayout_3_6.setContentsMargins(80, 0, 0, 0)

        self.checkBox_use_max_pool = QtWidgets.QCheckBox(self.groupBox_train_network)
        self.checkBox_use_max_pool.setChecked(False)
        self.checkBox_use_max_pool.setObjectName("checkBox_use_max_pool")
        self.horizontalLayout_3_6.addWidget(self.checkBox_use_max_pool)

        self.checkBox_train_batch_norm = QtWidgets.QCheckBox(self.groupBox_train_network)
        self.checkBox_train_batch_norm.setChecked(True)
        self.checkBox_train_batch_norm.setObjectName("checkBox_train_batch_norm")
        self.horizontalLayout_3_6.addWidget(self.checkBox_train_batch_norm)

        self.checkBox_train_normalize_percentile = QtWidgets.QCheckBox(self.groupBox_train_network)
        self.checkBox_train_normalize_percentile.setChecked(True)
        self.checkBox_train_normalize_percentile.setObjectName("checkBox_train_normalize_percentile")
        self.horizontalLayout_3_6.addWidget(self.checkBox_train_normalize_percentile)

        self.verticalLayout_3_3.addLayout(self.horizontalLayout_3_5)

        self.verticalLayout_3_3.addLayout(self.horizontalLayout_3_6)

        self.groupBox_train_network.setLayout(self.verticalLayout_3_3)

        self.gridLayout_train.addWidget(self.groupBox_train_network, 3, 0, 1, 1)

        self.groupBox_train_noise = QtWidgets.QGroupBox(self.tab_3)
        self.groupBox_train_noise.setMinimumSize(QtCore.QSize(0, 80))
        self.groupBox_train_noise.setMaximumSize(QtCore.QSize(16777215, 80))
        self.groupBox_train_noise.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_train_noise.setFlat(False)
        self.groupBox_train_noise.setObjectName("groupBox_train_noise")

        self.verticalLayout_3_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3_4.setObjectName("verticalLayout_3_4")
        
        self.horizontalLayout_3_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_7.setObjectName("horizontalLayout_3_7")

        self.label_noise_level = QtWidgets.QLabel(self.groupBox_train_noise)
        self.label_noise_level.setMinimumSize(QtCore.QSize(120, 0))
        self.label_noise_level.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_noise_level.setObjectName("label_noise_level")
        self.horizontalLayout_3_7.addWidget(self.label_noise_level)
        
        self.lineEdit_noise_level = QtWidgets.QLineEdit(self.groupBox_train_noise)
        self.lineEdit_noise_level.setMinimumSize(QtCore.QSize(180, 25))
        #self.lineEdit_noise_level.setMaximumSize(QtCore.QSize(180, 25))
        self.lineEdit_noise_level.setObjectName("lineEdit_noise_level")
        self.horizontalLayout_3_7.addWidget(self.lineEdit_noise_level)

        self.label_noise_start_iter = QtWidgets.QLabel(self.groupBox_train_noise)
        self.label_noise_start_iter.setMinimumSize(QtCore.QSize(120, 0))
        self.label_noise_start_iter.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_noise_start_iter.setObjectName("label_noise_start_iter")
        self.horizontalLayout_3_7.addWidget(self.label_noise_start_iter)
        
        self.lineEdit_noise_start_iter = QtWidgets.QLineEdit(self.groupBox_train_noise)
        self.lineEdit_noise_start_iter.setMinimumSize(QtCore.QSize(180, 25))
        #self.lineEdit_noise_start_iter.setMaximumSize(QtCore.QSize(180, 25))
        self.lineEdit_noise_start_iter.setObjectName("lineEdit_noise_start_iter")
        self.horizontalLayout_3_7.addWidget(self.lineEdit_noise_start_iter)

        self.label_noise_mode = QtWidgets.QLabel(self.groupBox_train_noise)
        self.label_noise_mode.setMinimumSize(QtCore.QSize(120, 0))
        self.label_noise_mode.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_noise_mode.setObjectName("label_noise_mode")
        
        self.horizontalLayout_3_7.addWidget(self.label_noise_mode)
        self.comboBox_noise_mode = QtWidgets.QComboBox(self.groupBox_train_noise)
        self.comboBox_noise_mode.setObjectName("comboBox_noise_mode")
        self.comboBox_noise_mode.addItem("")
        self.comboBox_noise_mode.addItem("")
        self.comboBox_noise_mode.addItem("")
        self.comboBox_noise_mode.setMaximumSize(QtCore.QSize(100, 25))
        self.horizontalLayout_3_7.addWidget(self.comboBox_noise_mode)

        self.verticalLayout_3_4.addLayout(self.horizontalLayout_3_7)

        self.groupBox_train_noise.setLayout(self.verticalLayout_3_4)

        self.gridLayout_train.addWidget(self.groupBox_train_noise, 4, 0, 1, 1)

        self.spacerItem3_3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_train.addItem(self.spacerItem3_3, 5, 0, 1, 1)

        self.horizontalLayout_3_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_last.setObjectName("horizontalLayout_3_last")

        spacerItem3_4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3_last.addItem(spacerItem3_4)

        self.checkBox_print_cmd_only_train = QtWidgets.QCheckBox(self.tab_3)
        self.checkBox_print_cmd_only_train.setChecked(False)
        self.checkBox_print_cmd_only_train.setObjectName("checkBox_print_cmd_only_train")
        self.horizontalLayout_3_last.addWidget(self.checkBox_print_cmd_only_train)

        self.pushButton_train = QtWidgets.QPushButton(self.tab_3)
        self.pushButton_train.setEnabled(True)
        self.pushButton_train.setMinimumSize(QtCore.QSize(120, 48))
        self.pushButton_train.setMaximumSize(QtCore.QSize(120, 48))
        self.pushButton_train.setObjectName("run")
        self.horizontalLayout_3_last.addWidget(self.pushButton_train)

        spacerItem3_5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3_last.addItem(spacerItem3_5)
        
        self.gridLayout_train.addLayout(self.horizontalLayout_3_last, 6, 0, 1, 1)
    
    def setUI_predict(self):
        
        scriptDir = os.path.dirname(os.path.realpath(__file__))
        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.tab_4 = QtWidgets.QWidget()
        self.tab_4.setObjectName("tab")

        self.gridLayout_predict = QtWidgets.QGridLayout(self.tab_4)

        self.groupBox_predict_general = QtWidgets.QGroupBox(self.tab_4)
        self.groupBox_predict_general.setMinimumSize(QtCore.QSize(0, 150))
        self.groupBox_predict_general.setMaximumSize(QtCore.QSize(16777215, 150))
        self.groupBox_predict_general.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.groupBox_predict_general.setFlat(False)
        self.groupBox_predict_general.setObjectName("groupBox_predict_general")

        self.verticalLayout_4_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4_1.setObjectName("verticalLayout_4_1")
        
        self.horizontalLayout_4_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4_1.setObjectName("horizontalLayout_4_1")
        
        self.label_predict_tomo_star = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_tomo_star.setMinimumSize(QtCore.QSize(100, 0))
        self.label_predict_tomo_star.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_tomo_star.setObjectName("label_predict_tomo_star")
        self.horizontalLayout_4_1.addWidget(self.label_predict_tomo_star)
        
        self.lineEdit_predict_tomo_star = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_tomo_star.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_predict_tomo_star.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_predict_tomo_star.setObjectName("lineEdit_predict_tomo_star")
        self.horizontalLayout_4_1.addWidget(self.lineEdit_predict_tomo_star)

        self.pushButton_predict_tomo_star = QtWidgets.QPushButton(self.tab_4)
        self.pushButton_predict_tomo_star.setText("")
        self.pushButton_predict_tomo_star.setIcon(icon)
        self.pushButton_predict_tomo_star.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_predict_tomo_star.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_predict_tomo_star.setMinimumSize(QtCore.QSize(48, 24))
        self.pushButton_predict_tomo_star.setObjectName("pushButton_predict_tomo_star")
        self.horizontalLayout_4_1.addWidget(self.pushButton_predict_tomo_star)

        self.verticalLayout_4_1.addLayout(self.horizontalLayout_4_1)

        self.horizontalLayout_4_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4_2.setObjectName("horizontalLayout_4_2")
        
        self.label_predict_input_model = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_input_model.setMinimumSize(QtCore.QSize(120, 0))
        self.label_predict_input_model.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_input_model.setObjectName("label_predict_input_model")
        self.horizontalLayout_4_2.addWidget(self.label_predict_input_model)
        
        self.lineEdit_predict_input_model = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_input_model.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_predict_input_model.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_predict_input_model.setObjectName("lineEdit_predict_input_model")
        self.horizontalLayout_4_2.addWidget(self.lineEdit_predict_input_model)

        self.pushButton_predict_input_model = QtWidgets.QPushButton(self.tab_4)
        self.pushButton_predict_input_model.setText("")
        self.pushButton_predict_input_model.setIcon(icon)
        self.pushButton_predict_input_model.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_predict_input_model.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_predict_input_model.setMinimumSize(QtCore.QSize(48, 24))
        self.pushButton_predict_input_model.setObjectName("pushButton_predict_input_model")
        self.horizontalLayout_4_2.addWidget(self.pushButton_predict_input_model)

        self.verticalLayout_4_1.addLayout(self.horizontalLayout_4_2)

        self.horizontalLayout_4_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4_3.setObjectName("horizontalLayout_4_3")
        
        self.label_predict_result_dir = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_result_dir.setMinimumSize(QtCore.QSize(80, 0))
        self.label_predict_result_dir.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_result_dir.setObjectName("label_predict_result_dir")
        self.horizontalLayout_4_3.addWidget(self.label_predict_result_dir)
        
        self.lineEdit_predict_result_dir = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_result_dir.setMinimumSize(QtCore.QSize(100, 25))
        self.lineEdit_predict_result_dir.setMaximumSize(QtCore.QSize(16777215, 25))
        self.lineEdit_predict_result_dir.setObjectName("lineEdit_predict_result_dir")
        self.horizontalLayout_4_3.addWidget(self.lineEdit_predict_result_dir)

        self.label_predict_cube_size = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_cube_size.setMinimumSize(QtCore.QSize(80, 0))
        self.label_predict_cube_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_cube_size.setObjectName("label_predict_cube_size")
        self.horizontalLayout_4_3.addWidget(self.label_predict_cube_size)
        
        self.lineEdit_predict_cube_size = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_cube_size.setMinimumSize(QtCore.QSize(50, 25))
        self.lineEdit_predict_cube_size.setMaximumSize(QtCore.QSize(50, 25))
        self.lineEdit_predict_cube_size.setObjectName("lineEdit_predict_cube_size")
        self.horizontalLayout_4_3.addWidget(self.lineEdit_predict_cube_size)

        self.label_predict_crop_size = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_crop_size.setMinimumSize(QtCore.QSize(80, 0))
        self.label_predict_crop_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_crop_size.setObjectName("label_predict_crop_size")
        self.horizontalLayout_4_3.addWidget(self.label_predict_crop_size)
        
        self.lineEdit_predict_crop_size = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_crop_size.setMinimumSize(QtCore.QSize(50, 25))
        self.lineEdit_predict_crop_size.setMaximumSize(QtCore.QSize(50, 25))
        self.lineEdit_predict_crop_size.setObjectName("lineEdit_predict_crop_size")
        self.horizontalLayout_4_3.addWidget(self.lineEdit_predict_crop_size)

        self.label_predict_gpu_ID = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_gpu_ID.setMinimumSize(QtCore.QSize(60, 0))
        self.label_predict_gpu_ID.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_gpu_ID.setObjectName("label_predict_gpu_ID")
        self.horizontalLayout_4_3.addWidget(self.label_predict_gpu_ID)
        
        self.lineEdit_predict_gpu_ID = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_gpu_ID.setMinimumSize(QtCore.QSize(50, 25))
        self.lineEdit_predict_gpu_ID.setMaximumSize(QtCore.QSize(80, 25))
        self.lineEdit_predict_gpu_ID.setObjectName("lineEdit_predict_gpu_ID")
        self.horizontalLayout_4_3.addWidget(self.lineEdit_predict_gpu_ID)

        self.label_predict_tomo_index = QtWidgets.QLabel(self.groupBox_predict_general)
        self.label_predict_tomo_index.setMinimumSize(QtCore.QSize(80, 0))
        self.label_predict_tomo_index.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_predict_tomo_index.setObjectName("label_predict_tomo_index")
        self.horizontalLayout_4_3.addWidget(self.label_predict_tomo_index)
        
        self.lineEdit_predict_tomo_index = QtWidgets.QLineEdit(self.groupBox_predict_general)
        self.lineEdit_predict_tomo_index.setMinimumSize(QtCore.QSize(50, 25))
        self.lineEdit_predict_tomo_index.setMaximumSize(QtCore.QSize(100, 25))
        self.lineEdit_predict_tomo_index.setObjectName("lineEdit_predict_tomo_index")
        self.horizontalLayout_4_3.addWidget(self.lineEdit_predict_tomo_index)
        
        self.verticalLayout_4_1.addLayout(self.horizontalLayout_4_3)

        self.groupBox_predict_general.setLayout(self.verticalLayout_4_1)

        self.gridLayout_predict.addWidget(self.groupBox_predict_general, 1, 0, 1, 1)

        self.spacerItem4_3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_predict.addItem(self.spacerItem4_3, 5, 0, 1, 1)

        self.horizontalLayout_4_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4_last.setObjectName("horizontalLayout_4_last")

        spacerItem4_4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4_last.addItem(spacerItem4_4)

        self.checkBox_print_cmd_only_predict = QtWidgets.QCheckBox(self.tab_4)
        self.checkBox_print_cmd_only_predict.setChecked(False)
        self.checkBox_print_cmd_only_predict.setObjectName("checkBox_print_cmd_only_predict")
        self.horizontalLayout_4_last.addWidget(self.checkBox_print_cmd_only_predict)

        self.pushButton_predict = QtWidgets.QPushButton(self.tab_4)
        self.pushButton_predict.setEnabled(True)
        self.pushButton_predict.setMinimumSize(QtCore.QSize(120, 48))
        self.pushButton_predict.setMaximumSize(QtCore.QSize(120, 48))
        self.pushButton_predict.setObjectName("run")
        self.horizontalLayout_4_last.addWidget(self.pushButton_predict)

        spacerItem4_5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_4_last.addItem(spacerItem4_5)
        
        self.gridLayout_predict.addLayout(self.horizontalLayout_4_last, 6, 0, 1, 1)
    
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
        self.pushButton_update_defocus.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Update all defocus value from CTF Estimation tab for all tomograms</span></p></body></html>"))
        self.pushButton_update_defocus.setText(_translate("Form", "Update Defocus"))
        self.pushButton_3dmod.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">open selected maps in 3dmod view.</span></p></body></html>"))
        self.pushButton_3dmod.setText(_translate("Form", "3dmod View"))

        self.groupBox_deconv.setTitle(_translate("Form", "Settings"))
        
        self.label_deconv_dir.setText(_translate("Form", "Deconvolve Directory"))
        self.lineEdit_deconv_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">A folder path to save your deconvolved maps. Default: deconv </span></p></body></html>"))
        self.lineEdit_deconv_dir.setPlaceholderText(_translate("Form", "deconv"))
        
        self.label_tomo_index_deconv.setText(_translate("Form", "Tomo Index"))
        self.lineEdit_tomo_index_deconv.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If this value is set, process only the tomograms listed in this index. e.g. 1,2,3,4. Default: None </span></p></body></html>"))

        self.label_chunk_size.setText(_translate("Form", "Chunk Size"))
        self.lineEdit_chunk_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Default: None. When your computer has enough memory, please keep the chunk_size as the default value: None . Otherwise, you can let the program crop the tomogram into multiple chunks for multiprocessing and assembly them into one. The chunk_size defines the size of individual chunk. This option may induce artifacts along edges of chunks. When that happen, you may use larger overlap_rate.</span></p></body></html>"))
        self.lineEdit_chunk_size.setPlaceholderText(_translate("Form", "None"))
        
        self.label_highpassnyquist.setText(_translate("Form", "High Pass Nyquist"))
        self.lineEdit_highpassnyquist.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Highpass filter at very low resolution. Default: 0.02</span></p></body></html>"))
        self.lineEdit_highpassnyquist.setPlaceholderText(_translate("Form", "0.02"))
        
        self.label_overlap.setText(_translate("Form", "Overlap Ratio"))
        self.lineEdit_overlap.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The overlapping rate for adjecent tiles. Default: 0.25 </span></p></body></html>"))
        self.lineEdit_overlap.setPlaceholderText(_translate("Form", "0.25"))

        self.label_ncpu.setText(_translate("Form", "CPU #"))
        self.lineEdit_ncpu.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">number of cpu to use in deconvolve. Default: 6 </span></p></body></html>"))
        self.lineEdit_ncpu.setPlaceholderText(_translate("Form", "6"))

        self.label_voltage.setText(_translate("Form", "Voltage"))
        self.lineEdit_voltage.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Voltage. Default: 300</span></p></body></html>"))
        self.lineEdit_voltage.setPlaceholderText(_translate("Form", "300"))

        self.label_cs.setText(_translate("Form", "CS"))
        self.lineEdit_cs.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> spherical aberration coefficient. Default: 2.7 </span></p></body></html>"))
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
        self.pushButton_3dmod_2.setText(_translate("Form", "3dmod View"))

        self.pushButton_generate_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">click to run isonet mask generation</span></p></body></html>"))
        self.pushButton_generate_mask.setText(_translate("Form", "Generate Mask"))

        self.pushButton_extract_subtomo.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">click to run isonet subtomo extraction which will be used for neural network training</span></p></body></html>"))
        self.pushButton_extract_subtomo.setText(_translate("Form", "Extract Subtomos"))
        
        self.groupBox_generate_mask.setTitle(_translate("Form", "Generate Mask Settings"))

        self.label_mask_dir.setText(_translate("Form", "Mask Directory"))
        self.lineEdit_mask_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">A folder path to save your mask for each tomograms. Default: mask</span></p><p><br/></p></body></html>"))
        self.lineEdit_mask_dir.setPlaceholderText(_translate("Form", "mask"))

        self.label_patch_size_mask.setText(_translate("Form", "Patch Size"))
        self.lineEdit_patch_size_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The size of the box from which the max-filter and std-filter are calculated. Default: mask</span></p></body></html>"))
        self.lineEdit_patch_size_mask.setPlaceholderText(_translate("Form", "4"))
        
        self.label_zAxis_crop_mask.setText(_translate("Form", "Z Axis Crop"))
        self.lineEdit_zAxis_crop_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If exclude the top and bottom regions of tomograms along z axis. For example, &quot;--z_crop 0.2&quot; will mask out the top 20% and bottom 20% region along z axis. Default: 0</span></p></body></html>"))
        self.lineEdit_zAxis_crop_mask.setPlaceholderText(_translate("Form", "0"))
        
        self.label_tomo_index_mask.setText(_translate("Form", "Tomo Index"))
        self.lineEdit_tomo_index_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If this value is set, process only the tomograms listed in this index. Default: None </span></p></body></html>"))
        
        self.checkBox_use_deconv_mask.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If CTF deconvolved tomogram is found in tomogram.star, use that tomogram instead.</span></p></body></html>"))
        self.checkBox_use_deconv_mask.setText(_translate("Form", "use deconv map"))

        self.groupBox_extract.setTitle(_translate("Form", "Extract Subtomograms Settings"))
        
        self.label_subtomo_dir.setText(_translate("Form", "Subtomo Directory"))
        self.lineEdit_subtomo_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">A folder path to save your mask for each tomograms. Default: subtomos</span></p><p><br/></p></body></html>"))
        self.lineEdit_subtomo_dir.setPlaceholderText(_translate("Form", "subtomo"))

        self.checkBox_use_deconv_subtomo.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">If CTF deconvolved tomogram is found in tomogram.star, use that tomogram instead.</span></p></body></html>"))
        self.checkBox_use_deconv_subtomo.setText(_translate("Form", "use deconv map"))
        
        self.label_subtomo_cube_size.setText(_translate("Form", "Cube Size"))
        self.lineEdit_subtomo_cube_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Size of cubes for training, should be divisible by 8, eg. 32, 64. The actual sizes of extracted subtomograms are this value add 16. Default: 64</span></p></body></html>"))
        self.lineEdit_subtomo_cube_size.setPlaceholderText(_translate("Form", "64"))
        
        self.label_tomo_index_subtomo.setText(_translate("Form", "Tomo Index"))
        self.lineEdit_tomo_index_subtomo.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">index numbers of tomograms to be used to train neural network. Default: None</span></p></body></html>"))

    def retranslateUi_train(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))

        self.groupBox_train_general.setTitle(_translate("Form", "General Settings"))
        self.label_train_subtomos_star.setText(_translate("Form", "Subtomos STAR File"))
        self.lineEdit_train_subtomos_star.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">star file containing subtomograms extracted for training. Default: IsoNet/subtomos.star </span></p></body></html>"))
        self.lineEdit_train_subtomos_star.setPlaceholderText(_translate("Form", "IsoNet/subtomos.star"))
        
        self.label_train_gpuID.setText(_translate("Form", "GPU ID"))
        self.lineEdit_train_gpuID.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> The ID of gpu to be used during the training. e.g 0,1,2,3. No default. </span></p></body></html>"))
        
        # self.label_train_pretrained_model.setText(_translate("Form", "pretrained model"))
        # self.lineEdit_train_pretrained_model.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> A trained neural network model in &quot;.h5&quot; format to start with. Default: None </span></p></body></html>"))
        # self.lineEdit_train_pretrained_model.setPlaceholderText(_translate("Form", "None"))

        self.label_continue_from_iter.setText(_translate("Form", "Continue Traning from JSON File"))
        self.lineEdit_continue_from_iter.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">A Json file to continue from. That json file is generated at each iteration of refine. Default: None </span></p></body></html>"))
        self.lineEdit_continue_from_iter.setPlaceholderText(_translate("Form", "None"))

        self.label_tilt_range.setText(_translate("Form", "Tilt Range"))
        self.lineEdit_tilt_range.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Tilt range of the reconstructed tomograms. Default: -60,60 </span></p></body></html>"))
        self.lineEdit_tilt_range.setPlaceholderText(_translate("Form", "-60,60"))
        
        self.label_train_result_folder.setText(_translate("Form", "Result Folder"))
        self.lineEdit_train_result_folder.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The name of directory to save trained network models. Default: results </span></p></body></html>"))
        self.lineEdit_train_result_folder.setPlaceholderText(_translate("Form", "results"))
        
        self.label_train_ncpu.setText(_translate("Form", "CPU #"))
        self.lineEdit_train_ncpu.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">CPU # for training dataset preparation. Default: 16</span></p></body></html>"))
        self.lineEdit_train_ncpu.setPlaceholderText(_translate("Form", "16"))
        
        # self.checkBox_only_print_command_refine.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Check to only print out the command line</span></p></body></html>"))
        # self.checkBox_only_print_command_refine.setText(_translate("Form", "only print command"))
        
        self.groupBox_train_refinement.setTitle(_translate("Form", "Training Settings"))

        self.label_train_iteration.setText(_translate("Form", "Iteration #"))
        self.lineEdit_train_iteration.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"># of training iterations. Default: 30 </span></p></body></html>"))
        self.lineEdit_train_iteration.setPlaceholderText(_translate("Form", "30"))
        
        self.label_train_batch_size.setText(_translate("Form", "Batch Size"))
        self.lineEdit_train_batch_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Size of the minibatch during training. If None, batch_size will be the max(2 * number_of_gpu, 4). Batch_size should be divisible by the number of gpu. Default: None </span></p></body></html>"))
        #self.lineEdit_train_batch_size.setPlaceholderText(_translate("Form", "4"))

        self.label_train_epoch.setText(_translate("Form", "Epochs #"))
        self.lineEdit_train_epoch.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Epoch # per iteration. Default: 10 </span></p></body></html>"))
        self.lineEdit_train_epoch.setPlaceholderText(_translate("Form", "10"))

        self.label_train_step_per_epoch.setText(_translate("Form", "Steps per Epoch"))
        self.lineEdit_train_step_per_epoch.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> Steps per epoch. If not defined, the default value will be min(num_of_subtomograms * 6 / batch_size, 200). Default: None </span></p></body></html>"))

        self.label_train_learning_rate.setText(_translate("Form", "Learning Rate"))
        self.lineEdit_train_learning_rate.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">A tuning parameter that determines the step size at each iteration while moving toward a minimum of a loss function. Default: 0.0004 </span></p></body></html>"))
        self.lineEdit_train_learning_rate.setPlaceholderText(_translate("Form", "0.0004"))

        self.groupBox_train_network.setTitle(_translate("Form", "Network Settings"))

        self.label_train_depth.setText(_translate("Form", "Network Depth"))
        self.lineEdit_train_depth.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Number of convolution layer for each depth. Default: 3 </span></p></body></html>"))
        self.lineEdit_train_depth.setPlaceholderText(_translate("Form", "3"))

        self.label_train_conv_layer_per_depth.setText(_translate("Form", "Convs per Depth"))
        self.lineEdit_train_conv_layer_per_depth.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Number of convolution layer for each depth. Default: 3 </span></p></body></html>"))
        self.lineEdit_train_conv_layer_per_depth.setPlaceholderText(_translate("Form", "3"))

        self.label_train_kernel_size.setText(_translate("Form", "Kernel Size"))
        self.lineEdit_train_kernel_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Kernel size for convolution layer. Default: 3,3,3 </span></p></body></html>"))
        self.lineEdit_train_kernel_size.setPlaceholderText(_translate("Form", "3,3,3"))

        self.label_train_filter_base_size.setText(_translate("Form", "Filter Base Size"))
        self.lineEdit_train_filter_base_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">The base number of channels after convolution. Default: 64 </span></p></body></html>"))
        self.lineEdit_train_filter_base_size.setPlaceholderText(_translate("Form", "64"))

        self.label_train_dropout.setText(_translate("Form", "Dropout Rate"))
        self.lineEdit_train_dropout.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Dropout rate to reduce overfitting. Default: 0.3 </span></p></body></html>"))
        self.lineEdit_train_dropout.setPlaceholderText(_translate("Form", "0.3"))

        self.checkBox_use_max_pool.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Use pooling layer instead of stride convolution layer. Default: False </span></p></body></html>"))
        self.checkBox_use_max_pool.setText(_translate("Form", "use maxpool layer"))

        self.checkBox_train_batch_norm.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Use Batch Normalization layer. Default: True </span></p></body></html>"))
        self.checkBox_train_batch_norm.setText(_translate("Form", "use batch normalization"))

        self.checkBox_train_normalize_percentile.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Normalize the 5 percent and 95 percent pixel intensity to 0 and 1 respectively. If this is set to False, normalize the input to 0 mean and 1 standard dievation. Default: True </span></p></body></html>"))
        self.checkBox_train_normalize_percentile.setText(_translate("Form", "use normalization percentile"))

        self.groupBox_train_noise.setTitle(_translate("Form", "Denoise Settings"))
        
        self.label_noise_level.setText(_translate("Form", "Noise Levels"))
        self.lineEdit_noise_level.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Level of noise STD(added noise)/STD(data) to start with. Set zero to disable noise reduction. Default: 0.05,0.1,0.15,0.2 </span></p></body></html>"))
        self.lineEdit_noise_level.setPlaceholderText(_translate("Form", "0.05,0.1,0.15,0.2"))
        
        self.label_noise_start_iter.setText(_translate("Form", "Start Iterations"))
        self.lineEdit_noise_start_iter.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Iteration that start to add trainning noise. Default: 11,16,21,26 </span></p></body></html>"))
        self.lineEdit_noise_start_iter.setPlaceholderText(_translate("Form", "11,16,21,26"))
        
        self.label_noise_mode.setText(_translate("Form", "Noise Mode"))
        self.comboBox_noise_mode.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Filter names when generating noise volumes, can be \'ramp\', \'hamming\' and \'noFilter\'. Default: noFilter </span></p></body></html>"))
        self.comboBox_noise_mode.setItemText(0, _translate("Form", "noFilter"))
        self.comboBox_noise_mode.setItemText(1, _translate("Form", "ramp"))
        self.comboBox_noise_mode.setItemText(2, _translate("Form", "hamming"))
        
        self.checkBox_print_cmd_only_train.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> Print out command for terminal use. </span></p></body></html>"))
        self.checkBox_print_cmd_only_train.setText(_translate("Form", "print cmd only"))
        
        self.pushButton_train.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Train neural network.</span></p></body></html>"))
        self.pushButton_train.setText(_translate("Form", "Train"))

    def retranslateUi_predict(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))

        self.groupBox_predict_general.setTitle(_translate("Form", "General Settings"))
        
        self.label_predict_tomo_star.setText(_translate("Form", "Input Tomo STAR File"))
        self.lineEdit_predict_tomo_star.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> Input star file contains tomograms to be predicted. Default: IsoNet/tomograms.star </span></p></body></html>"))
        self.lineEdit_predict_tomo_star.setPlaceholderText(_translate("Form", "IsoNet/tomograms.star"))
        
        self.label_predict_input_model.setText(_translate("Form", "Input Trained Model"))
        self.lineEdit_predict_input_model.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">A trained model to be used for prediction. No default </span></p></body></html>"))

        self.label_predict_result_dir.setText(_translate("Form", "Result Folder"))
        self.lineEdit_predict_result_dir.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> The folder name where corrected tomograms will be saved. Default: corrected_tomos </span></p></body></html>"))
        self.lineEdit_predict_result_dir.setPlaceholderText(_translate("Form", "corrected_tomos"))

        self.label_predict_gpu_ID.setText(_translate("Form", "GPU ID"))
        self.lineEdit_predict_gpu_ID.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> The ID of gpu(s) to be used. e.g 0,1,2,3. No default. </span></p></body></html>"))
        
        self.label_predict_cube_size.setText(_translate("Form", "Cube Size"))
        self.lineEdit_predict_cube_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> Size of cubes(subtomograms), should be divisible by 8, eg. 32, 64. The actual sizes of extracted subtomograms are this value add 16. Default: 64 </span></p></body></html>"))
        self.lineEdit_predict_cube_size.setPlaceholderText(_translate("Form", "64"))

        self.label_predict_crop_size.setText(_translate("Form", "Crop Size"))
        self.lineEdit_predict_crop_size.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> crop size of cubes, should be divisible by 8, and larger than the cube size. Default: 96 </span></p></body></html>"))
        self.lineEdit_predict_crop_size.setPlaceholderText(_translate("Form", "96"))

        self.label_predict_tomo_index.setText(_translate("Form", "Tomo Index"))
        self.lineEdit_predict_tomo_index.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> tomogram indexes to be used. Accepted example formats: 1 (single) or 1,2,3 (singles seperated by comma) or 1-3 (continues) . No default. </span></p></body></html>"))
        
        self.checkBox_print_cmd_only_predict.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\"> Print out command for terminal use. </span></p></body></html>"))
        self.checkBox_print_cmd_only_predict.setText(_translate("Form", "print cmd only"))
        
        self.pushButton_predict.setToolTip(_translate("Form", "<html><head/><body><p><span style=\" font-size:9pt;\">Perform missing-wedge compensation.</span></p></body></html>"))
        self.pushButton_predict.setText(_translate("Form", "Predict"))

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
        data['subtomo_cube_size'] = ""
        data['tomo_index_subtomo'] = ""
        data['use_deconv_subtomo'] = True

        data['train_subtomos_star'] = ""
        # data['train_pretrained_model'] = ""
        data['continue_from_iter'] = ""
        data['tilt_range'] = ""
        data['train_result_folder'] = ""
        data['train_ncpu'] = ""
        data['train_gpuID'] = ""

        data['train_iteration'] = ""
        data['train_batch_size'] = ""
        data['train_epoch_num'] = ""
        data['train_steps_per_epoch'] = ""
        data['train_learning_rate'] = ""

        data['train_depth'] = ""
        data['conv_layer_per_depth'] = ""
        data['train_kernel_size'] = ""
        data['train_filter_base_size'] = ""
        data['train_dropout'] = ""
        data['use_max_pool'] = False
        data['train_batch_norm'] = True
        data['train_normalize_percentile'] = True

        data['noise_level'] = ""
        data['noise_start_iter'] = ""
        data['noise_mode'] = "noFilter"

        data['predict_tomo_star'] = ""
        data['predict_input_model'] = ""
        data['predict_result_dir'] = ""
        data['predict_cube_size'] = ""
        data['predict_crop_size'] = ""
        data['predict_gpu_ID'] = ""
        data['predict_tomo_index'] = ""

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
        self.lineEdit_subtomo_cube_size.setText(data['subtomo_cube_size'])
        self.lineEdit_tomo_index_subtomo.setText(data['tomo_index_subtomo'])
        self.checkBox_use_deconv_subtomo.setChecked(data['use_deconv_subtomo'])

        self.lineEdit_train_subtomos_star.setText(data['train_subtomos_star'])
        # self.lineEdit_train_pretrained_model.setText(data['train_pretrained_model'])
        self.lineEdit_continue_from_iter.setText(data['continue_from_iter'])
        self.lineEdit_tilt_range.setText(data['tilt_range'])
        self.lineEdit_train_result_folder.setText(data['train_result_folder'])
        self.lineEdit_train_ncpu.setText(data['train_ncpu'])
        self.lineEdit_train_gpuID.setText(data['train_gpuID'])

        self.lineEdit_train_iteration.setText(data['train_iteration'])
        self.lineEdit_train_batch_size.setText(data['train_batch_size'])
        self.lineEdit_train_epoch.setText(data['train_epoch_num'])
        self.lineEdit_train_step_per_epoch.setText(data['train_steps_per_epoch'])
        self.lineEdit_train_learning_rate.setText(data['train_learning_rate'])

        self.lineEdit_train_depth.setText(data['train_depth'])
        self.lineEdit_train_conv_layer_per_depth.setText(data['conv_layer_per_depth'])
        self.lineEdit_train_kernel_size.setText(data['train_kernel_size'])
        self.lineEdit_train_filter_base_size.setText(data['train_filter_base_size'])
        self.lineEdit_train_dropout.setText(data['train_dropout'])

        self.checkBox_train_batch_norm.setChecked(data['train_batch_norm'])
        self.checkBox_train_normalize_percentile.setChecked(data['train_normalize_percentile'])
        self.checkBox_use_max_pool.setChecked(data['use_max_pool'])

        self.lineEdit_noise_level.setText(data['noise_level'])
        self.lineEdit_noise_start_iter.setText(data['noise_start_iter'])
        self.comboBox_noise_mode.setCurrentText(data['noise_mode'])

        self.lineEdit_predict_tomo_star.setText(data['predict_tomo_star'])
        self.lineEdit_predict_input_model.setText(data['predict_input_model'])
        self.lineEdit_predict_result_dir.setText(data['predict_result_dir'])
        self.lineEdit_predict_cube_size.setText(data['predict_cube_size'])
        self.lineEdit_predict_crop_size.setText(data['predict_crop_size'])
        self.lineEdit_predict_gpu_ID.setText(data['predict_gpu_ID'])
        self.lineEdit_predict_tomo_index.setText(data['predict_tomo_index'])
    
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
        param['subtomo_cube_size'] = self.lineEdit_subtomo_cube_size.text()
        param['tomo_index_subtomo'] = self.lineEdit_tomo_index_subtomo.text()
        param['use_deconv_subtomo'] = self.checkBox_use_deconv_subtomo.isChecked()

        param['train_subtomos_star'] = self.lineEdit_train_subtomos_star.text()
        # param['train_pretrained_model'] = self.lineEdit_train_pretrained_model.text()
        param['continue_from_iter'] = self.lineEdit_continue_from_iter.text()
        param['tilt_range'] = self.lineEdit_tilt_range.text()
        param['train_result_folder'] = self.lineEdit_train_result_folder.text()
        param['train_ncpu'] = self.lineEdit_train_ncpu.text()
        param['train_gpuID'] = self.lineEdit_train_gpuID.text()

        param['train_iteration'] = self.lineEdit_train_iteration.text()
        param['train_batch_size'] = self.lineEdit_train_batch_size.text()
        param['train_epoch_num'] = self.lineEdit_train_epoch.text()
        param['train_steps_per_epoch'] = self.lineEdit_train_step_per_epoch.text()
        param['train_learning_rate'] = self.lineEdit_train_learning_rate.text()

        param['train_depth'] = self.lineEdit_train_depth.text()
        param['conv_layer_per_depth'] = self.lineEdit_train_conv_layer_per_depth.text()
        param['train_kernel_size'] = self.lineEdit_train_kernel_size.text()
        param['train_filter_base_size'] = self.lineEdit_train_filter_base_size.text()
        param['train_dropout'] = self.lineEdit_train_dropout.text()
        param['use_max_pool'] = self.checkBox_use_max_pool.isChecked()
        param['train_batch_norm'] = self.checkBox_train_batch_norm.isChecked()
        param['train_normalize_percentile'] = self.checkBox_train_normalize_percentile.isChecked()

        param['noise_level'] = self.lineEdit_noise_level.text()
        param['noise_start_iter'] = self.lineEdit_noise_start_iter.text()
        param['noise_mode'] = self.comboBox_noise_mode.currentText()

        param['predict_tomo_star'] = self.lineEdit_predict_tomo_star.text()
        param['predict_input_model'] = self.lineEdit_predict_input_model.text()
        param['predict_result_dir'] = self.lineEdit_predict_result_dir.text()
        param['predict_cube_size'] = self.lineEdit_predict_cube_size.text()
        param['predict_crop_size'] = self.lineEdit_predict_crop_size.text()
        param['predict_gpu_ID'] = self.lineEdit_predict_gpu_ID.text()
        param['predict_tomo_index'] = self.lineEdit_predict_tomo_index.text()

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
        #import time
        #start_time = time.time()
        tw.setRowCount(0)
        nRows = len(md)
        labels = md.getLabels()
        nColumns = len(labels)
        #tw.setUpdatesEnabled(False)
        tw.setColumnCount(nColumns- 1) 
        tw.setRowCount(nRows)
        #self.logger.info(1)
        #self.logger.info(time.time() - start_time) #1
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
        #self.logger.info(4)
        #self.logger.info(time.time() - start_time) 

        for i in range(len(md._data)):
            it = md._data[i]
        #i=0
        #for it in md._data:
            #if i%10==1:
                #print(i)
                #print(time.time() - start_time) 
            for j in range(tw.columnCount()):
                tw.setItem(i, j, QTableWidgetItem(str(getattr(it, labels[j+1]))))
            # if i%10==1:
                # print(i)
                # print(time.time() - start_time) 
            # i+=1
        #tw.setUpdatesEnabled(True)
        #self.logger.info(5)
        #self.logger.info(time.time() - start_time) 
    
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
                                self.isonet_folder,
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

    def update_defocus(self):
        try:
            tableCtf = self.parentWidget().parentWidget().children()[2].findChild(QTabWidget, "ctffind").tableView
            
            def_dict = {}
            if tableCtf.rowCount() == 0:
                self.logger.warning("No defocus detected. If CTF Estimation was performed, please go to the CTF Estimation tab for a table refreshment.")
                return 
            else:
                for i in range(tableCtf.rowCount()): 
                    c1 = 0
                    c2 = 2
                    tomoname_i = tableCtf.item(i, c1).text()
                    defocus_i = tableCtf.item(i, c2).text()
                    def_dict[tomoname_i] = defocus_i
                
                for i in range(self.tableWidget.rowCount()): 
                    c1 = 0
                    c2 = 2
                    full_tomoname_i = self.tableWidget.item(i, c1).text()
                    basename = os.path.basename(full_tomoname_i)
                    if basename.endswith("_rec.mrc"):
                        tomoname_i = basename.split("_rec.mrc")[0]
                    elif basename.endswith(".mrc"):
                        tomoname_i = basename.split(".mrc")[0]
                    elif basename.endswith(".rec"):
                        tomoname_i = basename.split(".rec")[0]
                    else:
                        tomoname_i = basename.split(".")[0]
                    try:
                        def_value = def_dict[tomoname_i]
                    except:
                        self.logger.warning("defocus value was not detected for {}".format(tomoname_i))
                        continue
                    self.tableWidget.setItem(i, c2, QTableWidgetItem(def_value))

        except Exception as err:
            self.logger.info(err)
            return 
        self.logger.info("defocus updated.")
    
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
                elif self.currentIndex() == 1:
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
                    self.thread_deconvolve.kill_process()
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
                    self.thread_generate_mask.kill_process()
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
        
        if self.lineEdit_tomo_index_subtomo.text():
            tomo_index_subtomo = self.lineEdit_tomo_index_subtomo.text()
        else:
            tomo_index_subtomo = None

        param['tomogram_star'] = tomogram_star
        param['subtomo_dir'] = subtomo_dir
        param['subtomo_star_file'] = "{}.star".format(subtomo_dir)
        param['subtomo_cube_size'] = subtomo_cube_size
        param['tomo_index_subtomo'] = tomo_index_subtomo
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
    
    def get_train_params(self):
        
        param = {}
        
        tomogram_star = self.tomogram_star

        if self.lineEdit_train_subtomos_star.text():
            train_subtomos_star = self.lineEdit_train_subtomos_star.text()
        else:
            train_subtomos_star = "{}/subtomos.star".format(self.isonet_folder)
            if not os.path.exists(train_subtomos_star):
                return "The default input file {} does not exist".format(train_subtomos_star)
            
        # if self.lineEdit_train_pretrained_model.text():
        #     train_pretrained_model = self.lineEdit_train_pretrained_model.text()
        # else:
        #     train_pretrained_model=None
        
        if self.lineEdit_continue_from_iter.text():
            if not string2int(self.lineEdit_continue_from_iter.text()) == None:
                continue_from_iter = string2int(self.lineEdit_continue_from_iter.text())
                if not continue_from_iter > 0:
                    return "Please use the valid format for the continue from iteration #!"
            else:
                return "Please use the valid format for the continue from iteration #!"
        else:
            continue_from_iter = None

        if self.lineEdit_tilt_range.text():
            try:
                pair = self.lineEdit_tilt_range.text().split(",")
                if (not len(pair) == 2) or not string2int(pair[0]) or not string2int(pair[1]):
                    return "Please use the valid format for tilt range!"
                elif string2int(pair[0]) >= string2int(pair[1]):
                    return "The tilt range does not make sense! angle 1 should less than angle 2"
                else:
                    tilt_range = [string2int(pair[0]), string2int(pair[1])]
            except:
                return "Please use the valid format for tilt range!"
        else:
            tilt_range = [-60, 60]
        
        if self.lineEdit_train_result_folder.text():
            train_result_folder = "{}/{}".format(self.isonet_folder, self.lineEdit_train_result_folder.text())
        else:
            train_result_folder = "{}/results".format(self.isonet_folder)

        if self.lineEdit_train_ncpu.text():
            if not string2int(self.lineEdit_train_ncpu.text()) == None:
                train_ncpu = string2int(self.lineEdit_train_ncpu.text())
                if not train_ncpu > 0:
                    return "Please use the valid format for cpu #!"
            else:
                return "Please use the valid format for cpu #!"
        else:
            train_ncpu = 16

        if not len(self.lineEdit_train_gpuID.text()) > 0:
            return "Please specify GPU ID!"
        else:
            train_gpuID = self.lineEdit_train_gpuID.text()
        
        param['tomogram_star'] = tomogram_star
        param['train_subtomos_star'] = train_subtomos_star
        # param['train_pretrained_model'] = train_pretrained_model
        param['continue_from_iter'] = continue_from_iter
        param['tilt_range'] = tilt_range
        param['train_result_folder'] = train_result_folder
        param['train_ncpu'] = train_ncpu
        param['train_gpuID'] = train_gpuID
        
        if self.lineEdit_train_iteration.text():
            if not string2int(self.lineEdit_train_iteration.text()) == None:
                train_iteration = string2int(self.lineEdit_train_iteration.text())
                if not train_iteration > 0:
                    return "Please use the valid format for the training iteration #!"
            else:
                return "Please use the valid format for the training iteration #!"
        else:
            train_iteration = 30

        if self.lineEdit_train_batch_size.text():
            if not string2int(self.lineEdit_train_batch_size.text()) == None:
                train_batch_size = string2int(self.lineEdit_train_batch_size.text())
                if not train_batch_size > 0:
                    return "Please use the valid format for the training batch size!"
            else:
                return "Please use the valid format for the training batch size!"
        else:
            train_batch_size = None

        if self.lineEdit_train_epoch.text():
            if not string2int(self.lineEdit_train_epoch.text()) == None:
                train_epoch_num = string2int(self.lineEdit_train_epoch.text())
                if not train_epoch_num > 0:
                    return "Please use the valid format for the training epoch #!"
            else:
                return "Please use the valid format for the training epoch #!"
        else:
            train_epoch_num = 10

        if self.lineEdit_train_step_per_epoch.text():
            if not string2int(self.lineEdit_train_step_per_epoch.text()) == None:
                train_steps_per_epoch = string2int(self.lineEdit_train_step_per_epoch.text())
                if not train_steps_per_epoch > 0:
                    return "Please use the valid format for the training steps per epoch!"
            else:
                return "Please use the valid format for the training steps per epoch!"
        else:
            train_steps_per_epoch = None

        if self.lineEdit_train_learning_rate.text():
            if not string2float(self.lineEdit_train_learning_rate.text(), 8) == None:
                train_learning_rate = string2float(self.lineEdit_train_learning_rate.text(), 8)
                if not train_learning_rate > 0:
                    return "Please use the valid format for the training learning rate!"
            else:
                return "Please use the valid format for the training learning rate!"
        else:
            train_learning_rate = 0.0004

        param['train_iteration'] = train_iteration
        param['train_batch_size'] = train_batch_size
        param['train_epoch_num'] = train_epoch_num
        param['train_steps_per_epoch'] = train_steps_per_epoch
        param['train_learning_rate'] = train_learning_rate

        if self.lineEdit_train_depth.text():
            if not string2int(self.lineEdit_train_depth.text()) == None:
                train_depth = string2int(self.lineEdit_train_depth.text())
                if not train_depth > 0:
                    return "Please use the valid format for the training network depth!"
            else:
                return "Please use the valid format for the training network depth!"
        else:
            train_depth = 3

        if self.lineEdit_train_conv_layer_per_depth.text():
            if not string2int(self.lineEdit_train_conv_layer_per_depth.text()) == None:
                conv_layer_per_depth = string2int(self.lineEdit_train_conv_layer_per_depth.text())
                if not conv_layer_per_depth > 0:
                    return "Please use the valid format for convs per depth!"
            else:
                return "Please use the valid format for convs per depth!"
        else:
            conv_layer_per_depth = 3
        
        if not len(self.lineEdit_train_kernel_size.text()) > 0:
            train_kernel_size =  "3,3,3"
        else:
            train_kernel_size = self.lineEdit_train_kernel_size.text()

        if self.lineEdit_train_filter_base_size.text():
            if not string2int(self.lineEdit_train_filter_base_size.text()) == None:
                train_filter_base_size = string2int(self.lineEdit_train_filter_base_size.text())
                if not train_filter_base_size > 0:
                    return "Please use the valid format for filter base size!"
            else:
                return "Please use the valid format for filter base size!"
        else:
            train_filter_base_size = 64

        if self.lineEdit_train_dropout.text():
            if not string2float(self.lineEdit_train_dropout.text(), 8) == None:
                train_dropout = string2float(self.lineEdit_train_dropout.text(), 2)
                if not train_dropout > 0:
                    return "Please use the valid format for training dropout rate!"
            else:
                return "Please use the valid format for training dropout rate!"
        else:
            train_dropout = 0.3

        param['train_depth'] = train_depth
        param['conv_layer_per_depth'] = conv_layer_per_depth
        param['train_kernel_size'] = train_kernel_size
        param['train_filter_base_size'] = train_filter_base_size
        param['train_dropout'] = train_dropout

        param['use_max_pool'] = 1 if self.checkBox_use_max_pool.isChecked() else 0 
        param['train_batch_norm'] = 1 if self.checkBox_train_batch_norm.isChecked() else 0 
        param['train_normalize_percentile'] = 1 if self.checkBox_train_normalize_percentile.isChecked() else 0 

        if not len(self.lineEdit_noise_level.text()) > 0:
            noise_level =  "0.05,0.1,0.15,0.2"
        else:
            noise_level = self.lineEdit_noise_level.text()

        if not len(self.lineEdit_noise_start_iter.text()) > 0:
            noise_start_iter =  "11,16,21,26"
        else:
            noise_start_iter = self.lineEdit_noise_start_iter.text()

        param['noise_level'] = noise_level
        param['noise_start_iter'] = noise_start_iter
        param['noise_mode'] = self.comboBox_noise_mode.currentText()

        param['log_file'] = self.log_file

        return param
    
    def train(self):
        params = self.get_train_params()
        
        if type(params) is str:
            QMessageBox.warning(self, 'Error!', \
                "Error! {}"\
                .format(params))
            self.cmd_finished(button=self.pushButton_train, text="Train")
        elif type(params) is dict:
            if self.pushButton_train.text() == "Train":
                ret = QMessageBox.question(self, 'Train!', \
                        "Perform Training?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)   
                if ret == QMessageBox.Yes:
                    try:    
                        param_filename = "{}/train_params_{}.json".format(self.isonet_folder, os.path.basename(params['train_result_folder']))
                        if not os.path.exists(params['train_result_folder']):
                            mkfolder(params['train_result_folder'])
                        with open(param_filename, 'w') as fp:
                            json.dump(params, fp, indent=2, default=int)
                    except:
                        self.logger.error("Error generating JSON parameter file {}".format(param_filename))

                    cmd = "train_unet_isonet.py {}".format(param_filename)

                    if self.checkBox_print_cmd_only_train.isChecked():
                        self.logger.info("Command for training IsoNet: {}".format(cmd))
                        return
                    else:
                        self.pushButton_train.setText("STOP")
                        
                        self.pushButton_train.setStyleSheet('QPushButton {color: red;}')
                        
                        self.thread_train = TrainIsoNet(cmd)                

                        self.thread_train.finished.connect(lambda: self.cmd_finished(self.pushButton_train, "Train"))
                        
                        self.thread_train.start()
                else:
                    self.cmd_finished(button=self.pushButton_train, text="Train")
            else:
                ret = QMessageBox.question(self, 'Warning!', \
                    "Stop Training! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.thread_train.kill_process()
                    self.pushButton_train.setText("Train")
                    self.pushButton_train.setStyleSheet("QPushButton {color: black;}")
                    self.thread_train.stop_process()
    
    def get_predict_params(self):
        
        param = {}
        
        if self.lineEdit_predict_tomo_star.text():
            predict_tomo_star = self.lineEdit_predict_tomo_star.text()
        else:
            predict_tomo_star = "{}/tomograms.star".format(self.isonet_folder)
            if not os.path.exists(predict_tomo_star):
                return "The default input STAR file {} does not exist.".format(predict_tomo_star)
        
        if self.lineEdit_predict_input_model.text():
            predict_input_model = self.lineEdit_predict_input_model.text()
            if not os.path.exists(predict_input_model):
                return "The default input STAR file {} does not exist.".format(predict_input_model)
        else:
             return "Please provide the input model file (*h5).".format(predict_input_model)           
        
        if self.lineEdit_predict_result_dir.text():
            predict_result_dir = "{}/{}".format(self.isonet_folder, self.lineEdit_predict_result_dir.text())
        else:
            predict_result_dir = "{}/{}".format(self.isonet_folder, "corrected_tomograms")
        
        if not len(self.lineEdit_predict_gpu_ID.text()) > 0:
            return "Please specify GPU ID(s)!"
        else:
            predict_gpu_ID = self.lineEdit_predict_gpu_ID.text()
        
        if self.lineEdit_predict_tomo_index.text():
            predict_tomo_index = self.lineEdit_predict_tomo_index.text()
        else:
            predict_tomo_index = None
        
        if self.lineEdit_predict_cube_size.text():
            if not string2int(self.lineEdit_predict_cube_size.text()) == None:
                predict_cube_size = string2int(self.lineEdit_predict_cube_size.text())
                if not predict_cube_size > 0:
                    return "Please use the valid format for cube size!"
            else:
                return "Please use the valid format for cube size!"
        else:
            predict_cube_size = 64

        if self.lineEdit_predict_crop_size.text():
            if not string2int(self.lineEdit_predict_crop_size.text()) == None:
                predict_crop_size = string2int(self.lineEdit_predict_crop_size.text())
                if not predict_crop_size > 0:
                    return "Please use the valid format for crop size!"
            else:
                return "Please use the valid format for crop size!"
        else:
            predict_crop_size = 96
        
        param['star_file'] = predict_tomo_star
        param['model'] = predict_input_model
        param['output_dir'] = predict_result_dir
        param['gpuID'] = predict_gpu_ID
        param['tomo_idx'] = predict_tomo_index
        param['cube_size'] = predict_cube_size
        param['crop_size'] = predict_crop_size
        
        param['log_file'] = self.log_file

        return param

    def predict(self):
        
        params = self.get_predict_params()
        
        if type(params) is str:
            QMessageBox.warning(self, 'Error!', \
                "Error! {}"\
                .format(params))
            self.cmd_finished(button=self.pushButton_predict, text="Predict")
        elif type(params) is dict:
            if self.pushButton_predict.text() == "Predict":
                ret = QMessageBox.question(self, 'Predict!', \
                        "Perform Predicting?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)   
                if ret == QMessageBox.Yes:
                    try:    
                        param_filename = "{}/predict_params_{}.json".format(self.isonet_folder, os.path.basename(params['output_dir']))
                        if not os.path.exists(params['output_dir']):
                            mkfolder(params['output_dir'])
                        with open(param_filename, 'w') as fp:
                            json.dump(params, fp, indent=2, default=int)
                    except:
                        self.logger.error("Error generating JSON parameter file {}".format(param_filename))

                    cmd = "predict_unet_isonet.py {}".format(param_filename)

                    if self.checkBox_print_cmd_only_predict.isChecked():
                        self.logger.info("Command for predicting IsoNet: {}".format(cmd))
                        return
                    else:
                        self.pushButton_predict.setText("STOP")
                        
                        self.pushButton_predict.setStyleSheet('QPushButton {color: red;}')
                        
                        self.thread_predict = PredictIsoNet(cmd)                

                        self.thread_predict.finished.connect(lambda: self.cmd_finished(self.pushButton_predict, "Predict"))
                        
                        self.thread_predict.start()
                else:
                    self.cmd_finished(button=self.pushButton_predict, text="Predict")
            else:
                ret = QMessageBox.question(self, 'Warning!', \
                    "Stop Predicting! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.thread_predict.kill_process()
                    self.pushButton_predict.setText("Predict")
                    self.pushButton_predict.setStyleSheet("QPushButton {color: black;}")
                    self.thread_predict.stop_process()
                    self.open_star_fileName(self.tomogram_star)
                    
    def cmd_finished(self, button, text="Run"):
        button.setText(text)
        button.setStyleSheet("QPushButton {color: black;}")  
        self.open_star_fileName(self.tomogram_star)
