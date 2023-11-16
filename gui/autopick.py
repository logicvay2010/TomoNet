import logging
import os.path

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTabWidget, QMessageBox

from TomoNet.util import browse
import os
from TomoNet.util.utils import check_log_file, getLogContent, string2float, string2int

from TomoNet.process.bash_train_network import Train_network
from TomoNet.process.bash_predict_network import Predict_network


class Autopick(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="Autopick/autopick.setting"
        
        self.log_file = "Autopick/autopick.log"

        self.expand_folder = "Autopick"
        
        check_log_file(self.log_file, "Autopick")

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

        self.setUI_tab1()
        self.setUI_tab2()
        
        self.addTab(self.tab, "Train Network")
        self.addTab(self.tab_2, "Predict Particles")
        
        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)

        self.pushButton_input_folder_train.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_input_folder_train)) 
        self.pushButton_continue_from_model.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_continue_from_model, 'h5')) 

        self.pushButton_input_folder_predict.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_input_folder_predict)) 
        self.pushButton_input_model.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_input_model, 'h5')) 
        #self.pushButton_input_mask_predict.clicked.connect\
        #    (lambda: browse.browseSlot(self.lineEdit_input_mask_predict, 'map')) 
        
        self.pushButton_train_network.clicked.connect(self.train_network)

        for child in self.findChildren(QtWidgets.QCheckBox):
            child.stateChanged.connect(self.save_setting)

        self.pushButton_predict_network.clicked.connect(self.predict_network)

        self.read_settting()

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        
        self.retranslateUi_tab1()
        self.retranslateUi_tab2()
        #self.retranslateUi_tab3()

    def setUI_tab1(self):
        #tab 1
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 5, 10, 5)

        self.label_input_folder_train = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_input_folder_train.sizePolicy().hasHeightForWidth())
        self.label_input_folder_train.setSizePolicy(sizePolicy)
        self.label_input_folder_train.setMinimumSize(QtCore.QSize(120, 0))
        self.label_input_folder_train.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_input_folder_train.setObjectName("label_input_folder_train")
        self.horizontalLayout_1.addWidget(self.label_input_folder_train)

        self.lineEdit_input_folder_train = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_input_folder_train.setInputMask("")
        self.lineEdit_input_folder_train.setObjectName("lineEdit_input_folder_train")

        self.horizontalLayout_1.addWidget(self.lineEdit_input_folder_train)

        self.pushButton_input_folder_train = QtWidgets.QPushButton(self.tab)
        self.pushButton_input_folder_train.setText("")
        self.pushButton_input_folder_train.setIcon(self.icon)
        self.pushButton_input_folder_train.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_input_folder_train.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_input_folder_train.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_input_folder_train.setObjectName("pushButton_input_folder_train")
        self.horizontalLayout_1.addWidget(self.pushButton_input_folder_train)

        self.horizontalLayout_1_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1_2.setContentsMargins(10, 5, 10, 5)

        self.label_continue_from_model = QtWidgets.QLabel(self.tab)
        self.label_continue_from_model.setSizePolicy(sizePolicy)
        self.label_continue_from_model.setMinimumSize(QtCore.QSize(120, 0))
        self.label_continue_from_model.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_continue_from_model.setObjectName("label_continue_from_model")
        self.horizontalLayout_1_2.addWidget(self.label_continue_from_model)

        self.lineEdit_continue_from_model = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_continue_from_model.setInputMask("")
        self.lineEdit_continue_from_model.setObjectName("lineEdit_continue_from_model")
        self.horizontalLayout_1_2.addWidget(self.lineEdit_continue_from_model)

        self.pushButton_continue_from_model = QtWidgets.QPushButton(self.tab)
        self.pushButton_continue_from_model.setText("")
        self.pushButton_continue_from_model.setIcon(self.icon)
        self.pushButton_continue_from_model.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_continue_from_model.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_continue_from_model.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_continue_from_model.setObjectName("pushButton_continue_from_model")
        self.horizontalLayout_1_2.addWidget(self.pushButton_continue_from_model)

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(10, 5, 10, 5)

        self.label_result_folder_train = QtWidgets.QLabel(self.tab)
        self.label_result_folder_train.setSizePolicy(sizePolicy)
        self.label_result_folder_train.setMinimumSize(QtCore.QSize(120, 0))
        self.label_result_folder_train.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_result_folder_train.setObjectName("label_result_folder_train")
        self.horizontalLayout_2.addWidget(self.label_result_folder_train)

        self.lineEdit_result_folder_train = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_result_folder_train.setInputMask("")
        self.lineEdit_result_folder_train.setObjectName("lineEdit_result_folder_train")
        self.horizontalLayout_2.addWidget(self.lineEdit_result_folder_train)

        self.label_epoch_num = QtWidgets.QLabel(self.tab)
        self.label_epoch_num.setSizePolicy(sizePolicy)
        self.label_epoch_num.setMinimumSize(QtCore.QSize(120, 0))
        self.label_epoch_num.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_epoch_num.setObjectName("label_epoch_num")
        self.horizontalLayout_2.addWidget(self.label_epoch_num)

        self.lineEdit_epoch_num = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_epoch_num.setInputMask("")
        self.lineEdit_epoch_num.setObjectName("lineEdit_epoch_num")
        self.horizontalLayout_2.addWidget(self.lineEdit_epoch_num)

        self.label_GPU_id = QtWidgets.QLabel(self.tab)
        self.label_GPU_id.setSizePolicy(sizePolicy)
        self.label_GPU_id.setMinimumSize(QtCore.QSize(120, 0))
        self.label_GPU_id.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_GPU_id.setObjectName("label_GPU_id")
        self.horizontalLayout_2.addWidget(self.label_GPU_id)

        self.lineEdit_GPU_id = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_GPU_id.setInputMask("")
        self.lineEdit_GPU_id.setObjectName("lineEdit_GPU_id")
        self.horizontalLayout_2.addWidget(self.lineEdit_GPU_id)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(10, 5, 10, 5)
        
        self.label_subtomo_num = QtWidgets.QLabel(self.tab)
        self.label_subtomo_num.setSizePolicy(sizePolicy)
        self.label_subtomo_num.setMinimumSize(QtCore.QSize(120, 0))
        self.label_subtomo_num.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_subtomo_num.setObjectName("label_subtomo_num")
        self.horizontalLayout_3.addWidget(self.label_subtomo_num)

        self.lineEdit_subtomo_num = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_subtomo_num.setInputMask("")
        self.lineEdit_subtomo_num.setObjectName("lineEdit_subtomo_num")
        self.horizontalLayout_3.addWidget(self.lineEdit_subtomo_num)

        self.label_subtomo_box_size = QtWidgets.QLabel(self.tab)
        self.label_subtomo_box_size.setSizePolicy(sizePolicy)
        self.label_subtomo_box_size.setMinimumSize(QtCore.QSize(120, 0))
        self.label_subtomo_box_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_subtomo_box_size.setObjectName("label_subtomo_box_size")
        self.horizontalLayout_3.addWidget(self.label_subtomo_box_size)

        self.lineEdit_subtomo_box_size = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_subtomo_box_size.setInputMask("")
        self.lineEdit_subtomo_box_size.setObjectName("lineEdit_subtomo_box_size")
        self.horizontalLayout_3.addWidget(self.lineEdit_subtomo_box_size)

        self.label_label_size = QtWidgets.QLabel(self.tab)
        self.label_label_size.setSizePolicy(sizePolicy)
        self.label_label_size.setMinimumSize(QtCore.QSize(120, 0))
        self.label_label_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_label_size.setObjectName("label_label_size")
        self.horizontalLayout_3.addWidget(self.label_label_size)

        self.lineEdit_label_size = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_label_size.setInputMask("")
        self.lineEdit_label_size.setObjectName("lineEdit_label_size")
        self.horizontalLayout_3.addWidget(self.lineEdit_label_size)


        self.groupBox_2 = QtWidgets.QGroupBox()

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(5, 5, 5, 5)

        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setContentsMargins(10, 5, 10, 5)

        self.label_lr = QtWidgets.QLabel(self.tab)
        self.label_lr.setSizePolicy(sizePolicy)
        self.label_lr.setMinimumSize(QtCore.QSize(120, 0))
        self.label_lr.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_lr.setObjectName("label_lr")
        self.horizontalLayout_9.addWidget(self.label_lr)


        self.lineEdit_lr = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_lr.setInputMask("")
        self.lineEdit_lr.setObjectName("lineEdit_lr")

        self.horizontalLayout_9.addWidget(self.lineEdit_lr)

        self.label_batch_size = QtWidgets.QLabel(self.tab)
        self.label_batch_size.setSizePolicy(sizePolicy)
        self.label_batch_size.setMinimumSize(QtCore.QSize(120, 0))
        self.label_batch_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_batch_size.setObjectName("label_batch_size")
        self.horizontalLayout_9.addWidget(self.label_batch_size)


        self.lineEdit_batch_size = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_batch_size.setInputMask("")
        self.lineEdit_batch_size.setObjectName("lineEdit_batch_size")

        self.horizontalLayout_9.addWidget(self.lineEdit_batch_size)

        self.label_steps_per_epoch = QtWidgets.QLabel(self.tab)
        self.label_steps_per_epoch.setSizePolicy(sizePolicy)
        self.label_steps_per_epoch.setMinimumSize(QtCore.QSize(120, 0))
        self.label_steps_per_epoch.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_steps_per_epoch.setObjectName("label_steps_per_epoch")
        self.horizontalLayout_9.addWidget(self.label_steps_per_epoch)


        self.lineEdit_steps_per_epoch = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_steps_per_epoch.setInputMask("")
        self.lineEdit_steps_per_epoch.setObjectName("lineEdit_steps_per_epoch")
        self.horizontalLayout_9.addWidget(self.lineEdit_steps_per_epoch)

        self.label_coords_scale = QtWidgets.QLabel(self.tab)
        self.label_coords_scale.setSizePolicy(sizePolicy)
        self.label_coords_scale.setMinimumSize(QtCore.QSize(120, 0))
        self.label_coords_scale.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_coords_scale.setObjectName("label_coords_scale")
        self.horizontalLayout_9.addWidget(self.label_coords_scale)


        self.lineEdit_coords_scale = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_coords_scale.setInputMask("")
        self.lineEdit_coords_scale.setObjectName("lineEdit_coords_scale")
        self.horizontalLayout_9.addWidget(self.lineEdit_coords_scale)



        self.verticalLayout_2.addLayout(self.horizontalLayout_9)
        self.groupBox_2.setLayout(self.verticalLayout_2)


        self.horizontalLayout_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last.setObjectName("horizontalLayout_last")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem1)

        self.label_print_only_train_network = QtWidgets.QLabel(self.tab)
        self.label_print_only_train_network.setSizePolicy(sizePolicy)
        self.label_print_only_train_network.setMinimumSize(QtCore.QSize(120, 0))
        self.label_print_only_train_network.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_print_only_train_network.setObjectName("label_print_only_train_network")
        self.horizontalLayout_last.addWidget(self.label_print_only_train_network)

        self.checkBox_print_only_train_network = QtWidgets.QCheckBox(self.tab)
        self.checkBox_print_only_train_network.setChecked(False)
        self.checkBox_print_only_train_network.setObjectName("checkBox_print_only_train_network")
        self.horizontalLayout_last.addWidget(self.checkBox_print_only_train_network)

        self.pushButton_train_network = QtWidgets.QPushButton(self.tab)
        self.pushButton_train_network.setSizePolicy(sizePolicy)
        self.pushButton_train_network.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_train_network.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_train_network.setObjectName("run")
        self.horizontalLayout_last.addWidget(self.pushButton_train_network)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem2)

        self.gridLayout_prepare = QtWidgets.QGridLayout(self.tab)

        self.gridLayout_prepare.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_1_2, 1, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_2, 2, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)
        self.gridLayout_prepare.addWidget(self.groupBox_2, 4, 0, 1, 1)

        self.spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_prepare.addItem(self.spacerItem3, 5, 0, 1, 1)

        self.gridLayout_prepare.addLayout(self.horizontalLayout_last, 6, 0, 1, 1)
    
    def setUI_tab2(self):
        #tab 1
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

        self.gridLayout_prepare = QtWidgets.QGridLayout(self.tab_2)

        self.gridLayout_prepare.addLayout(self.horizontalLayout_4, 0, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_5, 1, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_7, 3, 0, 1, 1)
        self.gridLayout_prepare.addWidget(self.groupBox_1, 4, 0, 1, 1)

        self.spacerItem4 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_prepare.addItem(self.spacerItem4, 5, 0, 1, 1)

        self.gridLayout_prepare.addLayout(self.horizontalLayout_last_2, 6, 0, 1, 1)
        
    def retranslateUi_tab1(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_input_folder_train.setText(_translate("Form", "Input Folder:"))
        self.label_input_folder_train.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_input_folder_train.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_input_folder_train.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Input folder for network training. tomogram map(mrc/rec file) and coordinates files(.mod<imod model file>/.coords<text file>) are required.\
            If tomoName_mask.mrc(.rec) exist, then the mask file will be used to exclude unwanted areas for training.\
            </span></p></body></html>"))
        
        self.label_result_folder_train.setText(_translate("Form", "Output Folder Name:"))
        self.label_result_folder_train.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_result_folder_train.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_result_folder_train.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The output folder stores the trained model files.\
            </span></p></body></html>"))
        
        self.label_continue_from_model.setText(_translate("Form", "Continue from model:"))
        self.label_continue_from_model.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_continue_from_model.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_continue_from_model.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The model you want to continue from training.\
            </span></p></body></html>"))
        
        self.label_epoch_num.setText(_translate("Form", "Epoch #:"))
        self.label_epoch_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_epoch_num.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_epoch_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The epoch number during the network training. If the result folder already have trained model, it will continue the trained based on the latest exist model.\
            </span></p></body></html>"))
        
        self.label_GPU_id.setText(_translate("Form", "GPU ID:"))
        self.label_GPU_id.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_GPU_id.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_GPU_id.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The GPU to be used.\
            </span></p></body></html>"))
        
        self.label_subtomo_num.setText(_translate("Form", "Subtomo #(per tomo):"))
        self.label_subtomo_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_subtomo_num.setPlaceholderText(_translate("Form", "100"))
        self.lineEdit_subtomo_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The subtomograms number to be extracted from each of the input tomograms.\
            </span></p></body></html>"))
        
        self.label_subtomo_box_size.setText(_translate("Form", "Subtomo box size:"))
        self.label_subtomo_box_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_subtomo_box_size.setPlaceholderText(_translate("Form", "96"))
        self.lineEdit_subtomo_box_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The subtomograms box size .\
            </span></p></body></html>"))
        
        self.label_label_size.setText(_translate("Form", "Training y label size:"))
        self.label_label_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_label_size.setPlaceholderText(_translate("Form", "2"))
        self.lineEdit_label_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The y label size used in generating training dataset garget Y (particle will be label as a (2*y+1)^3 cubic). Normally 2 by default is good.\
                Unless your particle is too small or too large, you may need to decrese/increase the y label size for better performance\
            </span></p></body></html>"))
        
        self.groupBox_2.setTitle("Advanced")
        self.groupBox_2.setFlat(False)
        
        self.label_lr.setText(_translate("Form", "learning rate:"))
        self.label_lr.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_lr.setPlaceholderText(_translate("Form", "0.0001"))
        self.lineEdit_lr.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Learning rate for training network. default: 0.0001\
            </span></p></body></html>"))
        
        self.label_batch_size.setText(_translate("Form", "batch size:"))
        self.label_batch_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_batch_size.setPlaceholderText(_translate("Form", "4"))
        self.lineEdit_batch_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Batch size for training network. default: 4\
            </span></p></body></html>"))
        
        self.label_steps_per_epoch.setText(_translate("Form", "steps per epoch:"))
        self.label_steps_per_epoch.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))

        self.lineEdit_steps_per_epoch.setPlaceholderText(_translate("Form", "200"))
        self.lineEdit_steps_per_epoch.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Steps per epoch for training network. Each step, the network will learn from batch_size number of subtomograms.\
                Thus, normally batch_size*steps_per_epoch should be less than subtomogram_num*tomogram_num*4. Otherwise, same image will be learned twice. default: 200\
            </span></p></body></html>"))
        
        self.label_coords_scale.setText(_translate("Form", "coords scale:"))
        self.label_coords_scale.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_coords_scale.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_coords_scale.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> If the coordinates of particles is not in the same scale with the used tomogram. For example, if the particle was picked in bin4 volume, \
                but the input tomogram is bin8, then set the scale as 0.5, such that the coordinate matches to the density map.  default: 1\
            </span></p></body></html>"))
        
        self.label_print_only_train_network.setText(_translate("Form", "print cmd only:"))

        self.pushButton_train_network.setText(_translate("Form", "Train"))

    def retranslateUi_tab2(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))

        self.label_print_only_predict_network.setText(_translate("Form", "print cmd only:"))

        self.label_input_folder_predict.setText(_translate("Form", "Input Folder:"))
        self.label_input_folder_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_input_folder_predict.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_input_folder_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Input folder for network predicting. tomogram map(mrc/rec file) are required. You can also put the mask file in this folder for excluding bad regions.\
            If tomogram name is tomo1.mrc, the mask file should be tomo1_mask.mrc(.rec), otherwise mask file will not be recognized.\
            </span></p></body></html>"))
        
        self.label_input_model.setText(_translate("Form", "Input Model:"))
        self.label_input_model.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_input_model.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_input_model.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Input trained model from the network training. .h5 file is required. \
                Model files were save every 10 epoches, sometimes you want to try multiple models for the best performance.\
            </span></p></body></html>"))
        
        self.label_box_size_predict.setText(_translate("Form", "subtomo box size:"))
        self.label_box_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_box_size_predict.setPlaceholderText(_translate("Form", "96"))
        self.lineEdit_box_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Box size used for predicting. An interger = 8*n is required.\
            </span></p></body></html>"))
        
        self.label_unit_size_predict.setText(_translate("Form", "particle unit size(pixel):"))
        self.label_unit_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_unit_size_predict.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_unit_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The unit size of your particles in pixels. e.g., the diameter of a ribosome, or the distance between neighboring virus capsid vertex\
            </span></p></body></html>"))
        
        self.label_min_patch_size_predict.setText(_translate("Form", "min patch size:"))
        self.label_min_patch_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_min_patch_size_predict.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_min_patch_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Only useful when predicting lattice like densities. This parameter is used to exclude outliers. \
            This number defines the minimum number of a patch in your expect result, larger number will exclude more outlier prediction, but has risk to remove some good predictions too.\
            </span></p></body></html>"))
        
        self.label_y_label_size_predict.setText(_translate("Form", "y label size:"))
        self.label_y_label_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_y_label_size_predict.setPlaceholderText(_translate("Form", "2"))
        self.lineEdit_y_label_size_predict.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">This value should be consistent with your training input y label size.\
            </span></p></body></html>"))
        
        self.groupBox_1.setTitle("Advanced")
        self.groupBox_1.setFlat(False)

        self.label_tolerance.setText(_translate("Form", "tolerance:"))
        self.label_tolerance.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_tolerance.setPlaceholderText(_translate("Form", "0.5"))
        self.lineEdit_tolerance.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">This value normally is float number between 0.1-3. larger value means large tolerance to bad particles, the best value could be vcaries from different dataset. \
                (chance to getting more particles, but risk getting more bad particles). default:1\
            </span></p></body></html>"))
        
        self.label_margin.setText(_translate("Form", "overlap size:"))
        self.label_margin.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">\
            </span></p></body></html>"))
        
        self.lineEdit_margin.setPlaceholderText(_translate("Form", "16"))
        self.lineEdit_margin.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">This value normally. default:16\
            </span></p></body></html>"))
        
        
        self.pushButton_predict_network.setText(_translate("Form", "Predict"))
                   
    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 5:
                    in_current_page = False
            elif x.objectName() == "log_window":
                if in_current_page:
                    self.log_window = x
                    self.log_window.setText(getLogContent(txt))
                    self.log_window.moveCursor(QtGui.QTextCursor.End)

                    custom_font = QtGui.QFont()
                    custom_font.setPointSize(11)
                    self.log_window.setCurrentFont(custom_font)


        # self.log_window = self.parentWidget().parentWidget().children()[3] 
        # self.log_window.setText(getLogContent(txt).strip())
        # self.log_window.moveCursor(QtGui.QTextCursor.End)
        
        # custom_font = QtGui.QFont()
        # custom_font.setPointSize(11)
        # self.log_window.setCurrentFont(custom_font)

    def read_settting(self):
        if not os.path.exists(self.setting_file):
            try:
                f = open(self.setting_file)
            except:
                pass        
        data = {}
        data['input_folder_train'] = ""
        data['result_folder_train'] = ""
        data['epoch_num'] = ""
        data['GPU_id'] = ""
        data['subtomo_num'] = ""
        data['subtomo_box_size'] = ""
        data['label_size'] = ""
        data['continue_from_model'] = ""

        data['lr'] = ""
        data['batch_size'] = ""
        data['steps_per_epoch'] = ""
        data['coords_scale'] = ""

        data['checkBox_print_only_train_network'] = False

        data['input_folder_predict'] = ""
        data['input_model'] = ""
        data['box_size_predict'] = ""
        data['unit_size_predict'] = ""
        data['min_patch_size_predict'] = ""
        data['y_label_size_predict'] = ""
        data['tolerance'] = ""
        data['margin'] = ""

        data['checkBox_print_only_predict_network'] = False

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
        self.lineEdit_input_folder_train.setText(data['input_folder_train'])
        self.lineEdit_result_folder_train.setText(data['result_folder_train'])
        self.lineEdit_epoch_num.setText(data['epoch_num'])
        self.lineEdit_GPU_id.setText(data['GPU_id'])
        self.lineEdit_subtomo_num.setText(data['subtomo_num'])
        self.lineEdit_subtomo_box_size.setText(data['subtomo_box_size'])
        self.lineEdit_label_size.setText(data['label_size'])
        self.lineEdit_continue_from_model.setText(data['continue_from_model'])
  
        self.lineEdit_lr.setText(data['lr'])
        self.lineEdit_batch_size.setText(data['batch_size'])
        self.lineEdit_steps_per_epoch.setText(data['steps_per_epoch'])    
        self.lineEdit_coords_scale.setText(data['coords_scale'])    

        self.checkBox_print_only_train_network.setChecked(data['checkBox_print_only_train_network'])

        self.lineEdit_input_folder_predict.setText(data['input_folder_predict'])
        self.lineEdit_input_model.setText(data['input_model'])
        self.lineEdit_unit_size_predict.setText(data['unit_size_predict'])
        self.lineEdit_box_size_predict.setText(data['box_size_predict'])
        self.lineEdit_min_patch_size_predict.setText(data['min_patch_size_predict'])
        self.lineEdit_y_label_size_predict.setText(data['y_label_size_predict'])
        self.lineEdit_tolerance.setText(data['tolerance'])
        self.lineEdit_margin.setText(data['margin'])
        self.checkBox_print_only_predict_network.setChecked(data['checkBox_print_only_predict_network'])
    
    def save_setting(self):
        param = {}
        param['input_folder_train'] = self.lineEdit_input_folder_train.text()
        param['result_folder_train'] = self.lineEdit_result_folder_train.text()
        param['epoch_num'] = self.lineEdit_epoch_num.text()
        param['GPU_id'] = self.lineEdit_GPU_id.text()
        param['subtomo_num'] = self.lineEdit_subtomo_num.text()
        param['subtomo_box_size'] = self.lineEdit_subtomo_box_size.text()
        param['label_size'] = self.lineEdit_label_size.text()
        param['continue_from_model'] = self.lineEdit_continue_from_model.text()
        param['checkBox_print_only_train_network'] = self.checkBox_print_only_train_network.isChecked()

        param['input_folder_predict'] = self.lineEdit_input_folder_predict.text()
        param['input_model'] = self.lineEdit_input_model.text()
        param['box_size_predict'] = self.lineEdit_box_size_predict.text()
        param['unit_size_predict'] = self.lineEdit_unit_size_predict.text()
        param['min_patch_size_predict'] = self.lineEdit_min_patch_size_predict.text()
        param['y_label_size_predict'] = self.lineEdit_y_label_size_predict.text()
        param['tolerance'] = self.lineEdit_tolerance.text()
        param['margin'] = self.lineEdit_margin.text()

        param['lr'] = self.lineEdit_lr.text()
        param['batch_size'] = self.lineEdit_batch_size.text()
        param['steps_per_epoch'] = self.lineEdit_steps_per_epoch.text()
        param['coords_scale'] = self.lineEdit_coords_scale.text()

        param['checkBox_print_only_predict_network'] = self.checkBox_print_only_predict_network.isChecked()

        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))     

    def get_train_network_params(self):
        
        if not len(self.lineEdit_input_folder_train.text()) > 0:
            return "Please provide the input folder path"
        else:
            input_folder_train = self.lineEdit_input_folder_train.text()

        if not len(self.lineEdit_result_folder_train.text()) > 0:
            return "Please provide the result folder name"
        else:
            result_folder_train = self.lineEdit_result_folder_train.text()

        if not len(self.lineEdit_continue_from_model.text()) > 0:
            continue_from_model = "None"
        else:
            continue_from_model = self.lineEdit_continue_from_model.text()

        if not len(self.lineEdit_epoch_num.text()) > 0:
            epoch_num = 60
        else:
            epoch_num = self.lineEdit_epoch_num.text()
            if string2int(epoch_num) == None or string2int(epoch_num) <=0:
                return "Please use the valid format (positive integer) for the epoch number"
            else:
                epoch_num = string2int(epoch_num)

        if not len(self.lineEdit_GPU_id.text()) > 0:
            GPU_id = 0
        else:
            GPU_id = self.lineEdit_GPU_id.text()

        if not len(self.lineEdit_subtomo_num.text()) > 0:
            subtomo_num = 100
        else:
            subtomo_num = self.lineEdit_subtomo_num.text()
            if string2int(subtomo_num) == None or string2int(subtomo_num) <=0:
                return "Please use the valid format (positive integer) for the subtomogram number per tomogram"
            else:
                subtomo_num = string2int(subtomo_num)

        if not len(self.lineEdit_subtomo_box_size.text()) > 0:
            subtomo_box_size = 96
        else:
            subtomo_box_size = self.lineEdit_subtomo_box_size.text()
            if string2int(subtomo_box_size) == None or string2int(subtomo_box_size) <=0:
                return "Please use the valid format (positive integer) for the subtomogram box size"
            else:
                subtomo_box_size = string2int(subtomo_box_size)

        if not len(self.lineEdit_label_size.text()) > 0:
            label_size = 2
        else:
            label_size = self.lineEdit_label_size.text()
            if string2int(label_size) == None or string2int(label_size) <=0:
                return "Please use the valid format (positive integer) for the label size"
            else:
                label_size = string2int(label_size)

        if not len(self.lineEdit_lr.text()) > 0:
            lr = 0.0001
        else:
            lr = self.lineEdit_lr.text()
            if string2float(lr,d=10) == None or string2float(lr,d=10) <=0 :
                return "Please use the valid format (positive float) for the learning rate"
            else:
                lr = string2float(lr,d=10)

        if not len(self.lineEdit_batch_size.text()) > 0:
            batch_size = 4
        else:
            batch_size = self.lineEdit_batch_size.text()
            if string2int(batch_size) == None or string2int(batch_size) <=0 :
                return "Please use the valid format (positive integer) for the batch size"
            else:
                batch_size = string2int(batch_size)
        
        if not len(self.lineEdit_steps_per_epoch.text()) > 0:
            steps_per_epoch = 100
        else:
            steps_per_epoch = self.lineEdit_steps_per_epoch.text()
            if string2int(steps_per_epoch) == None or string2int(steps_per_epoch) <=0 :
                return "Please use the valid format (positive integer) for the steps per epoch"
            else:
                steps_per_epoch = string2int(steps_per_epoch)

        if not len(self.lineEdit_coords_scale.text()) > 0:
            coords_scale = 1
        else:
            coords_scale = self.lineEdit_coords_scale.text()
            if string2float(coords_scale) == None or string2float(coords_scale) <=0 :
                return "Please use the valid format (positive float) for the steps per epoch"
            else:
                coords_scale = string2float(coords_scale)

        params = {}
        params['input_folder_train'] = input_folder_train
        params['result_folder_train'] = "Autopick/"+result_folder_train
        params['epoch_num'] = epoch_num
        params['GPU_id'] = GPU_id
        params['subtomo_num'] = subtomo_num
        params['subtomo_box_size'] = subtomo_box_size
        params['label_size'] = label_size

        params['lr'] = lr
        params['batch_size'] = batch_size
        params['steps_per_epoch'] = steps_per_epoch
        params['coords_scale'] = coords_scale

        params['continue_from_model'] = continue_from_model
        params['checkBox_print_only_train_network'] = self.checkBox_print_only_train_network.isChecked()

        return params

    def train_network(self):
        if self.pushButton_train_network.text() == "Train":
            params = self.get_train_network_params()
            if type(params) is str:
                self.logger.error(params)
            elif type(params) is dict:
                ret = QMessageBox.question(self, 'Train', \
                        "Start Training?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
                if ret == QMessageBox.Yes:
                    self.pushButton_train_network.setText("STOP")
                    self.pushButton_train_network.setStyleSheet('QPushButton {color: red;}')
                    #print(params)
                    
                    self.thread_train_network = Train_network(params)
                    self.thread_train_network.finished.connect(lambda: self.cmd_finished(self.pushButton_train_network, 'Train'))
                    try:
                        self.thread_train_network.start()
                    except:
                        print("There is an issue running this function!")
                        self.thread_train_network.stop_process()
                    #self.cmd_finished(self.pushButton_train_network, "Train")
        else:
            ret = QMessageBox.question(self, 'Quit!', \
                        "Quit training?"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
            if ret == QMessageBox.Yes:
                self.cmd_finished(self.pushButton_train_network, "Train")
                try:
                    self.thread_train_network.stop_process()
                except:
                    self.logger.warning("no thread are running!")

    def get_predict_network_params(self):
        
        if not len(self.lineEdit_input_folder_predict.text()) > 0:
            return "Please provide the input tomograms folder path"
        else:
            input_folder_predict = self.lineEdit_input_folder_predict.text()

        if not len(self.lineEdit_input_model.text()) > 0:
            return "Please provide the result folder name"
        else:
            input_model = self.lineEdit_input_model.text()

        if not len(self.lineEdit_box_size_predict.text()) > 0:
            box_size_predict = 96
        else:
            box_size_predict = self.lineEdit_box_size_predict.text()
            if string2int(box_size_predict) == None or string2int(box_size_predict) <=0 or string2int(box_size_predict)%8 > 0:
                return "Please use the valid format (positive integer is divisable to 8) for the box size"
            else:
                box_size_predict = string2int(box_size_predict)

        if not len(self.lineEdit_unit_size_predict.text()) > 0:
            return "Please provide the particle unit size"
        else:
            unit_size_predict = self.lineEdit_unit_size_predict.text()
            if string2int(unit_size_predict) == None or string2int(unit_size_predict) <=0 :
                return "Please use the valid format (positive integer) for the box size"
            else:
                unit_size_predict = string2int(unit_size_predict)

        if not len(self.lineEdit_min_patch_size_predict.text()) > 0:
            min_patch_size_predict = 1
        else:
            min_patch_size_predict = self.lineEdit_min_patch_size_predict.text()
            if string2int(min_patch_size_predict) == None or string2int(min_patch_size_predict) <=0 :
                return "Please use the valid format (positive integer) for the minimum patch size"
            else:
                min_patch_size_predict = string2int(min_patch_size_predict)

        if not len(self.lineEdit_y_label_size_predict.text()) > 0:
            y_label_size_predict = 2
        else:
            y_label_size_predict = self.lineEdit_y_label_size_predict.text()
            if string2int(y_label_size_predict) == None or string2int(y_label_size_predict) <=0 :
                return "Please use the valid format (positive integer) for the minimum patch size"
            else:
                y_label_size_predict = string2int(y_label_size_predict)

        if not len(self.lineEdit_tolerance.text()) > 0:
            tolerance = 0.5
        else:
            tolerance = self.lineEdit_tolerance.text()
            if string2float(tolerance) == None or string2float(tolerance) <=0 :
                return "Please use the valid format (positive float) for the tolerance"
            else:
                tolerance = string2float(tolerance)

        if not len(self.lineEdit_margin.text()) > 0:
            margin = 16
        else:
            margin = self.lineEdit_margin.text()
            if string2int(margin) == None or string2int(margin) <=0 :
                return "Please use the valid format (positive integer) for the margin"
            else:
                margin = string2int(margin)

        params = {}
        params['input_folder_predict'] = input_folder_predict
        params['input_model'] = input_model
        params['box_size_predict'] = box_size_predict
        params['unit_size_predict'] = unit_size_predict
        params['min_patch_size_predict'] = min_patch_size_predict
        params['y_label_size_predict'] = y_label_size_predict
        params['tolerance'] = tolerance
        params['margin'] = margin
        params['checkBox_print_only_predict_network'] = self.checkBox_print_only_predict_network.isChecked()
        
        return params

    def predict_network(self):
        if self.pushButton_predict_network.text() == "Predict":
            params = self.get_predict_network_params()
            if type(params) is str:
                self.logger.error(params)
            elif type(params) is dict:
                ret = QMessageBox.question(self, 'Predict', \
                        "Start Predict?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
                if ret == QMessageBox.Yes:
                    self.pushButton_predict_network.setText("STOP")
                    self.pushButton_predict_network.setStyleSheet('QPushButton {color: red;}')
                    #print(params)
                    
                    self.thread_predict_network = Predict_network(params)
                    self.thread_predict_network.finished.connect(lambda: self.cmd_finished(self.pushButton_predict_network, 'Predict'))
                    try:
                        self.thread_predict_network.start()
                    except:
                        print("There is an issue running this function!")
                        self.thread_predict_network.stop_process()
        else:
            ret = QMessageBox.question(self, 'Quit!', \
                        "Quit predicting?"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
            if ret == QMessageBox.Yes:
                self.cmd_finished(self.pushButton_predict_network, "Predict")
                try:
                    self.thread_predict_network.stop_process()
                except:
                    self.logger.warning("no thread are running!")


    def cmd_finished(self, button, text="Run"):
        button.setText(text)
        button.setStyleSheet("QPushButton {color: black;}")

    