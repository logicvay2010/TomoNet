import os, subprocess, json, logging
import glob
import numpy as np
from ast import literal_eval

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTabWidget, QHeaderView, QMessageBox, QTableWidgetItem

from TomoNet.util import metadata, browse
from TomoNet.util.metadata import MetaData, Item, Label
from TomoNet.util.utils import mkfolder, check_log_file, getLogContent, string2float, string2int, idx2list
from TomoNet.util.searchParam import SearchParam
from TomoNet.process.bash_expand import Expand_CMDS

class Expand(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="Expand/expand.setting"
        
        self.log_file = "Expand/expand.log"

        self.expand_folder = "Expand"

        self.initParams_folder = "ManualPick"
        
        self.recon_root_folder = "Recon"
        
        check_log_file(self.log_file, "Expand")
        
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
        
        self.addTab(self.tab, "Generate tomograms.star")

        self.addTab(self.tab2, "Generate Picking Parameter")

        self.addTab(self.tab3, "Run Particle Expansion")

        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)

        self.checkBox_mask.stateChanged.connect(self.save_setting)
        self.checkBox_print_only_expand_select.stateChanged.connect(self.save_setting)

        self.checkBox_mask.stateChanged.connect(lambda state: self.lineEdit_mask.setDisabled(not state))
        self.checkBox_mask.stateChanged.connect(lambda state: self.pushButton_mask.setDisabled(not state))

        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        self.pushButton_initParam_folder.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_initParam_folder, location=self.initParams_folder)) 
        self.pushButton_recon_folder.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_recon_folder, location=self.recon_root_folder)) 
        # self.pushButton_expand_folder.clicked.connect\
        #     (lambda: browse.browseFolderSlot(self.lineEdit_expand_folder)) 
        
        self.pushButton_load_params.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_load_params, 'params', location=self.expand_folder)) 
        self.pushButton_reference.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_reference, 'map', location=".")) 
        self.pushButton_mask.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_mask, 'map', location=".")) 
        
        self.pushButton_star_file_to_use.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_star_file_to_use, 'star', location=self.expand_folder)) 
        self.pushButton_pick_param_file_to_use.clicked.connect\
            (lambda: browse.browseSlot(self.lineEdit_pick_param_file_to_use, 'params', location=self.expand_folder)) 
        self.pushButton_expand_folder_to_use.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_expand_folder_to_use, location=self.expand_folder)) 


        self.pushButton_prepare.clicked.connect(self.prepare_star_file)
        self.pushButton_generate_pick_params.clicked.connect(self.generate_pick_param_file)
        self.pushButton_expand_select.clicked.connect(self.expand_select)
        
        self.lineEdit_star_file_to_use.textChanged.connect(self.reload_table)
        self.lineEdit_load_params.textChanged.connect(self.reload_params)
        self.lineEdit_expand_folder_to_use.textChanged.connect(self.reload_table)
        self.currentChanged.connect(self.tab_changed)

        self.tableView.doubleClicked.connect(self.table_click)

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.retranslateUi_tab1()
        self.retranslateUi_tab2()
        self.retranslateUi_tab3()
        self.read_settting()

    def retranslateUi_tab1(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_initParam_folder.setText(_translate("Form", "Initial Picking File Folder:"))
        self.label_initParam_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Manual/initParams generated by TomoNet.\
            </span></p></body></html>"))
        
        self.lineEdit_initParam_folder.setPlaceholderText(_translate("Form", "Manual/initParams"))
        self.lineEdit_initParam_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Manual/initParams generated by TomoNet.\
            </span></p></body></html>"))
        
        self.label_recon_folder.setText(_translate("Form", "Tomo Reconstruction Folder:"))
        self.label_recon_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Recon/eTomo generated by TomoNet.\
            </span></p></body></html>"))
        
        self.lineEdit_recon_folder.setPlaceholderText(_translate("Form", "Recon/eTomo"))
        self.lineEdit_recon_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Recon/eTomo generated by TomoNet. Leave this empty if not available\
            </span></p></body></html>"))
        
        self.label_tomo_star_file_name.setText(_translate("Form", "Output Filename:"))
        self.label_tomo_star_file_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: tomograms.star.\
            </span></p></body></html>"))
        
        self.lineEdit_tomo_star_file_name.setPlaceholderText(_translate("Form", "tomograms.star"))
        self.lineEdit_tomo_star_file_name.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: For example: tomograms.star.\
            </span></p></body></html>"))
        
        self.label_expand_folder.setText(_translate("Form", "Expand Folder Name:"))
        self.label_expand_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">By default: Expand. However, if you want to run different setting without overwriting the previous results. Please specify another folder path here.\
            </span></p></body></html>"))
        
        self.lineEdit_expand_folder.setPlaceholderText(_translate("Form", "result_1"))
        self.lineEdit_expand_folder.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">By default: Expand. However, if you want to run different setting without overwriting the previous results. Please specify another folder path here.\
            </span></p></body></html>"))
        
        self.pushButton_prepare.setText(_translate("Form", "Prepare"))

    def retranslateUi_tab2(self):
        _translate = QtCore.QCoreApplication.translate
        
        self.label_load_params.setText(_translate("Form", "Load picking params:"))      
        self.lineEdit_load_params.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_load_params.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Load secific param setting (.params file) </span></p></body></html>"))

        self.label_rotRange.setText(_translate("Form", "First round search range:"))
        self.label_rotRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The ± angular search setting for the first round expand, normally set large search range in the first round for global serach.</span></p></body></html>"))
        
        self.lineEdit_rotRange.setPlaceholderText(_translate("Form", "60,60,60"))
        self.lineEdit_rotRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format rx,ry,rz or r. rx, ry, rz are the ± angular search ranges around x, y, z-axis respectively. For example 15,60,15 for c3 symmetry structure</span></p></body></html>"))
        
        self.label_rot_steps.setText(_translate("Form", "Search steps:"))
        self.label_rot_steps.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The angular search steps for x,y,z-axis respectively, related to the search ranges. </span></p></body></html>"))
        
        self.lineEdit_rot_steps.setPlaceholderText(_translate("Form", "2,2,2"))
        self.lineEdit_rot_steps.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format sx,sy,sz or s. sx, sy, sz are the angular search range steps around x, y, z-axis respectively.</span></p></body></html>"))
        
        
        self.label_fineRotRange.setText(_translate("Form", "Later rounds search range:"))
        self.label_fineRotRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The angular search setting for the later rounds expand, normally set small search range in the later round for local serach.\
            </span></p></body></html>"))
        
        self.lineEdit_fineRotRange.setPlaceholderText(_translate("Form", "12,12,12"))
        self.lineEdit_fineRotRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format rx,ry,rz or r. rx, ry, rz are the angular search range around x,y,z axis respectively. </span></p></body></html>"))
        
        self.label_fineRot_steps.setText(_translate("Form", "Search steps:"))
        self.label_fineRot_steps.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The angular search steps for x,y,z-axis respectively, related to the fine search ranges. </span></p></body></html>"))
        
        self.lineEdit_fineRot_steps.setPlaceholderText(_translate("Form", "2,2,2"))
        self.lineEdit_fineRot_steps.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format sx,sy,sz or s. sx, sy, sz are the angular search range steps around x, y, z-axis respectively.</span></p></body></html>"))

        self.groupBox_1.setTitle("Angular search (in degree)")
        self.groupBox_1.setFlat(False)
        
        self.label_transRange.setText(_translate("Form", "First round search range:"))
        self.label_transRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The translational search setting for the first round expand, normally set large search range in the first round for global serach.\
            The search step will be 1 pixel. </span></p></body></html>"))
        
        self.lineEdit_transRange.setPlaceholderText(_translate("Form", "8,8,8"))
        self.lineEdit_transRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format tx,ty,tz or t. tx, ty, tz are the translational search range along x,y,z-axis respectively. </span></p></body></html>"))
        
        self.label_fineTransRange.setText(_translate("Form", "Later rounds search range:"))
        self.label_fineTransRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The translational search setting for the later rounds expand, normally set small search range in the later round for fine serach.\
            The search step will be 1 pixel. </span></p></body></html>"))
        
        self.lineEdit_fineTransRange.setPlaceholderText(_translate("Form", "5,5,5"))
        self.lineEdit_fineTransRange.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format tx,ty,tz or t. tx, ty, tz are the translational search range along x,y,z-axis respectively. </span></p></body></html>"))

        self.label_transition_list.setText(_translate("Form", "Transition List:"))
        self.label_transition_list.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The list of transitions from one unit center to its neighbors. \
                For example, a c6 symmetry center should has 6 transitions to it's 6 neighbors respectively.</span></p></body></html>"))
        
        self.lineEdit_transition_list.setPlaceholderText(_translate("Form", "[10,10,10], [-10,-10,-10]"))
        self.lineEdit_transition_list.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format [x1,y1,z1],...,[xn,yn,zn]. [xn,yn,zn] is the transition vector from the center to its nth neighbor. \
                For example, in your reference map, the nth neighbor's coords are cn_x, cn_y, cn_z and the origin center coords are c_x, c_y, c_z, \
                    then xn = cn_x - c_x, yn = cn_y - c_y, zn = cn_z - c_z. </span></p></body></html>"))

        self.groupBox_2.setTitle("Translational search (in pixel)")
        self.groupBox_2.setFlat(False)

        self.label_boxSize.setText(_translate("Form", "Box size:"))
        self.label_boxSize.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The volume size used for CCC calculation (template match).\
            </span></p></body></html>"))
        
        self.lineEdit_boxSize.setPlaceholderText(_translate("Form", "80,80,80"))
        self.lineEdit_boxSize.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">general format nx,ny,nz, where nx,ny,nz denote the pixels in each dimension. </span></p></body></html>"))
        

        self.label_repeating_unit.setText(_translate("Form", "Repeating Unit (Å):"))
        self.label_repeating_unit.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">This is based on user's observation or prior knowledge. .\
            </span></p></body></html>"))
        
        self.lineEdit_repeating_unit.setPlaceholderText(_translate("Form", "120"))
        self.lineEdit_repeating_unit.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Distance between neighboring particles </span></p></body></html>"))

        self.label_threshold_CCC.setText(_translate("Form", "CCC threshold:"))
        self.label_threshold_CCC.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Particles have less than this defined CCC value comparing with the reference will be excluded.\
            </span></p></body></html>"))
        
        self.lineEdit_threshold_CCC.setPlaceholderText(_translate("Form", "0.1"))
        self.lineEdit_threshold_CCC.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Particles have less than this defined CCC value comparing with the reference will be excluded. </span></p></body></html>"))
        
        self.label_max_seed_num.setText(_translate("Form", "Max initial seed #:"))
        
        self.lineEdit_max_seed_num.setPlaceholderText(_translate("Form", "200"))
        self.lineEdit_max_seed_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Maximum seeds number at Iteration 0. This can be used to speed up the calculation by clustering you input seed particles into Max_# representive particles.\
            Can be useful when the seed particle set is already crowded. For example after AutoPicking, then you want to add the missed particles. (Default 200) </span></p></body></html>"))

        self.label_reference.setText(_translate("Form", "Reference:"))
        self.label_reference.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Refefence map for template match search. \
            </span></p></body></html>"))
        
        self.lineEdit_reference.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Refefence map for template match search. </span></p></body></html>"))
        
        self.label_mask.setText(_translate("Form", "Use Mask?:"))
        self.label_mask.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Mask can be used to perform masked template search. (optional)\
            </span></p></body></html>"))
        
        self.lineEdit_mask.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_mask.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Mask can be used to perform masked template search. (optional, check the checkbox to enable this) </span></p></body></html>"))
        
        self.label_refine_reference.setText(_translate("Form", "Refine reference?:"))


        self.comboBox_refine_reference.setItemText(0, _translate("Form", "Yes"))
        self.comboBox_refine_reference.setItemText(1, _translate("Form", "No"))
        self.comboBox_refine_reference.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" font-size:9pt;\">\
            No: equal to template matching, the reference will stay the same for all iterations; Yes: reference will be replaced by the reconstruction result from each iterations.\
            </span></p></body></html>"))

        self.label_min_count_to_continue.setText(_translate("Form", "Min seed particle # per expansion:"))
        self.lineEdit_min_count_to_continue.setPlaceholderText(_translate("Form", "5"))
        self.lineEdit_min_count_to_continue.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Before each expansion, the current round seed particles will be counted. \
                if under the specific number, then Expansion will end early. Thus, please use number between 1 to your initial seed particle#. (default 5) </span></p></body></html>"))
        
        self.label_pick_param_filename.setText(_translate("Form", "Output filename:"))
        self.label_pick_param_filename.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Output filename for saving the picking params.\
            </span></p></body></html>"))
        
        self.lineEdit_pick_param_filename.setPlaceholderText(_translate("Form", "pick.params"))
        self.lineEdit_pick_param_filename.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"> Output filename for saving the picking params. </span></p></body></html>"))

        self.groupBox_3.setTitle("Other Inputs")
        self.groupBox_3.setFlat(False)

        self.pushButton_generate_pick_params.setText(_translate("Form", "Generate"))

    def retranslateUi_tab3(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_star_file_to_use.setText(_translate("Form", "Tomogram star file:"))
        self.label_star_file_to_use.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">input file path: tomograms.star.\
            </span></p></body></html>"))
        
        self.lineEdit_star_file_to_use.setPlaceholderText(_translate("Form", "Expand/tomograms.star"))
        self.lineEdit_star_file_to_use.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Expand/tomograms.star generated by TomoNet.\
            </span></p></body></html>"))
        
        self.label_pick_param_file_to_use.setText(_translate("Form", "Pick params file:"))
        self.label_pick_param_file_to_use.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">pick params file path: pick.params.\
            </span></p></body></html>"))
        
        self.lineEdit_pick_param_file_to_use.setPlaceholderText(_translate("Form", "Expand/pick.params"))
        self.lineEdit_pick_param_file_to_use.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Expand/pick.params generated by TomoNet.\
            </span></p></body></html>"))
        
        self.label_expand_folder_to_use.setText(_translate("Form", "Select Expand Folder:"))
        self.label_expand_folder_to_use.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Select which folder to perform expand operation.\
            </span></p></body></html>"))
        
        self.lineEdit_expand_folder_to_use.setPlaceholderText(_translate("Form", "Expand"))
        self.lineEdit_expand_folder_to_use.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">For example: Expand_0526.\
            </span></p></body></html>"))
        
        self.label_tomo_index.setText(_translate("Form", "Select Tomo Index:"))
        self.label_tomo_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Select which tomograms to perform expand operation.\
            </span></p></body></html>"))
        
        self.lineEdit_tomo_index.setPlaceholderText(_translate("Form", "1-5,7-8,12"))
        self.lineEdit_tomo_index.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"font-size:9pt;\"> different tomo indexes are seperated by comma, sequential indexes are connected by dash. \
            </span></p></body></html>"))
        
        self.label_iterations.setText(_translate("Form", "Rounds:"))
        self.label_iterations.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Number of rounds to be performed this time. Large size lattice required more rounds to exhaust all possiable particles.\
            </span></p></body></html>"))
        
        self.lineEdit_iterations.setPlaceholderText(_translate("Form", "7"))
        self.lineEdit_iterations.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"font-size:9pt;\"> Integer. Number of rounds to be performed this time. Large size lattice required more rounds to exhaust all possiable particles. \
            </span></p></body></html>"))
        
        self.label_min_patch_size.setText(_translate("Form", "Min Patch Size:"))
        self.label_min_patch_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\"></span></p></body></html>"))
        
        self.lineEdit_min_patch_size.setPlaceholderText(_translate("Form", "12"))
        self.lineEdit_min_patch_size.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"font-size:9pt;\"> Minimum particle numbers for a patch. \
            </span></p></body></html>"))
        
        self.label_cpu_num.setText(_translate("Form", "CPU #:"))
        self.label_cpu_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Number of CPUs to be used.\
            </span></p></body></html>"))
        
        self.lineEdit_cpu_num.setPlaceholderText(_translate("Form", "20"))
        self.lineEdit_cpu_num.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\"font-size:9pt;\"> Integer. Number of CPUs to be used. \
            </span></p></body></html>"))
        
        self.label_print_only_expand_select.setText(_translate("Form", "print cmd only"))
        self.label_print_only_expand_select.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Only print cmd line format for submitting jobs to remote clusters.\
            </span></p></body></html>"))
        
        self.pushButton_expand_select.setText(_translate("Form", "RUN"))
              
    def setUI_tab1(self):
        #tab 1
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 5, 10, 5)

        self.label_initParam_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_initParam_folder.sizePolicy().hasHeightForWidth())
        self.label_initParam_folder.setSizePolicy(sizePolicy)
        self.label_initParam_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_initParam_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_initParam_folder.setObjectName("label_initParam_folder")
        self.horizontalLayout_1.addWidget(self.label_initParam_folder)

        self.lineEdit_initParam_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_initParam_folder.setInputMask("")
        self.lineEdit_initParam_folder.setObjectName("lineEdit_initParam_folder")

        self.horizontalLayout_1.addWidget(self.lineEdit_initParam_folder)

        self.pushButton_initParam_folder = QtWidgets.QPushButton(self.tab)
        self.pushButton_initParam_folder.setText("")
        self.pushButton_initParam_folder.setIcon(self.icon)
        self.pushButton_initParam_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_initParam_folder.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_initParam_folder.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_initParam_folder.setObjectName("pushButton_initParam_folder")
        self.horizontalLayout_1.addWidget(self.pushButton_initParam_folder)

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(10, 5, 10, 5)

        self.label_recon_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_recon_folder.sizePolicy().hasHeightForWidth())
        self.label_recon_folder.setSizePolicy(sizePolicy)
        self.label_recon_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_recon_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_recon_folder.setObjectName("label_recon_folder")
        self.horizontalLayout_2.addWidget(self.label_recon_folder)

        self.lineEdit_recon_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_recon_folder.setInputMask("")
        self.lineEdit_recon_folder.setObjectName("lineEdit_recon_folder")

        self.horizontalLayout_2.addWidget(self.lineEdit_recon_folder)

        self.pushButton_recon_folder = QtWidgets.QPushButton(self.tab)
        self.pushButton_recon_folder.setText("")
        self.pushButton_recon_folder.setIcon(self.icon)
        self.pushButton_recon_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_recon_folder.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_recon_folder.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_recon_folder.setObjectName("pushButton_recon_folder")
        self.horizontalLayout_2.addWidget(self.pushButton_recon_folder)
        
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(10, 5, 10, 5)

        self.label_expand_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_expand_folder.sizePolicy().hasHeightForWidth())
        self.label_expand_folder.setSizePolicy(sizePolicy)
        self.label_expand_folder.setMinimumSize(QtCore.QSize(60, 0))
        self.label_expand_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_expand_folder.setObjectName("label_expand_folder")
        self.horizontalLayout_3.addWidget(self.label_expand_folder)

        self.lineEdit_expand_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_expand_folder.setInputMask("")
        self.lineEdit_expand_folder.setObjectName("lineEdit_expand_folder")

        self.horizontalLayout_3.addWidget(self.lineEdit_expand_folder)
        
        self.label_tomo_star_file_name = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_tomo_star_file_name.sizePolicy().hasHeightForWidth())
        self.label_tomo_star_file_name.setSizePolicy(sizePolicy)
        self.label_tomo_star_file_name.setMinimumSize(QtCore.QSize(120, 0))
        self.label_tomo_star_file_name.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_star_file_name.setObjectName("label_tomo_star_file_name")
        self.horizontalLayout_3.addWidget(self.label_tomo_star_file_name)

        self.lineEdit_tomo_star_file_name = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_tomo_star_file_name.setInputMask("")
        self.lineEdit_tomo_star_file_name.setObjectName("lineEdit_tomo_star_file_name")

        self.horizontalLayout_3.addWidget(self.lineEdit_tomo_star_file_name)

        # self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        # self.horizontalLayout_4.setContentsMargins(10, 5, 10, 5)
        
        # self.pushButton_expand_folder = QtWidgets.QPushButton(self.tab)
        # self.pushButton_expand_folder.setText("")
        # self.pushButton_expand_folder.setIcon(self.icon)
        # self.pushButton_expand_folder.setIconSize(QtCore.QSize(24, 24))
        # self.pushButton_expand_folder.setMaximumSize(QtCore.QSize(160, 24))
        # self.pushButton_expand_folder.setMinimumSize(QtCore.QSize(60, 24))
        # self.pushButton_expand_folder.setObjectName("pushButton_expand_folder")
        # self.horizontalLayout_4.addWidget(self.pushButton_expand_folder)

        self.horizontalLayout_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last.setObjectName("horizontalLayout_last")
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem1)
        self.pushButton_prepare = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_prepare.sizePolicy().hasHeightForWidth())
        self.pushButton_prepare.setSizePolicy(sizePolicy)
        self.pushButton_prepare.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_prepare.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_prepare.setObjectName("run")
        self.horizontalLayout_last.addWidget(self.pushButton_prepare)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem2)

        self.gridLayout_prepare = QtWidgets.QGridLayout(self.tab)

        self.gridLayout_prepare.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)
        self.gridLayout_prepare.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)
        # self.gridLayout_prepare.addLayout(self.horizontalLayout_4, 3, 0, 1, 1)

        self.spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_prepare.addItem(self.spacerItem3, 4, 0, 1, 1)

        self.gridLayout_prepare.addLayout(self.horizontalLayout_last, 5, 0, 1, 1)

    def setUI_tab2(self):
        self.tab2 = QtWidgets.QWidget()
        self.tab2.setObjectName("tab")

        self.horizontalLayout_2_0 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_0.setContentsMargins(10, 5, 10, 5)
        
        self.label_load_params = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_load_params.sizePolicy().hasHeightForWidth())
        self.label_load_params.setSizePolicy(sizePolicy)
        self.label_load_params.setMinimumSize(QtCore.QSize(60, 0))
        self.label_load_params.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_load_params.setObjectName("label_load_params")
        self.horizontalLayout_2_0.addWidget(self.label_load_params)

        self.lineEdit_load_params = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_load_params.setInputMask("")
        self.lineEdit_load_params.setObjectName("lineEdit_load_params")

        self.horizontalLayout_2_0.addWidget(self.lineEdit_load_params)

        self.pushButton_load_params = QtWidgets.QPushButton(self.tab2)
        self.pushButton_load_params.setText("")
        self.pushButton_load_params.setIcon(self.icon)
        self.pushButton_load_params.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_load_params.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_load_params.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_load_params.setObjectName("pushButton_load_params")
        self.horizontalLayout_2_0.addWidget(self.pushButton_load_params)

        self.groupBox_1 = QtWidgets.QGroupBox()

        self.verticalLayout_2_1 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2_1.setContentsMargins(5, 5, 5, 5)

        self.horizontalLayout_2_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_1.setContentsMargins(10, 5, 10, 5)

        self.label_rotRange = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_rotRange.sizePolicy().hasHeightForWidth())
        self.label_rotRange.setSizePolicy(sizePolicy)
        self.label_rotRange.setMinimumSize(QtCore.QSize(120, 0))
        self.label_rotRange.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_rotRange.setObjectName("label_rotRange")
        self.horizontalLayout_2_1.addWidget(self.label_rotRange)

        self.lineEdit_rotRange = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_rotRange.setInputMask("")
        self.lineEdit_rotRange.setObjectName("lineEdit_rotRange")

        self.horizontalLayout_2_1.addWidget(self.lineEdit_rotRange)

        self.label_rot_steps = QtWidgets.QLabel(self.tab2)
        self.label_rot_steps.setSizePolicy(sizePolicy)
        self.label_rot_steps.setMinimumSize(QtCore.QSize(120, 0))
        self.label_rot_steps.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_rot_steps.setObjectName("label_rot_steps")
        self.horizontalLayout_2_1.addWidget(self.label_rot_steps)

        self.lineEdit_rot_steps = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_rot_steps.setInputMask("")
        self.lineEdit_rot_steps.setObjectName("lineEdit_rot_steps")

        self.horizontalLayout_2_1.addWidget(self.lineEdit_rot_steps)

        self.horizontalLayout_2_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_2.setContentsMargins(10, 5, 10, 5)

        self.label_fineRotRange = QtWidgets.QLabel(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_fineRotRange.sizePolicy().hasHeightForWidth())
        self.label_fineRotRange.setSizePolicy(sizePolicy)
        self.label_fineRotRange.setMinimumSize(QtCore.QSize(120, 0))
        self.label_fineRotRange.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_fineRotRange.setObjectName("label_fineRotRange")
        self.horizontalLayout_2_2.addWidget(self.label_fineRotRange)

        self.lineEdit_fineRotRange = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_fineRotRange.setInputMask("")
        self.lineEdit_fineRotRange.setObjectName("lineEdit_fineRotRange")

        self.horizontalLayout_2_2.addWidget(self.lineEdit_fineRotRange)

        self.label_fineRot_steps = QtWidgets.QLabel(self.tab2)
        self.label_fineRot_steps.setSizePolicy(sizePolicy)
        self.label_fineRot_steps.setMinimumSize(QtCore.QSize(120, 0))
        self.label_fineRot_steps.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_fineRot_steps.setObjectName("label_fineRot_steps")
        self.horizontalLayout_2_2.addWidget(self.label_fineRot_steps)

        self.lineEdit_fineRot_steps = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_fineRot_steps.setInputMask("")
        self.lineEdit_fineRot_steps.setObjectName("lineEdit_fineRot_steps")

        self.horizontalLayout_2_2.addWidget(self.lineEdit_fineRot_steps)

        self.verticalLayout_2_1.addLayout(self.horizontalLayout_2_1)
        self.verticalLayout_2_1.addLayout(self.horizontalLayout_2_2)
        self.groupBox_1.setLayout(self.verticalLayout_2_1)
 
        #groupBox 2
        self.groupBox_2 = QtWidgets.QGroupBox()

        self.verticalLayout_2_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2_2.setContentsMargins(5, 5, 5, 5)

        self.horizontalLayout_2_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_3.setContentsMargins(10, 5, 10, 5)

        self.label_transRange = QtWidgets.QLabel(self.tab2)
        self.label_transRange.setSizePolicy(sizePolicy)
        self.label_transRange.setMinimumSize(QtCore.QSize(120, 0))
        self.label_transRange.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_transRange.setObjectName("label_transRange")
        self.horizontalLayout_2_3.addWidget(self.label_transRange)

        self.lineEdit_transRange = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_transRange.setInputMask("")
        self.lineEdit_transRange.setObjectName("lineEdit_transRange")

        self.horizontalLayout_2_3.addWidget(self.lineEdit_transRange)

        self.label_fineTransRange = QtWidgets.QLabel(self.tab2)
        self.label_fineTransRange.setSizePolicy(sizePolicy)
        self.label_fineTransRange.setMinimumSize(QtCore.QSize(120, 0))
        self.label_fineTransRange.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_fineTransRange.setObjectName("label_fineTransRange")
        self.horizontalLayout_2_3.addWidget(self.label_fineTransRange)

        self.lineEdit_fineTransRange = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_fineTransRange.setInputMask("")
        self.lineEdit_fineTransRange.setObjectName("lineEdit_fineTransRange")

        self.horizontalLayout_2_3.addWidget(self.lineEdit_fineTransRange)

        self.horizontalLayout_2_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_4.setContentsMargins(10, 5, 10, 5)

        self.label_transition_list = QtWidgets.QLabel(self.tab2)
        self.label_transition_list.setSizePolicy(sizePolicy)
        self.label_transition_list.setMinimumSize(QtCore.QSize(80, 0))
        self.label_transition_list.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_transition_list.setObjectName("label_transition_list")
        self.horizontalLayout_2_4.addWidget(self.label_transition_list)

        self.lineEdit_transition_list = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_transition_list.setInputMask("")
        self.lineEdit_transition_list.setObjectName("lineEdit_transition_list")

        self.horizontalLayout_2_4.addWidget(self.lineEdit_transition_list)

        self.verticalLayout_2_2.addLayout(self.horizontalLayout_2_3)
        self.verticalLayout_2_2.addLayout(self.horizontalLayout_2_4)
        self.groupBox_2.setLayout(self.verticalLayout_2_2)

        #groupBox 3
        self.groupBox_3 = QtWidgets.QGroupBox()

        self.verticalLayout_2_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2_3.setContentsMargins(5, 5, 5, 5)

        self.horizontalLayout_2_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_5.setContentsMargins(10, 5, 10, 5)

        self.label_boxSize = QtWidgets.QLabel(self.tab2)
        self.label_boxSize.setSizePolicy(sizePolicy)
        self.label_boxSize.setMinimumSize(QtCore.QSize(70, 0))
        self.label_boxSize.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_boxSize.setObjectName("label_boxSize")
        self.horizontalLayout_2_5.addWidget(self.label_boxSize)

        self.lineEdit_boxSize = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_boxSize.setInputMask("")
        self.lineEdit_boxSize.setObjectName("lineEdit_boxSize")

        self.horizontalLayout_2_5.addWidget(self.lineEdit_boxSize)

        self.label_repeating_unit = QtWidgets.QLabel(self.tab2)
        self.label_repeating_unit.setSizePolicy(sizePolicy)
        self.label_repeating_unit.setMinimumSize(QtCore.QSize(150, 0))
        self.label_repeating_unit.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_repeating_unit.setObjectName("label_repeating_unit")
        self.horizontalLayout_2_5.addWidget(self.label_repeating_unit)

        self.lineEdit_repeating_unit = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_repeating_unit.setInputMask("")
        self.lineEdit_repeating_unit.setObjectName("lineEdit_repeating_unit")

        self.horizontalLayout_2_5.addWidget(self.lineEdit_repeating_unit)

        self.label_threshold_CCC = QtWidgets.QLabel(self.tab2)
        self.label_threshold_CCC.setSizePolicy(sizePolicy)
        self.label_threshold_CCC.setMinimumSize(QtCore.QSize(120, 0))
        self.label_threshold_CCC.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_threshold_CCC.setObjectName("label_threshold_CCC")
        self.horizontalLayout_2_5.addWidget(self.label_threshold_CCC)

        self.lineEdit_threshold_CCC = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_threshold_CCC.setInputMask("")
        self.lineEdit_threshold_CCC.setObjectName("lineEdit_threshold_CCC")

        self.horizontalLayout_2_5.addWidget(self.lineEdit_threshold_CCC)

        self.label_max_seed_num = QtWidgets.QLabel(self.tab2)
        self.label_max_seed_num.setSizePolicy(sizePolicy)
        self.label_max_seed_num.setMinimumSize(QtCore.QSize(140, 0))
        self.label_max_seed_num.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_max_seed_num.setObjectName("label_max_seed_num")
        self.horizontalLayout_2_5.addWidget(self.label_max_seed_num)

        self.lineEdit_max_seed_num = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_max_seed_num.setInputMask("")
        self.lineEdit_max_seed_num.setObjectName("lineEdit_max_seed_num")

        self.horizontalLayout_2_5.addWidget(self.lineEdit_max_seed_num)

        self.horizontalLayout_2_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_6.setContentsMargins(10, 5, 10, 5)

        self.label_reference = QtWidgets.QLabel(self.tab2)
        self.label_reference.setSizePolicy(sizePolicy)
        self.label_reference.setMinimumSize(QtCore.QSize(60, 0))
        self.label_reference.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_reference.setObjectName("label_reference")
        self.horizontalLayout_2_6.addWidget(self.label_reference)

        self.lineEdit_reference = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_reference.setInputMask("")
        self.lineEdit_reference.setObjectName("lineEdit_reference")

        self.horizontalLayout_2_6.addWidget(self.lineEdit_reference)

        self.pushButton_reference = QtWidgets.QPushButton(self.tab2)
        self.pushButton_reference.setText("")
        self.pushButton_reference.setIcon(self.icon)
        self.pushButton_reference.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_reference.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_reference.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_reference.setObjectName("pushButton_reference")
        self.horizontalLayout_2_6.addWidget(self.pushButton_reference)

        self.horizontalLayout_2_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_7.setContentsMargins(10, 5, 10, 5)

        self.label_mask = QtWidgets.QLabel(self.tab2)
        self.label_mask.setSizePolicy(sizePolicy)
        self.label_mask.setMinimumSize(QtCore.QSize(60, 0))
        self.label_mask.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_mask.setObjectName("label_mask")
        self.horizontalLayout_2_7.addWidget(self.label_mask)

        self.checkBox_mask = QtWidgets.QCheckBox(self.tab2)
        self.checkBox_mask.setChecked(True)
        self.checkBox_mask.setObjectName("checkBox_mask")
        self.horizontalLayout_2_7.addWidget(self.checkBox_mask)

        self.lineEdit_mask = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_mask.setInputMask("")
        self.lineEdit_mask.setObjectName("lineEdit_mask")

        self.horizontalLayout_2_7.addWidget(self.lineEdit_mask)

        self.pushButton_mask = QtWidgets.QPushButton(self.tab2)
        self.pushButton_mask.setText("")
        self.pushButton_mask.setIcon(self.icon)
        self.pushButton_mask.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_mask.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_mask.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_mask.setObjectName("pushButton_mask")
        self.horizontalLayout_2_7.addWidget(self.pushButton_mask)

        self.horizontalLayout_2_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2_8.setContentsMargins(10, 5, 10, 5)

        self.label_refine_reference = QtWidgets.QLabel(self.tab2)
        self.label_refine_reference.setSizePolicy(sizePolicy)
        self.label_refine_reference.setMinimumSize(QtCore.QSize(60, 0))
        self.label_refine_reference.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_refine_reference.setObjectName("label_refine_reference")
        self.horizontalLayout_2_8.addWidget(self.label_refine_reference)

        self.comboBox_refine_reference = QtWidgets.QComboBox(self.tab2)
        self.comboBox_refine_reference.setObjectName("comboBox_refine_reference")
        self.comboBox_refine_reference.addItem("")
        self.comboBox_refine_reference.addItem("")
        self.horizontalLayout_2_8.addWidget(self.comboBox_refine_reference)

        self.label_min_count_to_continue = QtWidgets.QLabel(self.tab2)
        self.label_min_count_to_continue.setSizePolicy(sizePolicy)
        self.label_min_count_to_continue.setMinimumSize(QtCore.QSize(100, 0))
        self.label_min_count_to_continue.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_count_to_continue.setObjectName("label_min_count_to_continue")
        self.horizontalLayout_2_8.addWidget(self.label_min_count_to_continue)

        self.lineEdit_min_count_to_continue = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_min_count_to_continue.setInputMask("")
        self.lineEdit_min_count_to_continue.setMaximumSize(QtCore.QSize(60, 40))
        self.lineEdit_min_count_to_continue.setObjectName("lineEdit_min_count_to_continue")
        self.horizontalLayout_2_8.addWidget(self.lineEdit_min_count_to_continue)

        self.label_pick_param_filename = QtWidgets.QLabel(self.tab2)
        self.label_pick_param_filename.setSizePolicy(sizePolicy)
        self.label_pick_param_filename.setMinimumSize(QtCore.QSize(60, 0))
        self.label_pick_param_filename.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_pick_param_filename.setObjectName("label_pick_param_filename")
        self.horizontalLayout_2_8.addWidget(self.label_pick_param_filename)

        self.lineEdit_pick_param_filename = QtWidgets.QLineEdit(self.tab2)
        self.lineEdit_pick_param_filename.setInputMask("")
        self.lineEdit_pick_param_filename.setObjectName("lineEdit_pick_param_filename")
        self.horizontalLayout_2_8.addWidget(self.lineEdit_pick_param_filename)

        self.verticalLayout_2_3.addLayout(self.horizontalLayout_2_5)
        self.verticalLayout_2_3.addLayout(self.horizontalLayout_2_6)
        self.verticalLayout_2_3.addLayout(self.horizontalLayout_2_7)
        self.verticalLayout_2_3.addLayout(self.horizontalLayout_2_8)
        self.groupBox_3.setLayout(self.verticalLayout_2_3)

        # the last H layout
        self.horizontalLayout_last_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last_2.setObjectName("horizontalLayout_last_2")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last_2.addItem(spacerItem4)
        self.pushButton_generate_pick_params = QtWidgets.QPushButton(self.tab2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_generate_pick_params.sizePolicy().hasHeightForWidth())
        self.pushButton_generate_pick_params.setSizePolicy(sizePolicy)
        self.pushButton_generate_pick_params.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_generate_pick_params.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_generate_pick_params.setObjectName("run")
        self.horizontalLayout_last_2.addWidget(self.pushButton_generate_pick_params)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last_2.addItem(spacerItem5)
        
        self.gridLayout_pick_params = QtWidgets.QGridLayout(self.tab2)

        #self.gridLayout_pick_params.addLayout(self.horizontalLayout_2_1, 0, 0, 1, 1)
        self.gridLayout_pick_params.addLayout(self.horizontalLayout_2_0, 0, 0, 1, 1)
        self.gridLayout_pick_params.addWidget(self.groupBox_1, 1, 0, 1, 1)
        self.gridLayout_pick_params.addWidget(self.groupBox_2, 2, 0, 1, 1)
        self.gridLayout_pick_params.addWidget(self.groupBox_3, 3, 0, 1, 1)

        self.spacerItem6 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_pick_params.addItem(self.spacerItem6, 4, 0, 1, 1)

        self.gridLayout_pick_params.addLayout(self.horizontalLayout_last_2, 5, 0, 1, 1)

    def setUI_tab3(self):
        #tab 3
        self.tab3 = QtWidgets.QWidget()
        self.tab3.setObjectName("tab")

        self.horizontalLayout_3_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_1.setContentsMargins(10, 5, 10, 5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_expand_folder.sizePolicy().hasHeightForWidth())
        self.label_star_file_to_use = QtWidgets.QLabel(self.tab3)
        self.label_star_file_to_use.setSizePolicy(sizePolicy)
        self.label_star_file_to_use.setMinimumSize(QtCore.QSize(120, 0))
        self.label_star_file_to_use.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_star_file_to_use.setObjectName("label_star_file_to_use")
        self.horizontalLayout_3_1.addWidget(self.label_star_file_to_use)

        self.lineEdit_star_file_to_use = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_star_file_to_use.setInputMask("")
        self.lineEdit_star_file_to_use.setObjectName("lineEdit_star_file_to_use")

        self.horizontalLayout_3_1.addWidget(self.lineEdit_star_file_to_use)

        self.pushButton_star_file_to_use = QtWidgets.QPushButton(self.tab3)
        self.pushButton_star_file_to_use.setText("")
        self.pushButton_star_file_to_use.setIcon(self.icon)
        self.pushButton_star_file_to_use.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_star_file_to_use.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_star_file_to_use.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_star_file_to_use.setObjectName("pushButton_star_file_to_use")
        self.horizontalLayout_3_1.addWidget(self.pushButton_star_file_to_use)

        self.horizontalLayout_3_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_2.setContentsMargins(10, 5, 10, 5)

        self.label_pick_param_file_to_use = QtWidgets.QLabel(self.tab3)
        self.label_pick_param_file_to_use.setSizePolicy(sizePolicy)
        self.label_pick_param_file_to_use.setMinimumSize(QtCore.QSize(100, 0))
        self.label_pick_param_file_to_use.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_pick_param_file_to_use.setObjectName("label_pick_param_file_to_use")
        self.horizontalLayout_3_2.addWidget(self.label_pick_param_file_to_use)

        self.lineEdit_pick_param_file_to_use = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_pick_param_file_to_use.setInputMask("")
        self.lineEdit_pick_param_file_to_use.setObjectName("lineEdit_pick_param_file_to_use")

        self.horizontalLayout_3_2.addWidget(self.lineEdit_pick_param_file_to_use)

        self.pushButton_pick_param_file_to_use = QtWidgets.QPushButton(self.tab3)
        self.pushButton_pick_param_file_to_use.setText("")
        self.pushButton_pick_param_file_to_use.setIcon(self.icon)
        self.pushButton_pick_param_file_to_use.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_pick_param_file_to_use.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_pick_param_file_to_use.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_pick_param_file_to_use.setObjectName("pushButton_pick_param_file_to_use")
        self.horizontalLayout_3_2.addWidget(self.pushButton_pick_param_file_to_use)

        self.horizontalLayout_3_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_3.setContentsMargins(10, 5, 10, 5)

        self.label_expand_folder_to_use = QtWidgets.QLabel(self.tab3)
        self.label_expand_folder_to_use.setSizePolicy(sizePolicy)
        self.label_expand_folder_to_use.setMinimumSize(QtCore.QSize(120, 0))
        self.label_expand_folder_to_use.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_expand_folder_to_use.setObjectName("label_expand_folder_to_use")
        self.horizontalLayout_3_3.addWidget(self.label_expand_folder_to_use)

        self.lineEdit_expand_folder_to_use = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_expand_folder_to_use.setInputMask("")
        self.lineEdit_expand_folder_to_use.setObjectName("lineEdit_expand_folder_to_use")

        self.horizontalLayout_3_3.addWidget(self.lineEdit_expand_folder_to_use)

        self.pushButton_expand_folder_to_use = QtWidgets.QPushButton(self.tab3)
        self.pushButton_expand_folder_to_use.setText("")
        self.pushButton_expand_folder_to_use.setIcon(self.icon)
        self.pushButton_expand_folder_to_use.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_expand_folder_to_use.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_expand_folder_to_use.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_expand_folder_to_use.setObjectName("pushButton_expand_folder_to_use")
        self.horizontalLayout_3_3.addWidget(self.pushButton_expand_folder_to_use)

        self.tableView = QtWidgets.QTableWidget(self)

        header_labels = metadata.header_labels_expand
        self.tableView.setColumnCount(len(header_labels))
        self.tableView.setHorizontalHeaderLabels(header_labels)

        header = self.tableView.horizontalHeader()   
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

        self.gridLayout_run = QtWidgets.QGridLayout(self.tab3)

        self.gridLayout_run.addLayout(self.horizontalLayout_3_1, 0, 0, 1, 1)
        self.gridLayout_run.addLayout(self.horizontalLayout_3_2, 1, 0, 1, 1)
        self.gridLayout_run.addLayout(self.horizontalLayout_3_3, 2, 0, 1, 1)
        self.gridLayout_run.addWidget(self.tableView, 3, 0)

        self.horizontalLayout_3_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_4.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_3_4.setObjectName("highlight-hbox")

        self.label_tomo_index = QtWidgets.QLabel(self.tab3)
        self.label_tomo_index.setSizePolicy(sizePolicy)
        self.label_tomo_index.setMinimumSize(QtCore.QSize(140, 0))
        self.label_tomo_index.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_tomo_index.setObjectName("label_tomo_index")
        self.horizontalLayout_3_4.addWidget(self.label_tomo_index)

        self.lineEdit_tomo_index = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_tomo_index.setInputMask("")
        self.lineEdit_tomo_index.setObjectName("lineEdit_tomo_index")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_tomo_index)

        self.label_iterations = QtWidgets.QLabel(self.tab3)
        self.label_iterations.setSizePolicy(sizePolicy)
        self.label_iterations.setMinimumSize(QtCore.QSize(60, 0))
        self.label_iterations.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_iterations.setObjectName("label_iterations")
        self.horizontalLayout_3_4.addWidget(self.label_iterations)

        self.lineEdit_iterations = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_iterations.setInputMask("")
        self.lineEdit_iterations.setObjectName("lineEdit_iterations")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_iterations)

        self.label_min_patch_size = QtWidgets.QLabel(self.tab3)
        self.label_min_patch_size.setSizePolicy(sizePolicy)
        self.label_min_patch_size.setMinimumSize(QtCore.QSize(120, 0))
        self.label_min_patch_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_min_patch_size.setObjectName("label_min_patch_size")
        self.horizontalLayout_3_4.addWidget(self.label_min_patch_size)

        self.lineEdit_min_patch_size = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_min_patch_size.setInputMask("")
        self.lineEdit_min_patch_size.setObjectName("lineEdit_min_patch_size")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_min_patch_size)

        self.label_cpu_num = QtWidgets.QLabel(self.tab3)
        self.label_cpu_num.setSizePolicy(sizePolicy)
        self.label_cpu_num.setMinimumSize(QtCore.QSize(50, 0))
        self.label_cpu_num.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_cpu_num.setObjectName("label_cpu_num")
        self.horizontalLayout_3_4.addWidget(self.label_cpu_num)

        self.lineEdit_cpu_num = QtWidgets.QLineEdit(self.tab3)
        self.lineEdit_cpu_num.setInputMask("")
        self.lineEdit_cpu_num.setObjectName("lineEdit_cpu_num")
        self.horizontalLayout_3_4.addWidget(self.lineEdit_cpu_num)

        self.horizontalLayout_3_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3_5.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_3_5.setObjectName("highlight-hbox")
        
        spacerItem7 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3_5.addItem(spacerItem7)

        self.label_print_only_expand_select = QtWidgets.QLabel(self.tab3)
        self.label_print_only_expand_select.setSizePolicy(sizePolicy)
        self.label_print_only_expand_select.setMinimumSize(QtCore.QSize(120, 0))
        self.label_print_only_expand_select.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_print_only_expand_select.setObjectName("label_print_only_expand_select")
        self.horizontalLayout_3_5.addWidget(self.label_print_only_expand_select)

        self.checkBox_print_only_expand_select = QtWidgets.QCheckBox(self.tab3)
        self.checkBox_print_only_expand_select.setChecked(False)
        self.checkBox_print_only_expand_select.setObjectName("checkBox_print_only_expand_select")
        self.horizontalLayout_3_5.addWidget(self.checkBox_print_only_expand_select)

        self.pushButton_expand_select = QtWidgets.QPushButton(self.tab3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_expand_select.sizePolicy().hasHeightForWidth())
        self.pushButton_expand_select.setSizePolicy(sizePolicy)
        self.pushButton_expand_select.setMinimumSize(QtCore.QSize(72, 42))
        self.pushButton_expand_select.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_expand_select.setObjectName("run")
        self.horizontalLayout_3_5.addWidget(self.pushButton_expand_select)

        spacerItem9 = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3_5.addItem(spacerItem9)

        self.gridLayout_run.addLayout(self.horizontalLayout_3_4, 4, 0, 1, 1)
        self.gridLayout_run.addLayout(self.horizontalLayout_3_5, 5, 0, 1, 1)

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

    def read_settting(self):
        if not os.path.exists(self.setting_file):
            try:
                f = open(self.setting_file)
            except:
                pass        
        data = {}
        data['initParam_folder'] = ""
        data['recon_folder'] = ""
        data['tomo_star_file_name'] = ""
        data['expand_folder'] = "" 
        data['rotRange'] = ""
        data['rot_steps'] = ""
        data['fineRotRange'] = ""
        data['fineRot_steps'] = ""
        data['transRange'] = ""
        data['transition_list'] = ""
        data['fineTransRange'] = "" 
        data['boxSize'] = ""
        data['repeating_unit'] = ""
        data['reference'] = "" 
        data['mask'] = ""
        data['min_count_to_continue'] = ""
        data['checkBox_mask'] = True
        data['refine_reference'] = "No"
        data['pick_param_filename'] = ""
        data['star_file_to_use'] = ""
        data['pick_param_file_to_use'] = ""
        data['expand_folder_to_use'] = ""
        data['threshold_CCC'] = ""
        data['max_seed_num'] = ""
        data['tomo_index'] = ""
        data['iterations'] = ""
        data['min_patch_size'] = ""
        data['cpu_num'] = ""
        data['checkBox_print_only_expand_select'] = False
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
        self.lineEdit_initParam_folder.setText(data['initParam_folder'])
        self.lineEdit_recon_folder.setText(data['recon_folder'])
        self.lineEdit_tomo_star_file_name.setText(data['tomo_star_file_name'])
        self.lineEdit_expand_folder.setText(data['expand_folder'])

        self.lineEdit_rotRange.setText(data['rotRange'])
        self.lineEdit_rot_steps.setText(data['rot_steps'])
        self.lineEdit_fineRotRange.setText(data['fineRotRange'])
        self.lineEdit_fineRot_steps.setText(data['fineRot_steps'])

        self.lineEdit_transRange.setText(data['transRange'])
        self.lineEdit_fineTransRange.setText(data['fineTransRange'])
        self.lineEdit_transition_list.setText(data['transition_list'])

        self.lineEdit_boxSize.setText(data['boxSize'])
        self.lineEdit_repeating_unit.setText(data['repeating_unit'])
        self.lineEdit_threshold_CCC.setText(data['threshold_CCC'])
        self.lineEdit_max_seed_num.setText(data['max_seed_num'])
        
        self.lineEdit_reference.setText(data['reference'])
        self.lineEdit_mask.setText(data['mask'])
        self.checkBox_mask.setChecked(data['checkBox_mask'])
        self.lineEdit_min_count_to_continue.setText(data['min_count_to_continue'])

        self.comboBox_refine_reference.setCurrentText(data['refine_reference'])
        self.lineEdit_pick_param_filename.setText(data['pick_param_filename'])

        self.lineEdit_star_file_to_use.setText(data['star_file_to_use'])
        self.lineEdit_pick_param_file_to_use.setText(data['pick_param_file_to_use'])
        self.lineEdit_expand_folder_to_use.setText(data['expand_folder_to_use'])

        self.lineEdit_tomo_index.setText(data['tomo_index'])
        self.lineEdit_iterations.setText(data['iterations'])
        self.lineEdit_min_patch_size.setText(data['min_patch_size'])
        self.lineEdit_cpu_num.setText(data['cpu_num'])

        self.checkBox_print_only_expand_select.setChecked(data['checkBox_print_only_expand_select'])
          
    def save_setting(self):
        param = {}
        param['initParam_folder'] = self.lineEdit_initParam_folder.text()
        param['recon_folder'] = self.lineEdit_recon_folder.text()
        param['tomo_star_file_name'] = self.lineEdit_tomo_star_file_name.text()
        param['expand_folder'] = self.lineEdit_expand_folder.text()

        param['rotRange'] = self.lineEdit_rotRange.text()
        param['rot_steps'] = self.lineEdit_rot_steps.text()
        param['fineRotRange'] = self.lineEdit_fineRotRange.text()
        param['fineRot_steps'] = self.lineEdit_fineRot_steps.text()

        param['transRange'] = self.lineEdit_transRange.text()
        param['fineTransRange'] = self.lineEdit_fineTransRange.text()
        param['transition_list'] = self.lineEdit_transition_list.text()

        param['boxSize'] = self.lineEdit_boxSize.text()
        param['repeating_unit'] = self.lineEdit_repeating_unit.text()
        param['threshold_CCC'] = self.lineEdit_threshold_CCC.text()
        param['max_seed_num'] = self.lineEdit_max_seed_num.text()
        
        param['reference'] = self.lineEdit_reference.text()
        param['min_count_to_continue'] = self.lineEdit_min_count_to_continue.text()
        param['mask'] = self.lineEdit_mask.text()
        param['checkBox_mask'] = self.checkBox_mask.isChecked()

        param['refine_reference'] = self.comboBox_refine_reference.currentText()
        param['pick_param_filename'] = self.lineEdit_pick_param_filename.text()

        param['star_file_to_use'] = self.lineEdit_star_file_to_use.text()
        param['pick_param_file_to_use'] = self.lineEdit_pick_param_file_to_use.text()
        param['expand_folder_to_use'] = self.lineEdit_expand_folder_to_use.text()

        param['tomo_index'] = self.lineEdit_tomo_index.text()
        param['iterations'] = self.lineEdit_iterations.text()
        param['min_patch_size'] = self.lineEdit_min_patch_size.text()
        param['cpu_num'] = self.lineEdit_cpu_num.text()
        param['checkBox_print_only_expand_select'] = self.checkBox_print_only_expand_select.isChecked()
        
        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))     

    def get_prepare_params(self):
        
        if not len(self.lineEdit_initParam_folder.text()) > 0:
            initParam_folder = "Manual/initParams"
        else:
            initParam_folder = self.lineEdit_initParam_folder.text()

        if not len(self.lineEdit_recon_folder.text()) > 0:
            recon_folder = "Recon/eTomo"
        else:
            recon_folder = self.lineEdit_recon_folder.text()

        if not len(self.lineEdit_tomo_star_file_name.text()) > 0:
            tomo_star_file_name = "tomograms.star"
        else:
            tomo_star_file_name = self.lineEdit_tomo_star_file_name.text()
            if not tomo_star_file_name.endswith(".star"):
                return "star file name should end with .star"
            
        if not len(self.lineEdit_expand_folder.text()) > 0:
            expand_folder = "{}/{}/{}".format(os.getcwd(),self.expand_folder, "result")
        else:
            expand_folder = "{}/{}/{}".format(os.getcwd(), self.expand_folder, self.lineEdit_expand_folder.text())
        
        if not os.path.exists(expand_folder):
            mkfolder(expand_folder)

        params = {}
        params['initParam_folder'] = initParam_folder
        params['recon_folder'] = recon_folder
        params['tomo_star_file_name'] = tomo_star_file_name
        params['expand_folder'] = expand_folder

        return params
    
    def get_tomo_list(self, folder):
        tomoName_mod = set([ os.path.basename(x).split(".")[0] for x in glob.glob("{}/*.mod".format(folder))])
        #self.logger.info(tomoName_mod)
        rec_files = set(glob.glob("{}/*.rec".format(folder)))
        tomo_files = set(glob.glob("{}/*.mrc".format(folder)))
        tomo_files.update(rec_files)
        tomoName_tomo = set([ os.path.basename(x).split(".")[0] for x in list(tomo_files)])
        #self.logger.info(tomoName_tomo)
        intersection_tomoName = sorted(list(tomoName_mod.intersection(tomoName_tomo)))
        #self.logger.info(intersection_tomoName)
        #try:
        #    intersection_tomoName.sort(key=natural_keys)
        #except:
        #    pass
        #self.logger.info(intersection_tomoName)
        return intersection_tomoName

    def prepare_star_file(self):
        params = self.get_prepare_params()
        if type(params) is str:
            self.logger.error(params)
        elif type(params) is dict:
            ret = QMessageBox.question(self, 'Prepare {}!'.format(params['tomo_star_file_name']), \
                    "Continue?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
            if ret == QMessageBox.Yes:
                self.pushButton_prepare.setText("STOP")
                self.pushButton_prepare.setStyleSheet('QPushButton {color: red;}')

                tomoNames = self.get_tomo_list(params['initParam_folder'])

                md = MetaData()
                md.addLabels('rlnIndex','rlnTomoName','rlnInitialParamFolder','rlnReconstructionPath','rlnPickingPath')
                i = 0
                for tomo in tomoNames:
                    i+=1
                    it = Item()
                    md.addItem(it)
                    md._setItemValue(it,Label('rlnIndex'),str(i))
                    md._setItemValue(it,Label('rlnTomoName'),tomo)
                    md._setItemValue(it,Label('rlnInitialParamFolder'), params['initParam_folder'])
                    md._setItemValue(it,Label('rlnReconstructionPath'), "{}/{}".format(params['recon_folder'], tomo))
                    md._setItemValue(it,Label('rlnPickingPath'), params['expand_folder'])
                
                md.write("{}/{}".format(params['expand_folder'],params['tomo_star_file_name']))
                
                self.logger.info("Done preparing {}/{}".format(params['expand_folder'],params['tomo_star_file_name']))
                
                self.cmd_finished(self.pushButton_prepare, "Prepare")

    def cmd_finished(self, button, text="RUN"):
        button.setText(text)
        button.setStyleSheet("QPushButton {color: black;}")
        if button == self.pushButton_expand_select:
            self.reload_table()
    
    def tab_changed(self, i):
        if i == 2:
            self.reload_table()
    
    def list_row_changed(self, i):
        if i == 5:
            if self.currentIndex() == 2:
                self.reload_table()
    
    def table_click(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.tableView.item(i, 0).text()
        if j == 3:
            exp_folder = self.lineEdit_expand_folder_to_use.text().strip() if self.lineEdit_expand_folder_to_use.text() else "Expand"
            path = "{}/{}_final".format(exp_folder, tomoName)
            self.final_result_3dmod(path, tomoName)
        elif j == 4:
            path = self.lineEdit_expand_folder_to_use.text().strip() if self.lineEdit_expand_folder_to_use.text() else "Expand"
            self.clean_up(path, tomoName)
            self.reload_table()
        else:
            pass
    
    def get_pick_params(self):
        
        if len(self.lineEdit_rotRange.text()) > 0:
            if not string2float(self.lineEdit_rotRange.text()) == None:
                rotRange = int(string2float(self.lineEdit_rotRange.text()))
                rotRanges = [rotRange, rotRange, rotRange]
            else:
                rotRanges = self.lineEdit_rotRange.text().split(",")
                if (not len(rotRanges) ==3) or string2float(rotRanges[0]) == None or string2float(rotRanges[1]) == None or string2float(rotRanges[2]) == None:
                   return "Please use the valid format for the first round search range!" 
                rotRanges = [int(string2float(x)) for x in rotRanges]
        else:
            return "Please specify the first round search range!"

        if len(self.lineEdit_rot_steps.text()) > 0:
            if not string2float(self.lineEdit_rot_steps.text()) == None:
                rot_step = int(string2float(self.lineEdit_rot_steps.text()))
                rot_steps = [rot_step, rot_step, rot_step]
            else:
                rot_steps = self.lineEdit_rot_steps.text().split(",")
                if (not len(rot_steps) ==3) or string2float(rot_steps[0]) == None or string2float(rot_steps[1]) == None or string2float(rot_steps[2]) == None:
                   return "Please use the valid format for the first round search steps!" 
                rot_steps = [int(string2float(x)) for x in rot_steps]
        else:
            return "Please specify the first round search steps!"
        
        if len(self.lineEdit_fineRotRange.text()) > 0:
            if not string2float(self.lineEdit_fineRotRange.text()) == None:
                fineRotRange = int(string2float(self.lineEdit_fineRotRange.text()))
                fineRotRanges = [fineRotRange, fineRotRange, fineRotRange]
            else:
                fineRotRanges = self.lineEdit_fineRotRange.text().split(",")
                if (not len(fineRotRanges) ==3) or string2float(fineRotRanges[0]) == None or string2float(fineRotRanges[1]) == None or string2float(fineRotRanges[2]) == None:
                   return "Please use the valid format for the later round angular search range!" 
                fineRotRanges = [int(string2float(x)) for x in fineRotRanges]
        else:
            return "Please specify the later round angular search range!"
        
        if len(self.lineEdit_fineRot_steps.text()) > 0:
            if not string2float(self.lineEdit_fineRot_steps.text()) == None:
                fineRot_step = int(string2float(self.lineEdit_fineRot_steps.text()))
                fineRot_steps = [fineRot_step, fineRot_step, fineRot_step]
            else:
                fineRot_steps = self.lineEdit_fineRot_steps.text().split(",")
                if (not len(fineRot_steps) ==3) or string2float(fineRot_steps[0]) == None or string2float(fineRot_steps[1]) == None or string2float(fineRot_steps[2]) == None: 
                   return "Please use the valid format for the later round angular search steps!" 
                fineRot_steps = [int(string2float(x)) for x in fineRot_steps]
        else:
            return "Please specify the later round angular search steps!"
        
        if len(self.lineEdit_transRange.text()) > 0:
            if not string2float(self.lineEdit_transRange.text()) == None:
                transRange = int(string2float(self.lineEdit_transRange.text()))
                transRanges = [transRange, transRange, transRange]
            else:
                transRanges = self.lineEdit_transRange.text().split(",")
                if (not len(transRanges) ==3) or string2float(transRanges[0]) == None or string2float(transRanges[1]) == None or string2float(transRanges[2]) == None:
                   return "Please use the valid format for the first round transpational search range!" 
                transRanges = [int(string2float(x)) for x in transRanges]
        else:
            return "Please specify the first round transpational search range!"
        
        if len(self.lineEdit_fineTransRange.text()) > 0:
            if not string2float(self.lineEdit_fineTransRange.text()) == None:
                fineTransRange = int(string2float(self.lineEdit_fineTransRange.text()))
                fineTransRanges = [fineTransRange, fineTransRange, fineTransRange]
            else:
                fineTransRanges = self.lineEdit_fineTransRange.text().split(",")
                if (not len(fineTransRanges) ==3) or string2float(fineTransRanges[0]) == None or string2float(fineTransRanges[1]) == None or string2float(fineTransRanges[2]) == None:
                   return "Please use the valid format for the later round translational search steps!" 
                fineTransRanges = [int(string2float(x)) for x in fineTransRanges]
        else:
            return "Please specify the later round translational search steps!"
        
        if len(self.lineEdit_transition_list.text()) > 0:
            try:
                transition_list = np.array(literal_eval(self.lineEdit_transition_list.text()))
            except:
                return "Please use the valid format for the transition list!" 
            try:
                shape = transition_list.shape
                if (len(shape)==1 and shape[0]!=3) or (len(shape)==2 and shape[1]!=3):
                    return "Please use the valid format for the transition list!" 
                elif len(shape) < 1 or len(shape) > 2:
                    return "Please use the valid format for the transition list!" 
            except:
                return "Please use the valid format for the transition list!"
        else:
            transition_list = np.array(literal_eval("[0,0,0]"))
        
        if len(self.lineEdit_boxSize.text()) > 0:
            if not string2int(self.lineEdit_boxSize.text()) == None:
                box_size = int(string2int(self.lineEdit_boxSize.text()))
                box_sizes = [box_size, box_size, box_size]
            else:
                box_sizes = self.lineEdit_boxSize.text().split(",")
                if (not len(box_sizes) ==3) or not string2int(box_sizes[0]) or string2int(box_sizes[0]) <=1 \
                    or not string2int(box_sizes[1]) or string2int(box_sizes[1]) <=1 \
                    or not string2int(box_sizes[2]) or string2int(box_sizes[2]) <=1:
                   return "Please use the valid format for the box size!" 
                box_sizes = [int(string2int(x)) for x in box_sizes]
        else:
            return "Please specify the box size!"
        
        if len(self.lineEdit_repeating_unit.text()) > 0:
            repeating_unit = string2float(self.lineEdit_repeating_unit.text(), 1)
            if not repeating_unit:
                return "Repeating unit should be in decimal format!"
        else: 
            return "Please specify the repeating unit!"
        
        
        if len(self.lineEdit_threshold_CCC.text()) > 0:
            threshold_CCC = string2float(self.lineEdit_threshold_CCC.text(), 3)
            if threshold_CCC == None:
                return "CCC threshold should be in decimal format!"
        else: 
            return "Please specify the CCC threshold!"
        
        if len(self.lineEdit_max_seed_num.text()) > 0:
            max_seed_num = string2int(self.lineEdit_max_seed_num.text())
            if max_seed_num == None or max_seed_num < 1:
                return "Maximum of initial # should be a positive integer!"
        else: 
            max_seed_num = 200
        
        if len(self.lineEdit_reference.text()) > 0:
            reference = self.lineEdit_reference.text()
            header = self.read_header(reference)
            #print(header['dimenstions'])
            if header['dimensions'][0] %2 !=0 or header['dimensions'][1] %2 !=0 or header['dimensions'][2] %2 !=0:
                return "Reference dimensions required to be even number, but the provided are {}!".format(header['dimensions'])
        else: 
            reference = None
            #return "Please specify the reference!"
        
        mask = "none"
        if self.checkBox_mask.isChecked():
            if len(self.lineEdit_mask.text()) > 0:
                mask = self.lineEdit_mask.text()
            else: 
                return "Please specify the mask!"
        
        if len(self.lineEdit_min_count_to_continue.text()) > 0:
            min_count_to_continue = string2int(self.lineEdit_min_count_to_continue.text())
            if min_count_to_continue == None or min_count_to_continue < 1:
                return "Minimum # of seed particles per iteration should be a positive integer!"
        else: 
            min_count_to_continue = 5

        flgNoReferenceRefinement = 0 if self.comboBox_refine_reference.currentText()=="Yes" else 1

        if not len(self.lineEdit_pick_param_filename.text()) > 0:
            pick_param_filename = "pick.params"
        else:
            pick_param_filename = self.lineEdit_pick_param_filename.text()
            if not pick_param_filename.endswith(".params"):
                return "pick params file name should end with .params"

        params = {}
        params['rotRanges'] = rotRanges
        params['rot_steps'] = rot_steps
        params['fineRotRanges'] = fineRotRanges
        params['fineRot_steps'] = fineRot_steps
        params['transRanges'] = transRanges
        params['fineTransRanges'] = fineTransRanges
        params['transition_list'] = list(transition_list) if len(transition_list.shape) == 1 else [list(x) for x in transition_list]
        #params['transition_list'] = transition_list_text
        #params['pick_param_filename'] = pick_param_filename
        params['box_sizes'] = box_sizes
        params['repeating_unit'] = repeating_unit
        
        #params['min_num_neighbors'] = min_num_neighbors
        params['threshold_CCC'] = threshold_CCC
        params['max_seed_num'] = max_seed_num

        params['reference'] = reference
        params['mask'] = mask
        params['min_count_to_continue'] = min_count_to_continue

        #######Advanced params#######
        params['threshold_dis'] = repeating_unit*0.75
        params['yaxisType'] = 3
        params['flgAbsValue'] = 1
        params['flgNoReferenceRefinement'] = flgNoReferenceRefinement
        ##############

        return [params, pick_param_filename]
    
    def generate_pick_param_file(self):
        results = self.get_pick_params()
        
        if type(results) is str:
            self.logger.error(results)
        else:
            params, output = results
            
            ret = QMessageBox.question(self, 'Generate {}!'.format(output), \
                    "Continue?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
            if ret == QMessageBox.Yes:
                
                try:
                    if not params['reference']:
                        self.logger.warning("no reference used, will use the 1st particle as reference. If you are generating initial reference and set the iter to 1, please ignore this!")
                except:
                    pass
        
                self.pushButton_generate_pick_params.setText("STOP")
                self.pushButton_generate_pick_params.setStyleSheet('QPushButton {color: red;}')

                with open("{}/{}".format(self.expand_folder, output), 'w') as fp:
                    json.dump(params, fp, indent=2, default=int)

                self.logger.info("Done generating {}/{}".format(self.expand_folder, output))

                self.cmd_finished(self.pushButton_generate_pick_params, "Generate")

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
            if "Number of columns" in line or "Image Size" in line:
                sections = line.strip().split()[-3:]
                d['dimensions'] = [int(x) for x in sections]
        return d            
    
    def read_tomogram_star(self, tomogram_star):
        md = MetaData()
        md.read(tomogram_star)
        tomoNames = [ x.rlnTomoName for x in md]
        return tomoNames

    def reload_params(self):
        param_file = self.lineEdit_load_params.text()
        if os.path.exists(param_file):
            try:
                search_param = SearchParam(param_file)
                rotRange = ",".join([str(x) for x in search_param.rotRanges])
                self.lineEdit_rotRange.setText(rotRange)
                rot_steps = ",".join([str(x) for x in search_param.rot_steps])
                self.lineEdit_rot_steps.setText(rot_steps)

                fineRotRange = ",".join([str(x) for x in search_param.fineRotRanges])
                self.lineEdit_fineRotRange.setText(fineRotRange)

                fineRot_steps = ",".join([str(x) for x in search_param.fineRot_steps])
                self.lineEdit_fineRot_steps.setText(fineRot_steps)

                transRange = ",".join([str(x) for x in search_param.transRanges])
                self.lineEdit_transRange.setText(transRange)

                fineTransRange = ",".join([str(x) for x in search_param.fineTransRanges])
                self.lineEdit_fineTransRange.setText(fineTransRange)
 
                try:
                    transition_list = np.array(search_param.transition_list).reshape(-1,3)
                    transition_list_text = ','.join(['[{}]'.format(",".join(str(x) for x in y)) for y in transition_list])

                    self.lineEdit_transition_list.setText(transition_list_text)
                except:
                    self.logger.warning("error reading transition list!")     

                boxSize = ",".join([str(x) for x in search_param.box_sizes])
                self.lineEdit_boxSize.setText(boxSize)

                self.lineEdit_repeating_unit.setText(str(search_param.repeating_unit))
                self.lineEdit_threshold_CCC.setText(str(search_param.threshold_CCC))
                
                try:
                    self.lineEdit_max_seed_num.setText(str(search_param.max_seed_num))
                except:
                    self.lineEdit_max_seed_num.setText("")
                self.lineEdit_reference.setText(str(search_param.reference))
                
                try:
                    self.lineEdit_min_count_to_continue.setText(str(search_param.min_count_to_continue))
                except:
                    self.lineEdit_min_count_to_continue.setText("")
                
                self.lineEdit_mask.setText(str(search_param.mask))
                if len(search_param.mask) > 0 and not(search_param.mask == 'none') and not(search_param.mask == 'None'):
                    self.checkBox_mask.setChecked(True)
                else:
                    self.checkBox_mask.setChecked(False)
                
                refine_reference = "Yes" if search_param.flgNoReferenceRefinement==0 else "No"
                self.comboBox_refine_reference.setCurrentText(str(refine_reference))
                self.logger.info("loaded {}!".format(param_file))   
            except Exception as error:
                self.logger.error(error)  
                self.logger.error("error reading {}!".format(param_file))              
    
    def reload_table(self):
        if self.lineEdit_star_file_to_use.text().endswith(".star"):
            try:
                tomoNames = self.read_tomogram_star(self.lineEdit_star_file_to_use.text())
            except:
                tomoNames=[]
            self.tableView.setRowCount(0)
            self.tableView.setRowCount(len(tomoNames))
            if len(tomoNames) > 0:
                expand_folder = self.lineEdit_expand_folder_to_use.text()
                for i, tomo in enumerate(tomoNames):
                    self.tableView.setItem(i, 0, QTableWidgetItem(tomo))

                    rounds_num, particles_num = self.read_progress(tomo, expand_folder)
                    item_rounds_num = QTableWidgetItem(str(rounds_num))
                    item_rounds_num.setBackground(QtGui.QColor("#4CAF50"))
                    item_rounds_num.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(i, 1, item_rounds_num)

                    item_particles_num = QTableWidgetItem(str(particles_num))
                    item_particles_num.setBackground(QtGui.QColor("#008CBA"))
                    item_particles_num.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(i, 2, item_particles_num)
                    
                    action_3dmod = QTableWidgetItem("3dmod")
                    action_3dmod.setBackground(QtGui.QColor("#f75990"))
                    action_3dmod.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(i, 3, action_3dmod)
                    
                    action_clean_up = QTableWidgetItem("Clean up")
                    action_clean_up.setBackground(QtGui.QColor("#d0bdf4"))
                    action_clean_up.setFont(QFont("sans-serif", 8, QFont.Bold))
                    self.tableView.setItem(i, 4, action_clean_up)
            self.current_tomoNames = tomoNames
        else:
            self.tableView.setRowCount(0)
    
    def read_progress(self, tomoName, expand_folder):
        rounds_num = 0
        particles_num = 0
        if os.path.exists("{}/{}_cache".format(expand_folder, tomoName)):
            files_cache = [os.path.basename(x) for x in glob.glob("{}/{}_cache/*".format(expand_folder, tomoName))]
            for f in files_cache:
                if f.startswith("round"):
                   rounds_num+=1
        if os.path.exists("{}/{}_final".format(expand_folder, tomoName)):
            files_final = glob.glob("{}/{}_final/*".format(expand_folder, tomoName))
            for f in files_final:
                if os.path.basename(f) == "{}.pts".format(tomoName):
                    with open(f) as file:
                        lines = file.readlines()
                        particles_num = len(lines)
        return [rounds_num, particles_num]

    def get_expand_select_params(self):
        params = {}
        tomo_index = []
        if len(self.lineEdit_tomo_index.text()) > 0:
            try:
                tomo_index = list(set([string2int(x) for x in idx2list(self.lineEdit_tomo_index.text())]))
                for i in tomo_index:
                    if not i or i <=0:
                        return "Please use valid format for the select tomo index!"
            except:
                return "Please use valid format for the select tomo index!"
        else: 
            return "Please specify the select tomo index!"
        
        if len(self.lineEdit_iterations.text()) > 0:
            iterations = string2int(self.lineEdit_iterations.text())
            if iterations ==None or iterations < 0:
                return "Rounds number should be in positive interger format!"
        else: 
            return "Please specify the rounds number!"
        
        if len(self.lineEdit_min_patch_size.text()) > 0:
            min_patch_size = string2int(self.lineEdit_min_patch_size.text())
            if min_patch_size ==None or min_patch_size < 0:
                return "Min patch size should be in positive interger format!"
        else: 
            return "Please specify the min patch size!"

        if len(self.lineEdit_cpu_num.text()) > 0:
            cpu_num = string2int(self.lineEdit_cpu_num.text())
            if not cpu_num or cpu_num <= 0:
                return "CPU number should be in positive interger format!"
        else: 
            return "Please specify the cpu number!"
        
        if len(self.lineEdit_star_file_to_use.text()) > 0:
            star_file_to_use = self.lineEdit_star_file_to_use.text()
            if not os.path.exists(star_file_to_use):
                return "Cannot find the tomogram star file to be used!".format(star_file_to_use)
        else: 
            return "Please specify the tomogram star file to be used!"
        
        if len(self.lineEdit_pick_param_file_to_use.text()) > 0:
            pick_param_file_to_use = self.lineEdit_pick_param_file_to_use.text()
            if not os.path.exists(pick_param_file_to_use):
                return "Cannot find the pick param file to be used! {}".format(pick_param_file_to_use)
        else: 
            return "Please specify the pick param file to be used!"
        
        params['tomo_index'] = sorted(tomo_index)
        params['iterations'] = iterations
        params['min_patch_size'] = min_patch_size
        params['cpu_num'] = cpu_num

        params['star_file_to_use'] = star_file_to_use
        params['pick_param_file_to_use'] = pick_param_file_to_use

        return params

    def expand_select(self):
        if self.pushButton_expand_select.text() == "RUN":
            params = self.get_expand_select_params()
            if type(params) is str:
                self.logger.error(params)
            else:
                ret = QMessageBox.question(self, 'Run Expand of {} tomograms!'.format(len(params['tomo_index'])), \
                        "Continue?\n"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
                if ret == QMessageBox.Yes:
                    self.pushButton_expand_select.setText("STOP")
                    self.pushButton_expand_select.setStyleSheet('QPushButton {color: red;}')
                    
                    cmds = []
                    max_index = len(self.current_tomoNames)
                    for ind in params['tomo_index']:
                        if ind <= max_index:
                            cmd = "sta_expand.py {} {} {} {} {} {}".format(params['star_file_to_use'],params['pick_param_file_to_use'],\
                                self.current_tomoNames[ind-1],params['iterations'], params['min_patch_size'], params['cpu_num'])
                            cmds.append(cmd)

                    if self.checkBox_print_only_expand_select.isChecked():
                        for c in cmds:
                            self.logger.info(c)
                        self.cmd_finished(self.pushButton_expand_select, "RUN")
                    else:
                        self.thread_expand_cmds = Expand_CMDS(cmds)
                        self.thread_expand_cmds.finished.connect(lambda: self.cmd_finished(self.pushButton_expand_select, 'RUN'))
                        try:
                            self.thread_expand_cmds.start()
                        except:
                            self.thread_expand_cmds.stop_process()
                else:
                    self.cmd_finished(self.pushButton_expand_select, "RUN")
        else:
            ret = QMessageBox.question(self, 'Quit!', \
                        "Quit expanding the selected tomograms? The current one will be still runing in back ground\nPlease wait for its finish or kill it before running new jobs!"\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
            if ret == QMessageBox.Yes:
                self.cmd_finished(self.pushButton_expand_select, "RUN")
                self.thread_expand_cmds.kill_process()
                try:
                    self.thread_expand_cmds.stop_process()
                except:
                    self.logger.warning("no thread are running!")

    def final_result_3dmod(self, path, tomoName):   
        if os.path.exists(path):
            cmd = "cd {}; 3dmod {}.mrc {}.mod".format(path, tomoName, tomoName)
            try:
                os.system(cmd)
            except:
                pass
        else:
            self.logger.error("{} does not exist!".format(path))

    def clean_up(self, path, tomoName):
        ret = QMessageBox.question(self, 'Clean up!', \
                        "Clean up all expand files for {}, Continue?\n".format(tomoName)\
                        , QMessageBox.Yes | QMessageBox.No, \
                        QMessageBox.No)
                    
        if ret == QMessageBox.Yes:

            if os.path.exists(path):
                cmd = "cd {}; rm {} {}_cache {}_final -r".format(path, tomoName, tomoName, tomoName)
                try:
                    subprocess.run(cmd, shell=True,stdout=subprocess.PIPE)
                except:
                    pass
            else:
                self.logger.error("{} does not exist!".format(path))
            self.logger.info("Done clean up for {}.".format(tomoName))

    def checkbox_mask_changed(self):
        if self.checkBox_mask.checkState():
            self.lineEdit_mask