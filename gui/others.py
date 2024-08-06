import logging
import os.path
import shutil
import mrcfile
import math
import os, glob
import starfile
import subprocess

import numpy as np
from scipy.spatial import distance_matrix
from scipy.spatial.distance import pdist, squareform
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTabWidget, QMessageBox

from TomoNet.util import browse
from TomoNet.util.utils import check_log_file, getLogContent, string2float, string2int, getRGBs
from TomoNet.util.utils import mkfolder
from TomoNet.util.geometry import get_raw_shifts_PEET, apply_slicerRot_PEET, PEET2Relion, Relion2PEET, Relion2ChimeraX, getNeighbors

class OtherUtils(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="OtherUtils/otherUtils.setting"
        
        self.log_file = "OtherUtils/otherUtils.log"

        self.others_folder = "OtherUtils"
        
        check_log_file(self.log_file, "OtherUtils")
        
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

        self.setUI_tab3()

        self.addTab(self.tab, "Recenter {} Rotate {} Assemble to .star file".format("|","|"))

        self.addTab(self.tab2, "3D Subtomogram Place Back")

        self.addTab(self.tab_Star2PEET, "Star2PEET")

        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)

        self.pushButton_expand_result_folder.clicked.connect\
             (lambda: browse.browseFolderSlot(self.lineEdit_expand_result_folder)) 
        
        self.pushButton_data_star_file.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_data_star_file, 'star')) 
        self.pushButton_fitin_map_file.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_fitin_map_file, 'map')) 
        
        self.pushButton_input_star_file.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_input_star_file, 'star')) 
        
        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        self.pushButton_assemble.clicked.connect(self.assemble)
        self.pushButton_place_back.clicked.connect(self.placeback)
        self.pushButton_star2PEET.clicked.connect(self.star2PEET)

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.retranslateUi_tab1()
        self.retranslateUi_tab2()
        self.retranslateUi_tab3()
        self.read_settting()
    
    def setUI_tab1(self):
        #tab 1
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 5, 10, 5)

        self.label_expand_result_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_expand_result_folder.sizePolicy().hasHeightForWidth())
        self.label_expand_result_folder.setSizePolicy(sizePolicy)
        self.label_expand_result_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_expand_result_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_expand_result_folder.setObjectName("label_expand_result_folder")
        self.horizontalLayout_1.addWidget(self.label_expand_result_folder)

        self.lineEdit_expand_result_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_expand_result_folder.setInputMask("")
        self.lineEdit_expand_result_folder.setObjectName("lineEdit_expand_result_folder")

        self.horizontalLayout_1.addWidget(self.lineEdit_expand_result_folder)

        self.pushButton_expand_result_folder = QtWidgets.QPushButton(self.tab)
        self.pushButton_expand_result_folder.setText("")
        self.pushButton_expand_result_folder.setIcon(self.icon)
        self.pushButton_expand_result_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_expand_result_folder.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_expand_result_folder.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_expand_result_folder.setObjectName("pushButton_expand_result_folder")
        self.horizontalLayout_1.addWidget(self.pushButton_expand_result_folder)

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(10, 5, 10, 5)

        self.label_assemble_output_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_assemble_output_folder.sizePolicy().hasHeightForWidth())
        self.label_assemble_output_folder.setSizePolicy(sizePolicy)
        self.label_assemble_output_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_assemble_output_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_assemble_output_folder.setObjectName("label_assemble_output_folder")
        self.horizontalLayout_2.addWidget(self.label_assemble_output_folder)

        self.lineEdit_assemble_output_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_assemble_output_folder.setInputMask("")
        self.lineEdit_assemble_output_folder.setObjectName("lineEdit_assemble_output_folder")
        self.horizontalLayout_2.addWidget(self.lineEdit_assemble_output_folder)

        self.label_bin_factor = QtWidgets.QLabel(self.tab)
        self.label_bin_factor.setSizePolicy(sizePolicy)
        self.label_bin_factor.setMinimumSize(QtCore.QSize(120, 0))
        self.label_bin_factor.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_bin_factor.setObjectName("label_bin_factor")
        self.horizontalLayout_2.addWidget(self.label_bin_factor)

        self.lineEdit_bin_factor = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_bin_factor.setInputMask("")
        self.lineEdit_bin_factor.setObjectName("lineEdit_bin_factor")
        self.horizontalLayout_2.addWidget(self.lineEdit_bin_factor)
        
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(10, 5, 10, 5)
        
        self.label_recenter = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_recenter.sizePolicy().hasHeightForWidth())
        self.label_recenter.setSizePolicy(sizePolicy)
        self.label_recenter.setMinimumSize(QtCore.QSize(200, 0))
        self.label_recenter.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_recenter.setObjectName("label_recenter")
        self.horizontalLayout_3.addWidget(self.label_recenter)

        self.label_recenter_x = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_recenter_x.sizePolicy().hasHeightForWidth())
        self.label_recenter_x.setSizePolicy(sizePolicy)
        self.label_recenter_x.setMinimumSize(QtCore.QSize(120, 0))
        self.label_recenter_x.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_recenter_x.setObjectName("label_recenter_x")
        self.horizontalLayout_3.addWidget(self.label_recenter_x)

        self.lineEdit_recenter_x = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_recenter_x.setInputMask("")
        self.lineEdit_recenter_x.setObjectName("lineEdit_recenter_x")
        self.horizontalLayout_3.addWidget(self.lineEdit_recenter_x)

        self.label_recenter_y = QtWidgets.QLabel(self.tab)
        self.label_recenter_y.setSizePolicy(sizePolicy)
        self.label_recenter_y.setMinimumSize(QtCore.QSize(120, 0))
        self.label_recenter_y.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_recenter_y.setObjectName("label_recenter_y")
        self.horizontalLayout_3.addWidget(self.label_recenter_y)

        self.lineEdit_recenter_y = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_recenter_y.setInputMask("")
        self.lineEdit_recenter_y.setObjectName("lineEdit_recenter_y")
        self.horizontalLayout_3.addWidget(self.lineEdit_recenter_y)

        self.label_recenter_z = QtWidgets.QLabel(self.tab)
        self.label_recenter_z.setSizePolicy(sizePolicy)
        self.label_recenter_z.setMinimumSize(QtCore.QSize(120, 0))
        self.label_recenter_z.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_recenter_z.setObjectName("label_recenter_z")
        self.horizontalLayout_3.addWidget(self.label_recenter_z)

        self.lineEdit_recenter_z = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_recenter_z.setInputMask("")
        self.lineEdit_recenter_z.setObjectName("lineEdit_recenter_z")
        self.horizontalLayout_3.addWidget(self.lineEdit_recenter_z)

        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(10, 5, 10, 5)
        
        self.label_rotation = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_rotation.sizePolicy().hasHeightForWidth())
        self.label_rotation.setSizePolicy(sizePolicy)
        self.label_rotation.setMinimumSize(QtCore.QSize(200, 0))
        self.label_rotation.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_rotation.setObjectName("label_rotation")
        self.horizontalLayout_4.addWidget(self.label_rotation)

        self.label_rotation_x = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_rotation_x.sizePolicy().hasHeightForWidth())
        self.label_rotation_x.setSizePolicy(sizePolicy)
        self.label_rotation_x.setMinimumSize(QtCore.QSize(120, 0))
        self.label_rotation_x.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_rotation_x.setObjectName("label_rotation_x")
        self.horizontalLayout_4.addWidget(self.label_rotation_x)

        self.lineEdit_rotation_x = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_rotation_x.setInputMask("")
        self.lineEdit_rotation_x.setObjectName("lineEdit_rotation_x")
        self.horizontalLayout_4.addWidget(self.lineEdit_rotation_x)

        self.label_rotation_y = QtWidgets.QLabel(self.tab)
        self.label_rotation_y.setSizePolicy(sizePolicy)
        self.label_rotation_y.setMinimumSize(QtCore.QSize(120, 0))
        self.label_rotation_y.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_rotation_y.setObjectName("label_rotation_y")
        self.horizontalLayout_4.addWidget(self.label_rotation_y)

        self.lineEdit_rotation_y = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_rotation_y.setInputMask("")
        self.lineEdit_rotation_y.setObjectName("lineEdit_rotation_y")
        self.horizontalLayout_4.addWidget(self.lineEdit_rotation_y)

        self.label_rotation_z = QtWidgets.QLabel(self.tab)
        self.label_rotation_z.setSizePolicy(sizePolicy)
        self.label_rotation_z.setMinimumSize(QtCore.QSize(120, 0))
        self.label_rotation_z.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_rotation_z.setObjectName("label_rotation_z")
        self.horizontalLayout_4.addWidget(self.label_rotation_z)

        self.lineEdit_rotation_z = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_rotation_z.setInputMask("")
        self.lineEdit_rotation_z.setObjectName("lineEdit_rotation_z")
        self.horizontalLayout_4.addWidget(self.lineEdit_rotation_z)
 
        self.groupBox_1 = QtWidgets.QGroupBox()

        self.verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_1.setContentsMargins(5, 5, 5, 5)

        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setContentsMargins(10, 5, 10, 5)

        self.label_random_euler = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_random_euler.sizePolicy().hasHeightForWidth())
        self.label_random_euler.setSizePolicy(sizePolicy)
        self.label_random_euler.setMinimumSize(QtCore.QSize(100, 0))
        self.label_random_euler.setMaximumSize(QtCore.QSize(200, 30))
        self.label_random_euler.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_random_euler.setObjectName("label_random_euler")
        self.horizontalLayout_5.addWidget(self.label_random_euler)
        self.comboBox_random_euler = QtWidgets.QComboBox(self.tab)
        self.comboBox_random_euler.setMaximumSize(QtCore.QSize(50, 30))
        self.comboBox_random_euler.setObjectName("comboBox_random_euler")
        self.comboBox_random_euler.addItem("")
        self.comboBox_random_euler.addItem("")
        
        self.horizontalLayout_5.addWidget(self.comboBox_random_euler)
        spacerItem0 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem0)

        self.verticalLayout_1.addLayout(self.horizontalLayout_5)
        self.groupBox_1.setLayout(self.verticalLayout_1)

        self.horizontalLayout_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last.setObjectName("horizontalLayout_last")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem1)
        self.pushButton_assemble = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_assemble.sizePolicy().hasHeightForWidth())
        self.pushButton_assemble.setSizePolicy(sizePolicy)
        self.pushButton_assemble.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_assemble.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_assemble.setObjectName("run")
        self.horizontalLayout_last.addWidget(self.pushButton_assemble)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem2)

        self.gridLayout_run_tab_1 = QtWidgets.QGridLayout(self.tab)

        self.gridLayout_run_tab_1.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_run_tab_1.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.gridLayout_run_tab_1.addLayout(self.horizontalLayout_4, 2, 0, 1, 1)
        self.gridLayout_run_tab_1.addLayout(self.horizontalLayout_3, 3, 0, 1, 1)
        self.gridLayout_run_tab_1.addWidget(self.groupBox_1, 4, 0, 1, 1)


        self.spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_run_tab_1.addItem(self.spacerItem3, 5, 0, 1, 1)

        self.gridLayout_run_tab_1.addLayout(self.horizontalLayout_last, 6, 0, 1, 1)
    
    def retranslateUi_tab1(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_expand_result_folder.setText(_translate("Form", "Expand Result Folder:"))
        self.label_expand_result_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_expand_result_folder.setPlaceholderText(_translate("Form", "Expand/result_xxx"))
        self.lineEdit_expand_result_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The folder path store all the Expand results:TomoName_final folders\
            </span></p></body></html>"))
        
        self.label_assemble_output_folder.setText(_translate("Form", "Output Folder Name:"))
        self.label_assemble_output_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_assemble_output_folder.setPlaceholderText(_translate("Form", "assemble_01"))
        self.lineEdit_assemble_output_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The output folder name for assemble results. User customized.\
            </span></p></body></html>"))
        
        self.label_bin_factor.setText(_translate("Form", "Bin factor:"))
        self.label_bin_factor.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_bin_factor.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_bin_factor.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The binning factor for the tomogram used for picking. \
                The Relion particle.star file store no binned coords info.\
            </span></p></body></html>"))
        
        self.label_recenter.setText(_translate("Form", "Re-center shifts (pixel) on"))
        self.label_recenter.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"\
                font-size:9pt;\"> In the average/reference, \
                use the new center's coords minus density map center.\
                For example (48,54,48) - (48,48,48) = 0,6,0\
            </span></p></body></html>"))
        
        self.label_recenter_x.setText(_translate("Form", "X-axis:"))
        self.label_recenter_x.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_recenter_x.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_recenter_x.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Recenter Shifts on X-axis before rotation.\
            </span></p></body></html>"))
        
        self.label_recenter_y.setText(_translate("Form", "Y-axis:"))
        self.label_recenter_y.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_recenter_y.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_recenter_y.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Recenter Shifts on Y-axis before rotation.\
            </span></p></body></html>"))
        
        self.label_recenter_z.setText(_translate("Form", "Z-axis:"))
        self.label_recenter_z.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_recenter_z.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_recenter_z.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Recenter Shifts on Z-axis before rotation.\
            </span></p></body></html>"))
        
        self.label_rotation.setText(_translate("Form", "Rotation (degree) apply on "))
        self.label_rotation.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"\
                font-size:9pt;\"> In 3dmod, use slicer view to rotate on X and/or Y and/or Z to get the expected orientation. Use the value showed in the slicer view for each axis.\
            This is essential if you want to apply symmetry reconstruction later: aligning the symmetry axis to new Z-axis. And try the parameter with \
            rotatevol command in PEET to see if the rotation is expected before Relion refinement.\
            </span></p></body></html>"))
        
        self.label_rotation_x.setText(_translate("Form", "X-axis:"))
        self.label_rotation_x.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_rotation_x.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_rotation_x.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">rotation apply on X-axis.\
            </span></p></body></html>"))
        
        self.label_rotation_y.setText(_translate("Form", "Y-axis:"))
        self.label_rotation_y.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_rotation_y.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_rotation_y.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">rotation apply on Y-axis.\
            </span></p></body></html>"))
        
        self.label_rotation_z.setText(_translate("Form", "Z-axis:"))
        self.label_rotation_z.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_rotation_z.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_rotation_z.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">rotation apply on Z-axis.\
            </span></p></body></html>"))
        
        self.groupBox_1.setTitle("Advanced")
        self.groupBox_1.setFlat(False)
            
        self.label_random_euler.setText(_translate("Form", "use random euler angles:"))
        self.comboBox_random_euler.setItemText(0, _translate("Form", "No"))
        self.comboBox_random_euler.setItemText(1, _translate("Form", "Yes"))
        self.comboBox_random_euler.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Select Yes to generate random euler angles. Only use this if the MOTL.csv (euler angles) is not provided. (default No)\
            </span></p></body></html>"))

        self.pushButton_assemble.setText(_translate("Form", "RUN"))

    def setUI_tab2(self):
        self.tab2 = QtWidgets.QWidget()
        self.tab2.setObjectName("tab")

        self.horizontalLayout_2_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_1.setContentsMargins(10, 5, 10, 5)

        self.label_data_star_file = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_data_star_file.sizePolicy().hasHeightForWidth())
        self.label_data_star_file.setSizePolicy(sizePolicy)
        self.label_data_star_file.setMinimumSize(QtCore.QSize(120, 0))
        self.label_data_star_file.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_data_star_file.setObjectName("label_data_star_file")
        self.horizontalLayout_2_1.addWidget(self.label_data_star_file)

        self.lineEdit_data_star_file = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_data_star_file.setInputMask("")
        self.lineEdit_data_star_file.setObjectName("lineEdit_data_star_file")
        self.horizontalLayout_2_1.addWidget(self.lineEdit_data_star_file)

        self.pushButton_data_star_file = QtWidgets.QPushButton(self.tab2)
        self.pushButton_data_star_file.setText("")
        self.pushButton_data_star_file.setIcon(self.icon)
        self.pushButton_data_star_file.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_data_star_file.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_data_star_file.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_data_star_file.setObjectName("pushButton_data_star_file")
        self.horizontalLayout_2_1.addWidget(self.pushButton_data_star_file)

        self.horizontalLayout_2_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_2.setContentsMargins(10, 5, 10, 5)

        self.label_fitin_map_file = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_fitin_map_file.sizePolicy().hasHeightForWidth())
        self.label_fitin_map_file.setSizePolicy(sizePolicy)
        self.label_fitin_map_file.setMinimumSize(QtCore.QSize(120, 0))
        self.label_fitin_map_file.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_fitin_map_file.setObjectName("label_fitin_map_file")
        self.horizontalLayout_2_2.addWidget(self.label_fitin_map_file)

        self.lineEdit_fitin_map_file = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_fitin_map_file.setInputMask("")
        self.lineEdit_fitin_map_file.setObjectName("lineEdit_fitin_map_file")
        self.horizontalLayout_2_2.addWidget(self.lineEdit_fitin_map_file)

        self.pushButton_fitin_map_file = QtWidgets.QPushButton(self.tab2)
        self.pushButton_fitin_map_file.setText("")
        self.pushButton_fitin_map_file.setIcon(self.icon)
        self.pushButton_fitin_map_file.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_fitin_map_file.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_fitin_map_file.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_fitin_map_file.setObjectName("pushButton_fitin_map_file")
        self.horizontalLayout_2_2.addWidget(self.pushButton_fitin_map_file)
        
        self.horizontalLayout_2_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_3.setContentsMargins(10, 5, 10, 5)

        self.label_tomo_name = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_fitin_map_file.sizePolicy().hasHeightForWidth())
        self.label_tomo_name.setSizePolicy(sizePolicy)
        self.label_tomo_name.setMinimumSize(QtCore.QSize(130, 0))
        self.label_tomo_name.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_name.setObjectName("label_tomo_name")
        self.horizontalLayout_2_3.addWidget(self.label_tomo_name)

        self.lineEdit_tomo_name = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_tomo_name.setInputMask("")
        self.lineEdit_tomo_name.setObjectName("lineEdit_tomo_name")
        self.horizontalLayout_2_3.addWidget(self.lineEdit_tomo_name)

        self.label_pixel_size_unbinned = QtWidgets.QLabel(self.tab2)
        self.label_pixel_size_unbinned.setSizePolicy(sizePolicy)
        self.label_pixel_size_unbinned.setMinimumSize(QtCore.QSize(150, 0))
        self.label_pixel_size_unbinned.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_pixel_size_unbinned.setObjectName("label_pixel_size_unbinned")
        self.horizontalLayout_2_3.addWidget(self.label_pixel_size_unbinned)

        self.lineEdit_pixel_size_unbinned = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_pixel_size_unbinned.setInputMask("")
        self.lineEdit_pixel_size_unbinned.setObjectName("lineEdit_pixel_size_unbinned")
        self.horizontalLayout_2_3.addWidget(self.lineEdit_pixel_size_unbinned)

        self.label_pixel_size_fitin_map = QtWidgets.QLabel(self.tab2)
        self.label_pixel_size_fitin_map.setSizePolicy(sizePolicy)
        self.label_pixel_size_fitin_map.setMinimumSize(QtCore.QSize(150, 0))
        self.label_pixel_size_fitin_map.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_pixel_size_fitin_map.setObjectName("label_pixel_size_fitin_map")
        self.horizontalLayout_2_3.addWidget(self.label_pixel_size_fitin_map)

        self.lineEdit_pixel_size_fitin_map = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_pixel_size_fitin_map.setInputMask("")
        self.lineEdit_pixel_size_fitin_map.setObjectName("lineEdit_pixel_size_fitin_map")
        self.horizontalLayout_2_3.addWidget(self.lineEdit_pixel_size_fitin_map)

        self.horizontalLayout_2_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_4.setContentsMargins(10, 5, 10, 5)

        self.label_unit_size_cxs = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_unit_size_cxs.sizePolicy().hasHeightForWidth())
        self.label_unit_size_cxs.setSizePolicy(sizePolicy)
        self.label_unit_size_cxs.setMinimumSize(QtCore.QSize(130, 0))
        self.label_unit_size_cxs.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_unit_size_cxs.setObjectName("label_unit_size_cxs")
        self.horizontalLayout_2_4.addWidget(self.label_unit_size_cxs)

        self.lineEdit_unit_size_cxs = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_unit_size_cxs.setInputMask("")
        self.lineEdit_unit_size_cxs.setObjectName("lineEdit_unit_size_cxs")
        self.horizontalLayout_2_4.addWidget(self.lineEdit_unit_size_cxs)

        self.label_min_num_neighbors = QtWidgets.QLabel(self.tab2)
        self.label_min_num_neighbors.setSizePolicy(sizePolicy)
        self.label_min_num_neighbors.setMinimumSize(QtCore.QSize(130, 0))
        self.label_min_num_neighbors.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_num_neighbors.setObjectName("label_min_num_neighbors")
        self.horizontalLayout_2_4.addWidget(self.label_min_num_neighbors)

        self.lineEdit_min_num_neighbors = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_min_num_neighbors.setInputMask("")
        self.lineEdit_min_num_neighbors.setObjectName("lineEdit_min_num_neighbors")
        self.horizontalLayout_2_4.addWidget(self.lineEdit_min_num_neighbors)

        self.label_avg_angle = QtWidgets.QLabel(self.tab2)
        self.label_avg_angle.setSizePolicy(sizePolicy)
        self.label_avg_angle.setMinimumSize(QtCore.QSize(130, 0))
        self.label_avg_angle.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_avg_angle.setObjectName("label_avg_angle")
        self.horizontalLayout_2_4.addWidget(self.label_avg_angle)

        self.lineEdit_avg_angle = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_avg_angle.setInputMask("")
        self.lineEdit_avg_angle.setObjectName("lineEdit_avg_angle")
        self.horizontalLayout_2_4.addWidget(self.lineEdit_avg_angle)
 
        # the last H layout
        self.horizontalLayout_last_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last_2.setObjectName("horizontalLayout_last_2")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last_2.addItem(spacerItem4)
        self.pushButton_place_back = QtWidgets.QPushButton(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_place_back.sizePolicy().hasHeightForWidth())
        self.pushButton_place_back.setSizePolicy(sizePolicy)
        self.pushButton_place_back.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_place_back.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_place_back.setObjectName("run")
        self.horizontalLayout_last_2.addWidget(self.pushButton_place_back)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last_2.addItem(spacerItem5)
        
        self.gridLayout_pick_params = QtWidgets.QGridLayout(self.tab2)

        self.gridLayout_pick_params.addLayout(self.horizontalLayout_2_1, 0, 0, 1, 1)
        self.gridLayout_pick_params.addLayout(self.horizontalLayout_2_2, 1, 0, 1, 1)
        self.gridLayout_pick_params.addLayout(self.horizontalLayout_2_3, 2, 0, 1, 1)

        self.gridLayout_pick_params.addLayout(self.horizontalLayout_2_4, 3, 0, 1, 1)

        self.spacerItem6 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_pick_params.addItem(self.spacerItem6, 4, 0, 1, 1)

        self.gridLayout_pick_params.addLayout(self.horizontalLayout_last_2, 5, 0, 1, 1)
    
    def retranslateUi_tab2(self):
        _translate = QtCore.QCoreApplication.translate
        
        self.label_data_star_file.setText(_translate("Form", "Particles star file:"))
        self.label_data_star_file.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_data_star_file.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_data_star_file.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The input data.star file from refinement result of Relion. </span></p></body></html>"))
        
        self.label_fitin_map_file.setText(_translate("Form", "Average density map:"))
        self.label_fitin_map_file.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_fitin_map_file.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_fitin_map_file.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The average density map or simplified model for your sub-tomogram to be place back to the raw tomogram.</span></p></body></html>"))
        
        self.label_tomo_name.setText(_translate("Form", "Tomogram name:"))
        self.label_tomo_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_tomo_name.setPlaceholderText(_translate("Form", "all"))
        self.lineEdit_tomo_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The target tomogram name. For example TS_01. Leave empty or input 'all' this will apply on all tomograms. default: all</span></p></body></html>"))
        
        self.label_pixel_size_unbinned.setText(_translate("Form", "Unbinned pixel size:"))
        self.label_pixel_size_unbinned.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_pixel_size_unbinned.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_pixel_size_unbinned.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The unbinned pixel size.</span></p></body></html>"))
        
        self.label_pixel_size_fitin_map.setText(_translate("Form", "Fitin map pixel size:"))
        self.label_pixel_size_fitin_map.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_pixel_size_fitin_map.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_pixel_size_fitin_map.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">average density map's pixel size or target pixel size </span></p></body></html>"))
        
        self.label_unit_size_cxs.setText(_translate("Form", "Repeating Unit (Å):"))
        self.label_unit_size_cxs.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_unit_size_cxs.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_unit_size_cxs.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Distance between two repeating unit.</span></p></body></html>"))

        self.label_min_num_neighbors.setText(_translate("Form", "Min # of neighbors:"))
        self.label_min_num_neighbors.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_min_num_neighbors.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_min_num_neighbors.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Minimum number of neighboring particles that is tolerated.</span></p></body></html>"))
        
        self.label_avg_angle.setText(_translate("Form", "Maximum Angle:"))
        self.label_avg_angle.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\""))
        
        self.lineEdit_avg_angle.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_avg_angle.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Maximum neighbor angle tolerance.</span></p></body></html>"))

        self.pushButton_place_back.setText(_translate("Form", "RUN"))
          
    def setUI_tab3(self):
        #tab 3
        self.tab_Star2PEET = QtWidgets.QWidget()
        self.tab_Star2PEET.setObjectName("tab")

        self.horizontalLayout_3_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_1.setContentsMargins(10, 5, 10, 5)

        self.label_input_star_file = QtWidgets.QLabel(self.tab_Star2PEET)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_input_star_file.sizePolicy().hasHeightForWidth())
        self.label_input_star_file.setSizePolicy(sizePolicy)
        self.label_input_star_file.setMinimumSize(QtCore.QSize(120, 0))
        self.label_input_star_file.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_input_star_file.setObjectName("label_input_star_file")
        self.horizontalLayout_3_1.addWidget(self.label_input_star_file)

        self.lineEdit_input_star_file = QtWidgets.QLineEdit(self.tab_Star2PEET)
        self.lineEdit_input_star_file.setInputMask("")
        self.lineEdit_input_star_file.setObjectName("lineEdit_input_star_file")

        self.horizontalLayout_3_1.addWidget(self.lineEdit_input_star_file)

        self.pushButton_input_star_file = QtWidgets.QPushButton(self.tab_Star2PEET)
        self.pushButton_input_star_file.setText("")
        self.pushButton_input_star_file.setIcon(self.icon)
        self.pushButton_input_star_file.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_input_star_file.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_input_star_file.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_input_star_file.setObjectName("pushButton_input_star_file")
        self.horizontalLayout_3_1.addWidget(self.pushButton_input_star_file)

        self.horizontalLayout_3_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_2.setContentsMargins(10, 5, 10, 5)

        self.label_star2PEET_output_folder = QtWidgets.QLabel(self.tab_Star2PEET)
        sizePolicy.setHeightForWidth(self.label_star2PEET_output_folder.sizePolicy().hasHeightForWidth())
        self.label_star2PEET_output_folder.setSizePolicy(sizePolicy)
        self.label_star2PEET_output_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_star2PEET_output_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_star2PEET_output_folder.setObjectName("label_star2PEET_output_folder")
        self.horizontalLayout_3_2.addWidget(self.label_star2PEET_output_folder)

        self.lineEdit_star2PEET_output_folder = QtWidgets.QLineEdit(self.tab_Star2PEET)
        self.lineEdit_star2PEET_output_folder.setInputMask("")
        self.lineEdit_star2PEET_output_folder.setObjectName("lineEdit_star2PEET_output_folder")
        self.horizontalLayout_3_2.addWidget(self.lineEdit_star2PEET_output_folder)

        self.label_star2PEET_bin_factor = QtWidgets.QLabel(self.tab_Star2PEET)
        self.label_star2PEET_bin_factor.setSizePolicy(sizePolicy)
        self.label_star2PEET_bin_factor.setMinimumSize(QtCore.QSize(120, 0))
        self.label_star2PEET_bin_factor.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_star2PEET_bin_factor.setObjectName("label_star2PEET_bin_factor")
        self.horizontalLayout_3_2.addWidget(self.label_star2PEET_bin_factor)

        self.lineEdit_star2PEET_bin_factor = QtWidgets.QLineEdit(self.tab_Star2PEET)
        self.lineEdit_star2PEET_bin_factor.setInputMask("")
        self.lineEdit_star2PEET_bin_factor.setObjectName("lineEdit_star2PEET_bin_factor")
        self.horizontalLayout_3_2.addWidget(self.lineEdit_star2PEET_bin_factor)

        self.label_star2PEET_apix = QtWidgets.QLabel(self.tab_Star2PEET)
        self.label_star2PEET_apix.setSizePolicy(sizePolicy)
        self.label_star2PEET_apix.setMinimumSize(QtCore.QSize(120, 0))
        self.label_star2PEET_apix.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_star2PEET_apix.setObjectName("label_star2PEET_apix")
        self.horizontalLayout_3_2.addWidget(self.label_star2PEET_apix)

        self.lineEdit_star2PEET_apix = QtWidgets.QLineEdit(self.tab_Star2PEET)
        self.lineEdit_star2PEET_apix.setInputMask("")
        self.lineEdit_star2PEET_apix.setObjectName("lineEdit_star2PEET_apix")
        self.horizontalLayout_3_2.addWidget(self.lineEdit_star2PEET_apix)
        
        self.horizontalLayout_star2PEET_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_star2PEET_last.setObjectName("horizontalLayout_star2PEET_last")
        spacerItem7 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_star2PEET_last.addItem(spacerItem7)
        self.pushButton_star2PEET = QtWidgets.QPushButton(self.tab_Star2PEET)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_star2PEET.sizePolicy().hasHeightForWidth())
        self.pushButton_star2PEET.setSizePolicy(sizePolicy)
        self.pushButton_star2PEET.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_star2PEET.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_star2PEET.setObjectName("run")
        self.horizontalLayout_star2PEET_last.addWidget(self.pushButton_star2PEET)
        spacerItem8 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_star2PEET_last.addItem(spacerItem8)

        self.gridLayout_star2PEET_tab_3 = QtWidgets.QGridLayout(self.tab_Star2PEET)

        self.gridLayout_star2PEET_tab_3.addLayout(self.horizontalLayout_3_1, 0, 0, 1, 1)
        self.gridLayout_star2PEET_tab_3.addLayout(self.horizontalLayout_3_2, 1, 0, 1, 1)

        spacerItem9 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_star2PEET_tab_3.addItem(spacerItem9, 2, 0, 1, 1)

        self.gridLayout_star2PEET_tab_3.addLayout(self.horizontalLayout_star2PEET_last, 3, 0, 1, 1)

    def retranslateUi_tab3(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_input_star_file.setText(_translate("Form", "Input STAR file:"))
        self.label_input_star_file.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_input_star_file.setPlaceholderText(_translate("Form", "run_data.star"))
        self.lineEdit_input_star_file.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> The input STAR file path. \
            </span></p></body></html>"))
        
        self.label_star2PEET_output_folder.setText(_translate("Form", "Output folder name:"))
        self.label_star2PEET_output_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_star2PEET_output_folder.setPlaceholderText(_translate("Form", "PEET_params_01"))
        self.lineEdit_star2PEET_output_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The output folder name. All output parameter files will be stored in this folder.\
            </span></p></body></html>"))
        
        self.label_star2PEET_bin_factor.setText(_translate("Form", "Bin factor:"))
        self.label_star2PEET_bin_factor.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_star2PEET_bin_factor.setPlaceholderText(_translate("Form", "4"))
        self.lineEdit_star2PEET_bin_factor.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The binning factor applied on for the given input. Output coords = unbin_coords/bin_factor. (Default: 4)\
            </span></p></body></html>"))
        
        self.label_star2PEET_apix.setText(_translate("Form", "Unbinned pixel size:"))
        self.label_star2PEET_apix.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            </span></p></body></html>"))
        
        self.lineEdit_star2PEET_apix.setPlaceholderText(_translate("Form", "1.0"))
        self.lineEdit_star2PEET_apix.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The unbinned (bin1) pixel size (Default: 1.0)\
            </span></p></body></html>"))
        
        self.pushButton_star2PEET.setText(_translate("Form", "RUN"))

    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 6:
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
        data['expand_result_folder'] = ""
        data['assemble_output_folder'] = ""
        data['bin_factor'] = ""
        data['recenter_x'] = ""
        data['recenter_y'] = ""
        data['recenter_z'] = ""
        data['rotation_x'] = ""
        data['rotation_y'] = ""
        data['rotation_z'] = ""

        data['random_euler'] = "No"

        data['data_star_file'] =""
        data['fitin_map_file'] =""
        data['tomo_name'] =""
        data['pixel_size_unbinned'] =""
        data['pixel_size_fitin_map'] =""
        data['unit_size_cxs'] =""

        data['min_num_neighbors'] =""
        data['avg_angle'] =""

        data['input_star_file'] =""
        data['star2PEET_output_folder'] =""
        data['star2PEET_bin_factor'] =""
        data['star2PEET_apix'] =""
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
        self.lineEdit_expand_result_folder.setText(data['expand_result_folder'])
        self.lineEdit_assemble_output_folder.setText(data['assemble_output_folder'])
        self.lineEdit_bin_factor.setText(data['bin_factor'])
        self.lineEdit_recenter_x.setText(data['recenter_x'])
        self.lineEdit_recenter_y.setText(data['recenter_y'])
        self.lineEdit_recenter_z.setText(data['recenter_z'])
        self.lineEdit_rotation_x.setText(data['rotation_x'])
        self.lineEdit_rotation_y.setText(data['rotation_y'])
        self.lineEdit_rotation_z.setText(data['rotation_z'])
        
        self.comboBox_random_euler.setCurrentText(data['random_euler'])

        self.lineEdit_data_star_file.setText(data['data_star_file'])
        self.lineEdit_fitin_map_file.setText(data['fitin_map_file'])
        self.lineEdit_tomo_name.setText(data['tomo_name'])
        self.lineEdit_pixel_size_unbinned.setText(data['pixel_size_unbinned'])
        self.lineEdit_pixel_size_fitin_map.setText(data['pixel_size_fitin_map'])
        self.lineEdit_unit_size_cxs.setText(data['unit_size_cxs'])

        self.lineEdit_min_num_neighbors.setText(data['min_num_neighbors'])
        self.lineEdit_avg_angle.setText(data['avg_angle'])

        self.lineEdit_input_star_file.setText(data['input_star_file'])
        self.lineEdit_star2PEET_output_folder.setText(data['star2PEET_output_folder'])
        self.lineEdit_star2PEET_bin_factor.setText(data['star2PEET_bin_factor'])
        self.lineEdit_star2PEET_apix.setText(data['star2PEET_apix'])
          
    def save_setting(self):
        param = {}
        param['expand_result_folder'] = self.lineEdit_expand_result_folder.text()
        param['assemble_output_folder'] = self.lineEdit_assemble_output_folder.text()
        param['bin_factor'] = self.lineEdit_bin_factor.text()
        param['recenter_x'] = self.lineEdit_recenter_x.text()
        param['recenter_y'] = self.lineEdit_recenter_y.text()
        param['recenter_z'] = self.lineEdit_recenter_z.text()
        param['rotation_x'] = self.lineEdit_rotation_x.text()
        param['rotation_y'] = self.lineEdit_rotation_y.text()
        param['rotation_z'] = self.lineEdit_rotation_z.text()

        param['random_euler'] = self.comboBox_random_euler.currentText()

        param['data_star_file'] = self.lineEdit_data_star_file.text()
        param['fitin_map_file'] = self.lineEdit_fitin_map_file.text()
        param['tomo_name'] = self.lineEdit_tomo_name.text()
        param['pixel_size_unbinned'] = self.lineEdit_pixel_size_unbinned.text()
        param['pixel_size_fitin_map'] = self.lineEdit_pixel_size_fitin_map.text()
       
        param['unit_size_cxs'] = self.lineEdit_unit_size_cxs.text()
        param['min_num_neighbors'] = self.lineEdit_min_num_neighbors.text()
        param['avg_angle'] = self.lineEdit_avg_angle.text()

        param['input_star_file'] = self.lineEdit_input_star_file.text()
        param['star2PEET_output_folder'] = self.lineEdit_star2PEET_output_folder.text()
        param['star2PEET_bin_factor'] = self.lineEdit_star2PEET_bin_factor.text()
        param['star2PEET_apix'] = self.lineEdit_star2PEET_apix.text()

        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))     
    
    def get_assemble_params(self):
        
        if not len(self.lineEdit_expand_result_folder.text()) > 0:
            return "Please specify the expand result folder!"
        else:
            expand_result_folder = self.lineEdit_expand_result_folder.text()

        if not len(self.lineEdit_assemble_output_folder.text()) > 0:
            return "Please specify the assemble result folder!"
        else:
            assemble_output_folder = "{}/{}".format(self.others_folder, self.lineEdit_assemble_output_folder.text())

        if len(self.lineEdit_bin_factor.text()) > 0:
            if not string2float(self.lineEdit_bin_factor.text()) == None:
                bin_factor = string2float(self.lineEdit_bin_factor.text())
            else:
                return "Please use the valid format for the bin factor!"
        else:
            bin_factor = 1

        if len(self.lineEdit_recenter_x.text()) > 0:
            if not string2float(self.lineEdit_recenter_x.text()) == None:
                recenter_x = string2float(self.lineEdit_recenter_x.text())
            else:
                return "Please use the valid format for the x shift!"
        else:
            recenter_x = 0
        
        if len(self.lineEdit_recenter_y.text()) > 0:
            if not string2float(self.lineEdit_recenter_y.text()) == None:
                recenter_y = string2float(self.lineEdit_recenter_y.text())
            else:
                return "Please use the valid format for the x shift!"
        else:
            recenter_y = 0
        
        if len(self.lineEdit_recenter_z.text()) > 0:
            if not string2float(self.lineEdit_recenter_z.text()) == None:
                recenter_z = string2float(self.lineEdit_recenter_z.text())
            else:
                return "Please use the valid format for the x shift!"
        else:
            recenter_z = 0

        if len(self.lineEdit_rotation_x.text()) > 0:
            if not string2float(self.lineEdit_rotation_x.text()) == None:
                rotation_x = string2float(self.lineEdit_rotation_x.text())
            else:
                return "Please use the valid format for the x shift!"
        else:
            rotation_x = 0
        
        if len(self.lineEdit_rotation_y.text()) > 0:
            if not string2float(self.lineEdit_rotation_y.text()) == None:
                rotation_y = string2float(self.lineEdit_rotation_y.text())
            else:
                return "Please use the valid format for the x shift!"
        else:
            rotation_y = 0
        
        if len(self.lineEdit_rotation_z.text()) > 0:
            if not string2float(self.lineEdit_rotation_z.text()) == None:
                rotation_z = string2float(self.lineEdit_rotation_z.text())
            else:
                return "Please use the valid format for the x shift!"
        else:
            rotation_z = 0
                
        if not os.path.exists(assemble_output_folder):
            mkfolder(assemble_output_folder)

        params = {}
        params['expand_result_folder'] = expand_result_folder
        params['assemble_output_folder'] = assemble_output_folder
        params['bin_factor'] = bin_factor
        params['recenter_x'] = recenter_x
        params['recenter_y'] = recenter_y
        params['recenter_z'] = recenter_z
        params['rotation_x'] = rotation_x
        params['rotation_y'] = rotation_y
        params['rotation_z'] = rotation_z

        return params
    
    def get_final_folder_list(self, folder):
        final_folder_list = [os.path.basename(x).split(".")[0] for x in sorted(glob.glob("{}/*_final".format(folder)))]
        tomo_list = [x.split("_final")[0] for x in final_folder_list]
        
        return tomo_list

    def transform_coords_euler(self, tomo, origin_coords_file, origin_motl_file, output_coords_file, output_euler_file, shifts, rotation):
        with open(origin_coords_file, 'r') as f:
            origin_coords_lines = np.array([ x.split() for x in f.readlines()])
        if os.path.exists(origin_motl_file):
            with open(origin_motl_file, 'r') as f:
                origin_motl_lines = np.array([ x.split(',') for x in f.readlines()][1:])
            random_euler = False
        else:
            if self.comboBox_random_euler.currentText() == "No":
                random_euler = False
                self.logger.warning("MOTL.csv file is not detected for tomogram {}, set euler angles as 0,0,0 !".format(tomo))
            else:
                random_euler = True
                self.logger.warning("MOTL.csv file is not detected for tomogram {}, use random euler angles instead!".format(tomo))

        try:
            if len(origin_coords_lines) <=0 or origin_coords_lines.shape[1] < 3 or origin_coords_lines.shape[1] > 4:
                self.logger.warning(".pts file format is wrong for tomogram {}, skip it!".format(tomo))
            else:
                with open(output_coords_file, 'w') as w_c:
                    with open(output_euler_file, 'w') as w_e:
                        
                        for i, line in enumerate(origin_coords_lines):
                            if not random_euler:
                                zxz_euler = np.array([float(origin_motl_lines[i][16]),float(origin_motl_lines[i][18]),float(origin_motl_lines[i][17])])
                            else:
                                #zxz_euler = np.random.rand(3,) * 360-180
                                zxz_euler = np.random.rand(3,) * 0
                            real_shifts = get_raw_shifts_PEET(zxz_euler, shifts)

                            if origin_coords_lines.shape[1] ==4:
                                pid = line[0]
                                new_coords = np.array([float(v) for v in line[1:]]) + real_shifts
                            else:
                                pid = 1
                                new_coords = np.array([float(v) for v in line]) + real_shifts
                            
                            new_coords_line = "{} {} {} {}\n".format(pid, round(new_coords[0],2), round(new_coords[1],2), round(new_coords[2],2))
                            w_c.write(new_coords_line)
                            
                            new_zxz_euler = apply_slicerRot_PEET(zxz_euler, rotation)
                            zyz_euler = PEET2Relion(new_zxz_euler)
                            new_euler_line = "{},{},{}\n".format(round(zyz_euler[0],2), round(zyz_euler[1],2), round(zyz_euler[2],2))
                            w_e.write(new_euler_line)

            self.logger.info("coords and euler files are generated for {}! Total particle # {}".format(tomo, len(origin_coords_lines)))
        except:
            self.logger.error("It seems that the number of particle is not consistent from MOTL and pts files for {}!".format(tomo))

    def combine_all(self, tomo_list, folder, bin_factor=1):
        out_file = "{}/particles.star".format(folder)
        with open(out_file,"w") as f:
            header ="{}\n\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}\n".format(\
            "data_particles",\
            "loop_",\
            "_rlnTomoName #1",\
            "_rlnTomoParticleId #2",\
            "_rlnTomoManifoldIndex #3",\
            "_rlnCoordinateX #4",\
            "_rlnCoordinateY #5",\
            "_rlnCoordinateZ #6",\
            "_rlnOriginXAngst #7",\
            "_rlnOriginYAngst #8",\
            "_rlnOriginZAngst #9",\
            "_rlnAngleRot #10",\
            "_rlnAngleTilt #11",\
            "_rlnAnglePsi #12",\
            "_rlnClassNumber #13",\
            "_rlnRandomSubset #14")
            f.write(header)
            particle_index = 1
            manifold_id = 0
            for tomo in tomo_list:
                pid = -1
                coords_file = "{}/{}.coords".format(folder,tomo)
                try:
                    with open(coords_file,'r') as r:
                        coords_data=r.readlines()
                    euler_file = "{}/{}.euler".format(folder,tomo)
                    with open(euler_file,'r') as r:
                        euler_data=r.readlines()
                    for i in range(0, len(coords_data)):
                        
                        pair_euler = [float(x) for x in euler_data[i].strip().split(',')]
                        pair_coords = [float(x) for x in coords_data[i].strip().split()]
                        pid_now = int(pair_coords[0])
                        if pid_now > pid:
                            manifold_id +=1
                            pid = pid_now
                        line = "{} {} {} {} {} {} {} {} {} {} {} {} {} {} \n".format(tomo, particle_index, manifold_id, \
                                pair_coords[1]*bin_factor, pair_coords[2]*bin_factor, pair_coords[3]*bin_factor, \
                                0, 0, 0,\
                                pair_euler[0], pair_euler[1], pair_euler[2], \
                                1, particle_index%2+1)
                        f.write(line)
                        particle_index +=1
                except:
                    self.logger.warning("{} has invalid final result, skip it!".format(tomo))
    
    def assemble(self):
        params = self.get_assemble_params()
        if type(params) is str:
            self.logger.error(params)
        elif type(params) is dict:
            ret = QMessageBox.question(self, 'Reformatting!', \
                    "Continue?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
            if ret == QMessageBox.Yes:
                self.pushButton_assemble.setText("STOP")
                self.pushButton_assemble.setStyleSheet('QPushButton {color: red;}')
                self.logger.info("Start transform!")
                tomo_list = self.get_final_folder_list(params['expand_result_folder'])

                rotations = [params['rotation_x'],params['rotation_y'],params['rotation_z']]
                shifts = [params['recenter_x'], params['recenter_y'], params['recenter_z']]
                for tomo in tomo_list:
                    pts_file = "{}/{}_final/{}.pts".format(params['expand_result_folder'], tomo, tomo)
                    motl_file = "{}/{}_final/{}_InitMOTL.csv".format(params['expand_result_folder'], tomo, tomo)

                    coords_file = "{}/{}.coords".format(params['assemble_output_folder'], tomo)
                    euler_file = "{}/{}.euler".format(params['assemble_output_folder'], tomo)
                    
                    if not os.path.exists(motl_file):
                        motl_file = "{}/{}_final/{}_MOTL.csv".format(params['expand_result_folder'], tomo, tomo)

                    if os.path.exists(pts_file):
                        self.transform_coords_euler(tomo, pts_file, motl_file, coords_file, euler_file, shifts, rotations)
                    else:
                        self.logger.warning(".pts (coords) file {} is missing for tomogram {}, skip it!".format(pts_file, tomo))
                        continue
                self.combine_all(tomo_list, params['assemble_output_folder'], params["bin_factor"])
                self.logger.info("Done transform!")
                
                self.cmd_finished(self.pushButton_assemble)

    def get_placeback_params(self):
        if not len(self.lineEdit_data_star_file.text()) > 0:
            return "Please provide the data star file!"
        else:
            data_star_file = self.lineEdit_data_star_file.text()

        if not len(self.lineEdit_fitin_map_file.text()) > 0:
            return "Please provide the the fitin map!"
        else:
            fitin_map_file = self.lineEdit_fitin_map_file.text()

        if not len(self.lineEdit_tomo_name.text()) > 0:
            tomo_name = "all"
            #return "Please provide the tomogram name!"
        else:
            tomo_name = self.lineEdit_tomo_name.text()

        if len(self.lineEdit_pixel_size_unbinned.text()) > 0:
            if not string2float(self.lineEdit_pixel_size_unbinned.text()) == None:
                pixel_size_unbinned = string2float(self.lineEdit_pixel_size_unbinned.text())
            else:
                return "Please use the valid format for the unbinned pixel size!"
        else:
            return "Please provide the unbinned pixel size!"
        
        if len(self.lineEdit_pixel_size_fitin_map.text()) > 0:
            if not string2float(self.lineEdit_pixel_size_fitin_map.text()) == None:
                pixel_size_fitin_map = string2float(self.lineEdit_pixel_size_fitin_map.text())
            else:
                return "Please use the valid format for the unbinned pixel size!"
        else:
            return "Please provide the unbinned pixel size!"
        
        if len(self.lineEdit_unit_size_cxs.text()) > 0:
            if not string2float(self.lineEdit_unit_size_cxs.text()) == None:
                unit_size_cxs = string2float(self.lineEdit_unit_size_cxs.text())
            else:
                return "Please use the valid format for the repeating unit!"
        else:
            unit_size_cxs = 10000.0

        if len(self.lineEdit_min_num_neighbors.text()) > 0:
            if not string2int(self.lineEdit_min_num_neighbors.text()) == None:
                min_num_neighbors = string2int(self.lineEdit_min_num_neighbors.text())
            else:
                return "Please use the valid format for the min num of neighbors!"
        else:
            min_num_neighbors = 0

        if len(self.lineEdit_avg_angle.text()) > 0:
            if not string2float(self.lineEdit_avg_angle.text()) == None:
                avg_angle = string2float(self.lineEdit_avg_angle.text())
            else:
                return "Please use the valid format for the averaged angle to neighbors!"
        else:
            avg_angle = 180

        params = {}
        params['result_folder'] = "{}/placeback_result".format(self.others_folder)
        params['data_star_file'] = data_star_file
        params['fitin_map_file'] = fitin_map_file
        params['tomo_name'] = tomo_name
        params['pixel_size_unbinned'] = pixel_size_unbinned
        params['pixel_size_fitin_map'] = pixel_size_fitin_map
        params['unit_size_cxs'] = unit_size_cxs
        params['min_num_neighbors'] = min_num_neighbors
        params['avg_angle'] = avg_angle
        
        return params
    
    def generate_cxs_file(self, params):
        placeback_folder = "{}/PlaceBack".format(self.others_folder)
        if not os.path.exists(placeback_folder):
            mkfolder(placeback_folder)
        
        star_file = params['data_star_file']
        tomo_names = params['tomo_name']
        average_map = params['fitin_map_file']
        
        bin_factor = params['pixel_size_fitin_map']/params['pixel_size_unbinned']
        Min_neighbors = params['min_num_neighbors']
        Avg_angle_limit = params['avg_angle']

        with mrcfile.open(average_map) as mrcData:
            orig_data = mrcData.data.astype(np.float32)

        map_dimension = orig_data.shape

        dis_unit = params['unit_size_cxs']
        dis_ratio = 1.2

        apix = params['pixel_size_unbinned']

        try:
            df_particles = starfile.read(star_file,  always_dict=True)['particles']
        except:
            return -1
        
        if tomo_names.lower() == "all":
            try:
                tomoList = sorted(set(df_particles['rlnTomoName'].tolist()))
            except:
                return -1
        else:
            tomoList = [tomo_names]
        
        header = self.get_header(star_file)
        
        for tomo_name in tomoList:
            try:
                df_particles_i = df_particles.loc[df_particles['rlnTomoName']==tomo_name]
            except:
                self.logger.error("No particle was found for tomogame: {}!".format(tomo_name))
                return -1
            df_particles_i = df_particles_i.reset_index()

            manifoldIndex_start = df_particles_i['rlnTomoManifoldIndex'].astype(int).min()
            manifold_num = df_particles_i['rlnTomoManifoldIndex'].astype(int).max() - manifoldIndex_start + 1
            
            average_map_basename = os.path.basename(average_map)
            try:
                if not os.path.exists("{}/{}".format(placeback_folder, average_map_basename)):
                    shutil.copy(average_map, placeback_folder)
            except:
                pass
        
            global_id = 0
            real_patch_num = 0
            clean_i = 0
            
            output_file_name = "{}/placeback_tomo_{}.cxc".format(placeback_folder, tomo_name)
            clean_version_star = "{}/clean_tomo_{}.star".format(placeback_folder, tomo_name)

            if not manifold_num or math.isnan(manifold_num):
                self.logger.warning("No Tomo Name: {}.".format(tomo_name))
                return 0
            else:
                with open(output_file_name, "w") as outfile:
                    with open(clean_version_star, "w") as c_star_file:
                        for i in range(int(manifold_num)):
                            current_manifold_id = manifoldIndex_start+i
                            manifold_df = df_particles_i.loc[df_particles_i['rlnTomoManifoldIndex']==current_manifold_id]
                            manifold_df = manifold_df.reset_index()
                            pNum_i = manifold_df.shape[0]
                            if pNum_i > 0:
                                real_patch_num+=1
                                global_id+=pNum_i
                                
                                open_line = "open"
                                move_cmds = ""
                                turn_cmds = ""

                                centers = []
                                new_vectors = []

                                for j in range(pNum_i):
                                    
                                    xp, yp, zp = [manifold_df['rlnCoordinateX'][j], manifold_df['rlnCoordinateY'][j], manifold_df['rlnCoordinateZ'][j]]
                                    xt, yt, zt = [manifold_df['rlnOriginXAngst'][j], manifold_df['rlnOriginYAngst'][j], manifold_df['rlnOriginZAngst'][j]]
                                    rot, tilt, psi = [manifold_df['rlnAngleRot'][j], manifold_df['rlnAngleTilt'][j], manifold_df['rlnAnglePsi'][j]]
                                    
                                    output_eulers, output_vector = Relion2ChimeraX(np.array([rot, tilt, psi]))

                                    x = round(xp*apix + xt,3)
                                    y = round(yp*apix + yt,3)
                                    z = round(zp*apix + zt,3)

                                    centers.append([x,y,z])
                                    new_vectors.append([output_vector[0],output_vector[1],output_vector[2]])

                                    if pNum_i == 1:
                                        model_id = "{}".format(real_patch_num, j+1)
                                    else:
                                        model_id = "{}.{}".format(real_patch_num, j+1)
                                    
                                    open_line = "{} {}".format(open_line, average_map_basename)

                                    move_cmds = "{}move x {} models #{}; move y {} models #{}; move z {} models #{};\n"\
                                                .format(move_cmds, x, model_id, y, model_id, z, model_id)
                                    
                                    turn_cmds = "{}turn z {} center 0,0,0 models #{} coordinateSystem #{}; turn y {} center 0,0,0 models #{} coordinateSystem #{}; turn z {} center 0,0,0  models #{} coordinateSystem #{};\n"\
                                                .format(turn_cmds, output_eulers[0], model_id, model_id, output_eulers[1], model_id, model_id, \
                                                    output_eulers[2], model_id, model_id)

                                mat_coords = np.array(distance_matrix(centers, centers))
                                mat_norm = squareform(pdist(new_vectors, "cosine"))
                                
                                color_cmds = ""

                                for j in range(pNum_i):
                                    
                                    neignbors = getNeighbors(mat_coords[j], j, dis_unit*dis_ratio)
                                    sum = 0
                                    max_angle = 0
                                    avg_angle = 0
                                    for n in neignbors:		
                                        sum += math.acos(1-mat_norm[j][n])/math.pi*180
                                        max_angle = max(max_angle, math.acos(1-mat_norm[j][n])/math.pi*180)
                                    if len(neignbors) > 0:
                                        avg_angle =  sum/len(neignbors)

                                    #r,g,b = getRGBs(avg_angle, max_angle=30)
                                    r,g,b = getRGBs(avg_angle, max_angle= Avg_angle_limit)
                                    
                                    ## TEST ## save only largely curved region
                                    #if len(neignbors) >= Min_neighbors and avg_angle >= Avg_angle_limit:
                                    ## TEST ## save based on max angle
                                    #if len(neignbors) >= Min_neighbors and max_angle <= Avg_angle_limit:
                                    ## TEST ## save based on side/top view
                                    # if Avg_angle_limit >= 0:
                                    #     test_bool = abs(new_vectors[j][2]) >= Avg_angle_limit
                                    # else:
                                    #     test_bool = abs(new_vectors[j][2]) <= -Avg_angle_limit
                                    
                                    # if len(neignbors) >= Min_neighbors and test_bool:
                                        
                                    # original setting
                                    if len(neignbors) >= Min_neighbors and avg_angle <= Avg_angle_limit:
                                        c_star_line = " ".join([str(x) for x in manifold_df.loc[j].values.flatten().tolist()][2:]) + "\n"
                                        c_star_file.write(c_star_line)
                                        clean_i+=1
                                    if pNum_i == 1:
                                        model_id = "{}".format(real_patch_num, j+1)
                                    else:
                                        model_id = "{}.{}".format(real_patch_num, j+1)

                                    color_cmds = "{}color #{} rgb({},{},{});\n".format(color_cmds, model_id, r, g, b)

                                recenter_line = "vop #{} originIndex {},{},{};\n".format(real_patch_num, map_dimension[2]/2, map_dimension[1]/2, map_dimension[0]/2)
                                
                                outfile.write(open_line+";\n\n")
                                outfile.write(recenter_line+"\n")
                                outfile.write(move_cmds+"\n")
                                outfile.write(turn_cmds+"\n")
                                outfile.write(color_cmds+"\n")

                    outfile.write("view\n")  

                self.logger.info("Original: {}; Clean version: {}.".format(global_id, clean_i))
                self.logger.info("Done getting placeback session file for ChimeraX: {}!".format(tomo_name))

        if len(tomoList) > 1:
            clean_version_star_all = "{}/particles_clean_all.star".format(placeback_folder)
            with open (clean_version_star_all, 'w') as w:
                w.write(header)
            for tomo_name in tomoList:
                starfile_i = "{}/clean_tomo_{}.star".format(placeback_folder, tomo_name)
                if os.path.exists(starfile_i):
                    cmd = "cat {} >> {}".format(starfile_i, clean_version_star_all)
                    subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
            
            self.logger.info("clean version of STAR file saved: {}!".format(clean_version_star_all))
            

    def get_header(self, star_file):
        header = ""
        with open(star_file, 'r') as f:
            lines = f.readlines()
            start_particle_header = False
            start_particle_header_rln = False
            for line in lines:
                if not start_particle_header:
                    header += line
                    if line.startswith("data_particles"):
                        start_particle_header = True
                else:
                    if not start_particle_header_rln:
                        header += line
                        if line.startswith("_rln"):
                            start_particle_header_rln = True
                    else:
                        if not line.startswith("_rln"):
                            break
                        else:
                            header += line
        return header 
    
    def placeback(self):
        params = self.get_placeback_params()
        if type(params) is str:
            self.logger.error(params)
        elif type(params) is dict:
            ret = QMessageBox.question(self, 'Get placeback ChimeraX session!', \
                    "Continue?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)   
            if ret == QMessageBox.Yes:
                self.pushButton_place_back.setText("STOP")
                self.pushButton_place_back.setStyleSheet('QPushButton {color: red;}')
                
                result = self.generate_cxs_file(params)

                # if result == 1:
                #     self.logger.info("Done getting placeback session file for ChimeraX: {}!".format(params['tomo_name']))
                # elif result == -1:
                #     self.logger.error("No particle was found for tomogame: {}!".format(params['tomo_name']))
                # else:
                #     self.logger.error("Unexpected error for tomogame: {}!".format(params['tomo_name']))
                
                self.cmd_finished(self.pushButton_place_back)
    
    def get_star2PEET_params(self):
        
        if not len(self.lineEdit_input_star_file.text()) > 0:
            return "Please specify the input star file!"
        else:
            input_star_file = self.lineEdit_input_star_file.text()
            if not os.path.exists(input_star_file):
                return "The input star file does not exist!"

        if not len(self.lineEdit_star2PEET_output_folder.text()) > 0:
            return "Please specify the STAR2PEET result folder!"
        else:
            star2PEET_output_folder = "{}/{}".format(self.others_folder, self.lineEdit_star2PEET_output_folder.text())

        if len(self.lineEdit_star2PEET_bin_factor.text()) > 0:
            if not string2float(self.lineEdit_star2PEET_bin_factor.text()) == None:
                star2PEET_bin_factor = string2float(self.lineEdit_star2PEET_bin_factor.text())
            else:
                return "Please use the valid format for the bin factor!"
        else:
            star2PEET_bin_factor = 4

        if len(self.lineEdit_star2PEET_apix.text()) > 0:
            if not string2float(self.lineEdit_star2PEET_apix.text()) == None:
                star2PEET_apix = string2float(self.lineEdit_star2PEET_apix.text())
            else:
                return "Please use the valid format for the the pixel size!"
        else:
            star2PEET_apix = 1.0  

        if not os.path.exists(star2PEET_output_folder):
            mkfolder(star2PEET_output_folder)

        params = {}
        params['input_star_file'] = input_star_file
        params['star2PEET_output_folder'] = star2PEET_output_folder
        params['star2PEET_bin_factor'] = star2PEET_bin_factor
        params['star2PEET_apix'] = star2PEET_apix

        return params
    
    def generate_PEET_files(self, params):
        input_star_file = params['input_star_file']
        output_folder = params['star2PEET_output_folder'] 
        bin_factor = params['star2PEET_bin_factor']
        apix = params['star2PEET_apix']
        peet_motl_header = "CCC,reserved,reserved,pIndex,wedgeWT,NA,NA,NA,NA,NA,xOffset,yOffset,zOffset,NA,NA,reserved,EulerZ(1),EulerZ(3),EulerX(2),reserved,CREATED WITH PEET Version 1.15.0 10-January-2021\n"

        try:
            df_particles = starfile.read(input_star_file,  always_dict=True)['particles']
        except:
            self.logger.info("Encountering improper format of particle STAR file: {}".format(input_star_file))
            return -1
        try:
            tomoList = sorted(set(df_particles['rlnTomoName'].tolist()))
        except:
            self.logger.info("Encountering improper format of particle STAR file: {}".format(input_star_file))
            return -1
        
        for tomo_name in tomoList:
            try:
                df_particles_current = df_particles.loc[df_particles['rlnTomoName']==tomo_name]
            except:
                self.logger.info("Encountering improper format of particle STAR file: {}".format(input_star_file))
                return -1
            
            df_particles_current = df_particles_current.reset_index()
            num_par = df_particles_current.shape[0]
            
            pts_file = "{}/{}.pts".format(output_folder, tomo_name)
            mod_file = "{}/{}.mod".format(output_folder, tomo_name)
            motl_file = "{}/{}_MOTL.csv".format(output_folder, tomo_name)
            rotAxis_file = "{}/{}_RotAxes.csv".format(output_folder, tomo_name)

            with open(pts_file, "w") as fp:
                with open(motl_file, "w") as fm:
                    with open(rotAxis_file, "w") as fr:
                        fm.write(peet_motl_header)
                        for i in range(num_par):
                            xp, yp, zp = [df_particles_current['rlnCoordinateX'][i], df_particles_current['rlnCoordinateY'][i], df_particles_current['rlnCoordinateZ'][i]]
                            xt, yt, zt = [df_particles_current['rlnOriginXAngst'][i], df_particles_current['rlnOriginYAngst'][i], df_particles_current['rlnOriginZAngst'][i]]
                            rot, tilt, psi = [df_particles_current['rlnAngleRot'][i], df_particles_current['rlnAngleTilt'][i], df_particles_current['rlnAnglePsi'][i]]

                            output_eulers, output_vector = Relion2PEET(np.array([rot, tilt, psi]))

                            x_coords_binned = int(round(xp*apix + xt,3)/apix/bin_factor)
                            y_coords_binned = int(round(yp*apix + yt,3)/apix/bin_factor)
                            z_coords_binned = int(round(zp*apix + zt,3)/apix/bin_factor)

                            fp.write("{} {} {}\n".format(x_coords_binned, y_coords_binned, z_coords_binned))
                            motl_line = "1,0,0,{},1,0,0,0,0,0,0,0,0,0,0,0,{},{},{},0 \n".format(i+1, output_eulers[0],output_eulers[2],output_eulers[1])
                            fm.write(motl_line)
                            fr.write("{},{},{}\n".format(output_vector[0], output_vector[1], output_vector[2]))


            cmd = "point2model {} {} -scat -sphere 5 ".format(pts_file, mod_file)
            subprocess.run(cmd,shell=True, stdout=subprocess.PIPE)
            self.logger.info("Done STAR2PEET for {}. Total particle # {}.".format(tomo_name, num_par))

    def star2PEET(self):
        params = self.get_star2PEET_params()
        if type(params) is str:
            self.logger.error(params)
        elif type(params) is dict:
            ret = QMessageBox.question(self, 'Generating PEET parameter files', \
                    "Continue?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)   
            if ret == QMessageBox.Yes:
                self.pushButton_star2PEET.setText("STOP")
                self.pushButton_star2PEET.setStyleSheet('QPushButton {color: red;}')
                
                self.generate_PEET_files(params)
                
                self.cmd_finished(self.pushButton_star2PEET)

    def cmd_finished(self, button, text="RUN"):
        button.setText(text)
        button.setStyleSheet("QPushButton {color: black;}")