import os.path
import logging

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QTabWidget, QMessageBox
from TomoNet.util import browse
from TomoNet.util.utils import check_or_create_path, string2float, string2int
from TomoNet.process.bash_motioncor import MotionCor2

class MotionCor(QTabWidget):
    def __init__(self):
        super().__init__()
        ############### Define variables ################
        self.corrected_folder = "MotionCorrection/MotionCor/corrected_images"
        #self.processed_folder = "MotionCorrection/MotionCor/processed_raw_images"
        self.processed_folder = "Raw_frames_DoNotDelete"
        self.setting_file ="MotionCorrection/MotionCor/motioncor.setting"
        
        self.log_file = "MotionCorrection/motion.log"
        
        self.check_log_file("MotionCorrection")

        check_or_create_path("MotionCorrection/MotionCor")

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

        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.setupUi()        
        

    def setupUi(self):
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")

        scriptDir = os.path.dirname(os.path.realpath(__file__))

        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        self.gridLayout_1 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_1.setObjectName("gridLayout_1")
        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_1.setObjectName("horizontalLayout_1")

        self.label_raw_image_folder = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_raw_image_folder.sizePolicy().hasHeightForWidth())
        self.label_raw_image_folder.setSizePolicy(sizePolicy)
        self.label_raw_image_folder.setMinimumSize(QtCore.QSize(120, 0))
        self.label_raw_image_folder.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_raw_image_folder.setObjectName("label_raw_image_folder")
        self.horizontalLayout_1.addWidget(self.label_raw_image_folder)
        self.lineEdit_raw_image_folder = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_raw_image_folder.setInputMask("")
        self.lineEdit_raw_image_folder.setObjectName("lineEdit_raw_image_folder")
        self.horizontalLayout_1.addWidget(self.lineEdit_raw_image_folder)
        
        self.pushButton_raw_image_folder = QtWidgets.QPushButton(self.tab)
        self.pushButton_raw_image_folder.setText("")
        self.pushButton_raw_image_folder.setIcon(icon)
        self.pushButton_raw_image_folder.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_raw_image_folder.setMaximumSize(QtCore.QSize(60, 24))
        self.pushButton_raw_image_folder.setObjectName("pushButton_raw_image_folder")
        self.horizontalLayout_1.addWidget(self.pushButton_raw_image_folder)
        self.gridLayout_1.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.label_motioncor_exe = QtWidgets.QLabel(self.tab)
        self.label_motioncor_exe.setSizePolicy(sizePolicy)
        self.label_motioncor_exe.setMinimumSize(QtCore.QSize(120, 0))
        self.label_motioncor_exe.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_motioncor_exe.setObjectName("label_motioncor_exe")
        self.horizontalLayout_2.addWidget(self.label_motioncor_exe)
        self.lineEdit_motioncor_exe = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_motioncor_exe.setInputMask("")
        self.lineEdit_motioncor_exe.setObjectName("lineEdit_motioncor_exe")
        self.horizontalLayout_2.addWidget(self.lineEdit_motioncor_exe)
        
        self.pushButton_motioncor_exe = QtWidgets.QPushButton(self.tab)
        self.pushButton_motioncor_exe.setText("")
        self.pushButton_motioncor_exe.setIcon(icon)
        self.pushButton_motioncor_exe.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_motioncor_exe.setMaximumSize(QtCore.QSize(60, 24))
        self.pushButton_motioncor_exe.setObjectName("pushButton_motioncor_exe")
        self.horizontalLayout_2.addWidget(self.pushButton_motioncor_exe)
        self.gridLayout_1.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")

        self.label_gain_ref = QtWidgets.QLabel(self.tab)
        self.label_gain_ref.setSizePolicy(sizePolicy)
        self.label_gain_ref.setMinimumSize(QtCore.QSize(120, 0))
        self.label_gain_ref.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_gain_ref.setObjectName("label_gain_ref")
        self.horizontalLayout_3.addWidget(self.label_gain_ref)
        self.lineEdit_gain_ref = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_gain_ref.setInputMask("")
        self.lineEdit_gain_ref.setObjectName("lineEdit_gain_ref")
        self.horizontalLayout_3.addWidget(self.lineEdit_gain_ref)
        
        self.pushButton_gain_ref = QtWidgets.QPushButton(self.tab)
        self.pushButton_gain_ref.setText("")
        self.pushButton_gain_ref.setIcon(icon)
        self.pushButton_gain_ref.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_gain_ref.setMaximumSize(QtCore.QSize(60, 24))
        self.pushButton_gain_ref.setObjectName("pushButton_gain_ref")
        self.horizontalLayout_3.addWidget(self.pushButton_gain_ref)
        self.gridLayout_1.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)


        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_pixel_size = QtWidgets.QLabel(self.tab)        
        self.label_pixel_size.setSizePolicy(sizePolicy)
        self.label_pixel_size.setMinimumSize(QtCore.QSize(60, 0))
        self.label_pixel_size.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_pixel_size.setObjectName("label_pixel_size")
        self.horizontalLayout_4.addWidget(self.label_pixel_size)
        self.lineEdit_pixel_size = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_pixel_size.setInputMask("")
        self.lineEdit_pixel_size.setObjectName("lineEdit_pixel_size")
        self.horizontalLayout_4.addWidget(self.lineEdit_pixel_size)
        self.label_frame_dose = QtWidgets.QLabel(self.tab)
        self.label_frame_dose.setSizePolicy(sizePolicy)
        self.label_frame_dose.setMinimumSize(QtCore.QSize(80, 0))
        self.label_frame_dose.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_frame_dose.setObjectName("label_frame_dose")
        self.horizontalLayout_4.addWidget(self.label_frame_dose)
        self.lineEdit_frame_dose = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_frame_dose.setInputMask("")
        self.lineEdit_frame_dose.setObjectName("lineEdit_frame_dose")
        self.horizontalLayout_4.addWidget(self.lineEdit_frame_dose)
        self.label_gpu_ID = QtWidgets.QLabel(self.tab)
        self.label_gpu_ID.setSizePolicy(sizePolicy)
        self.label_gpu_ID.setMinimumSize(QtCore.QSize(60, 0))
        self.label_gpu_ID.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_gpu_ID.setObjectName("label_gpu_ID")
        self.horizontalLayout_4.addWidget(self.label_gpu_ID)
        self.lineEdit_gpu_ID = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_gpu_ID.setInputMask("")
        self.lineEdit_gpu_ID.setObjectName("lineEdit_gpu_ID")
        self.horizontalLayout_4.addWidget(self.lineEdit_gpu_ID)
        self.gridLayout_1.addLayout(self.horizontalLayout_4, 3, 0, 1, 1)

        self.label_ftbin = QtWidgets.QLabel(self.tab)
        self.label_ftbin.setSizePolicy(sizePolicy)
        self.label_ftbin.setMinimumSize(QtCore.QSize(60, 0))
        self.label_ftbin.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_ftbin.setObjectName("label_ftbin")
        self.horizontalLayout_4.addWidget(self.label_ftbin)
        
        self.lineEdit_ftbin = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_ftbin.setSizePolicy(sizePolicy)
        self.lineEdit_ftbin.setMaximumWidth(60)
        #self.lineEdit_ftbin.setMinimumSize(QtCore.QSize(120, 0))
        self.lineEdit_ftbin.setInputMask("")
        self.lineEdit_ftbin.setObjectName("lineEdit_ftbin")
        self.horizontalLayout_4.addWidget(self.lineEdit_ftbin)
        self.label_input_file_type = QtWidgets.QLabel(self.tab)
        self.label_input_file_type.setSizePolicy(sizePolicy)
        self.label_input_file_type.setMinimumSize(QtCore.QSize(120, 0))
        self.label_input_file_type.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_input_file_type.setObjectName("label_input_file_type")
        self.horizontalLayout_4.addWidget(self.label_input_file_type)
        self.comboBox_input_file_type = QtWidgets.QComboBox(self.tab)
        self.comboBox_input_file_type.setObjectName("comboBox_input_file_type")
        self.comboBox_input_file_type.addItem("")
        self.comboBox_input_file_type.addItem("")
        self.comboBox_input_file_type.addItem("")
        self.horizontalLayout_4.addWidget(self.comboBox_input_file_type)
        #self.gridLayout_1.addLayout(self.horizontalLayout_5, 4, 0, 1, 1)



        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")

        self.label_addtional_param = QtWidgets.QLabel(self.tab)
        self.label_addtional_param.setSizePolicy(sizePolicy)
        self.label_addtional_param.setMinimumSize(QtCore.QSize(160, 0))
        self.label_addtional_param.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_addtional_param.setObjectName("label_addtional_param")
        self.horizontalLayout_6.addWidget(self.label_addtional_param)
        self.lineEdit_addtional_param = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_addtional_param.setInputMask("")
        self.lineEdit_addtional_param.setObjectName("lineEdit_addtional_param")
        self.horizontalLayout_6.addWidget(self.lineEdit_addtional_param)
        self.gridLayout_1.addLayout(self.horizontalLayout_6, 5, 0, 1, 1)

        self.spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_1.addItem(self.spacerItem1, 6, 0, 1, 1)


        self.horizontalLayout_last = QtWidgets.QHBoxLayout()
        self.horizontalLayout_last.setObjectName("horizontalLayout_last")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem2)
        self.pushButton_run_motioncor = QtWidgets.QPushButton(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_run_motioncor.sizePolicy().hasHeightForWidth())
        self.pushButton_run_motioncor.setSizePolicy(sizePolicy)
        self.pushButton_run_motioncor.setMinimumSize(QtCore.QSize(98, 50))
        self.pushButton_run_motioncor.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.pushButton_run_motioncor.setObjectName("run")
        self.horizontalLayout_last.addWidget(self.pushButton_run_motioncor)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_last.addItem(spacerItem3)
        self.gridLayout_1.addLayout(self.horizontalLayout_last, 7, 0, 1, 1)

        self.addTab(self.tab, "")

        self.thread_motioncor = None
        ############### Define variables ################

        for child in self.findChildren(QtWidgets.QLineEdit):
            child.textChanged.connect(self.save_setting)
        for child in self.findChildren(QtWidgets.QComboBox):
            child.currentIndexChanged.connect(self.save_setting)

        self.pushButton_raw_image_folder.clicked.connect(lambda: browse.browseFolderSlot(self.lineEdit_raw_image_folder)) 
        self.pushButton_motioncor_exe.clicked.connect(lambda: browse.browseSlot(self.lineEdit_motioncor_exe)) 
        self.pushButton_gain_ref.clicked.connect(lambda: browse.browseSlot(self.lineEdit_gain_ref, 'map')) 


        self.pushButton_run_motioncor.clicked.connect(self.motioncor)

        self.retranslateUi()
        self.read_setting()

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        self.label_raw_image_folder.setText(_translate("Form", "Raw Frames Folder:"))
        self.lineEdit_raw_image_folder.setPlaceholderText(_translate("Form", "MotionCorrection/MotionCor/frames"))
        self.lineEdit_raw_image_folder.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\">Folder path to your raw frames. </span></p></body></html>"))

        
        self.label_motioncor_exe.setText(_translate("Form", "MotionCor Executable:"))
        self.lineEdit_motioncor_exe.setPlaceholderText(_translate("Form", ""))
        self.lineEdit_motioncor_exe.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\">Path to MotionCor executable file, e.g., Your/Path/To/Motioncorr2/bin/MotionCor2_1.2.6-Cuda101 </span></p></body></html>"))

        
        self.label_gain_ref.setText(_translate("Form", "Gain Reference Image:"))
        self.lineEdit_gain_ref.setPlaceholderText(_translate("Form", "YourPath/gain_ref.mrc"))
        self.lineEdit_gain_ref.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\">Path to Gain Reference Image, e.g., Your/Path/To/gain_ref.mrc </span></p></body></html>"))

        self.label_pixel_size.setText(_translate("Form", "PixSize:"))
        self.lineEdit_pixel_size.setPlaceholderText(_translate("Form", "1.0"))
        self.lineEdit_pixel_size.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\">Pixel size. </span></p></body></html>"))


        self.label_frame_dose.setText(_translate("Form", "FmDose:"))
        self.lineEdit_frame_dose.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\">\
            Electron dosage per frame. If dose-weight is not wanted, keep this param empty. </span></p></body></html>"))
        self.label_gpu_ID.setText(_translate("Form", "GPU ID:"))
        self.lineEdit_gpu_ID.setPlaceholderText(_translate("Form", "0"))
        self.lineEdit_gpu_ID.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\">GPU IDs to be used for MotionCor, parallel processing is allow by assigning multiple GPU. e.g. 0,1,2,3 </span></p></body></html>"))

        self.label_ftbin.setText(_translate("Form", "Binning:"))
        self.lineEdit_ftbin.setPlaceholderText(_translate("Form", "1"))
        self.lineEdit_ftbin.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\"> If the raw movie stacks are collected in super-resolution mode and the final images is intended to be binned. </span></p></body></html>"))
        
        self.label_input_file_type.setText(_translate("Form", "Input File Type:"))
        self.comboBox_input_file_type.setItemText(0, _translate("Form", "tif"))
        self.comboBox_input_file_type.setItemText(1, _translate("Form", "tiff"))
        self.comboBox_input_file_type.setItemText(2, _translate("Form", "mrc"))

        self.label_addtional_param.setText(_translate("Form", "Additional Parameters:"))
        self.lineEdit_addtional_param.setToolTip(_translate("MainWindow", "<html><head/><body><p><span style=\" font-size:9pt;\"> Addtional parameters to be used. Follow format -Option1 value1 -Option2 value2 ... </span></p></body></html>"))
        
        self.pushButton_run_motioncor.setText(_translate("Form", "RUN"))

        self.setTabText(self.indexOf(self.tab), _translate("Form", "MotionCor2"))

    def get_params(self):
        if len(self.lineEdit_raw_image_folder.text()) > 0:
            raw_image_folder = self.lineEdit_raw_image_folder.text()
        else: 
            self.cmd_finished()
            return "raw image folder path cannot be empty!"

        if len(self.lineEdit_motioncor_exe.text()) > 0:
            motioncor_exe = self.lineEdit_motioncor_exe.text()
        else: 
            self.cmd_finished()
            return "please provide your Motioncor executable!"

        if len(self.lineEdit_gain_ref.text()) > 0:
            gain_ref = self.lineEdit_gain_ref.text()
        else: 
            self.cmd_finished()
            return "please provide your gain reference image!"

        if len(self.lineEdit_pixel_size.text()) > 0 :
            pixel_size = string2float(self.lineEdit_pixel_size.text())
            if pixel_size == None or pixel_size < 0:
                return "please use correct format for pixel size (positive real number)!"
            #pixel_size = self.lineEdit_pixel_size.text()
        else: 
            self.cmd_finished()
            return "please provide pixel size!"
        
        if len(self.lineEdit_frame_dose.text()) > 0:
            frame_dose = string2float(self.lineEdit_frame_dose.text())
            if frame_dose == None or frame_dose < 0:
                return "please use correct format for frame dose (positive real number)!"
            #frame_dose = self.lineEdit_frame_dose.text()
        else: 
            frame_dose = None

        gpu_ID = self.lineEdit_gpu_ID.text() if len(self.lineEdit_gpu_ID.text()) > 0 else 0

        if len(self.lineEdit_ftbin.text()) > 0 :
            ftbin = string2int(self.lineEdit_ftbin.text())
            if ftbin == None or ftbin < 0:
                return "please use correct format for binning (positive int number)!"
            #pixel_size = self.lineEdit_pixel_size.text()
        else: 
            ftbin = 1
            #return "please provide pixel size!"
        

        #ftbin = self.lineEdit_ftbin.text() if len(self.lineEdit_ftbin.text()) > 0 else 1

        input_file_type = self.comboBox_input_file_type.currentText()
        addtional_param = self.lineEdit_addtional_param.text()

        d = {}
        d['raw_image_folder'] = raw_image_folder
        d['motioncor_exe'] = motioncor_exe
        d['gain_ref'] = gain_ref
        d['pixel_size'] = pixel_size
        d['frame_dose'] = frame_dose
        d['gpu_ID'] = gpu_ID
        d['ftbin'] = ftbin
        d['input_file_type'] = input_file_type
        d['addtional_param'] = addtional_param

        return d
               
    def motioncor(self):
        
        d = self.get_params()
        if type(d) is dict:
            if self.pushButton_run_motioncor.text() == "RUN":
                ret = QMessageBox.question(self, 'Run Motion Correction!', \
                    "Run motion correction for all the image from {}. \
                    \nContinue?\n".format(d['raw_image_folder'])\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                
                if ret == QMessageBox.Yes:
                    self.pushButton_run_motioncor.setText("STOP")
                    self.pushButton_run_motioncor.setStyleSheet('QPushButton {color: red;}')

                    if not self.thread_motioncor:
                        self.thread_motioncor = MotionCor2(d,self.corrected_folder,self.processed_folder)
                    else:
                        self.thread_motioncor = MotionCor2(d,self.corrected_folder,self.processed_folder)
                    self.thread_motioncor.finished.connect(self.cmd_finished)
                    try:
                        self.thread_motioncor.start()
                    except:
                        self.thread_motioncor.stop_process()

                else:
                    self.cmd_finished()
            else :
                ret = QMessageBox.question(self, 'Stop Motion Correction!', \
                    "Stop Motion Correction! \
                    \nConfirm?\n"\
                    , QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.pushButton_run_motioncor.setText("RUN")
                    self.pushButton_run_motioncor.setStyleSheet("QPushButton {color: black;}")
                    try:
                        self.thread_motioncor.stop_process()

                    except:
                        self.logger.warning("no thread are running!")
        else:
             self.logger.error(d)
             self.cmd_finished()
        self.save_setting()
        

    def cmd_finished(self):
        self.pushButton_run_motioncor.setText("RUN")
        self.pushButton_run_motioncor.setStyleSheet("QPushButton {color: black;}")

    def read_setting(self):
        if os.path.exists(self.setting_file):
            data = {}
            data['raw_image_folder'] = ""
            data['motioncor_exe'] = ""
            data['gain_ref'] = ""
            data['pixel_size'] = ""
            data['frame_dose'] = ""
            data['gpu_ID'] = ""
            data['ftbin'] = ""
            data['input_file_type'] = "tif"
            data['addtional_param'] = ""
            try:
                with open(self.setting_file) as f:
                    for line in f:
                        (k, v) = line.split(":")
                        data[k] = v.strip()
                self.lineEdit_raw_image_folder.setText(data['raw_image_folder'])
                self.lineEdit_motioncor_exe.setText(data['motioncor_exe'])
                self.lineEdit_gain_ref.setText(data['gain_ref'])
                self.lineEdit_pixel_size.setText(data['pixel_size'])
                self.lineEdit_frame_dose.setText(data['frame_dose'])
                self.lineEdit_gpu_ID.setText(data['gpu_ID'])
                self.lineEdit_ftbin.setText(data['ftbin'])
                self.comboBox_input_file_type.setCurrentText(data['input_file_type'])
                self.lineEdit_addtional_param.setText(data['addtional_param'])
                
            except:
                print("error reading {}!".format(self.setting_file))

    def save_setting(self):
        param = {}
        param['raw_image_folder'] = self.lineEdit_raw_image_folder.text()
        param['motioncor_exe'] = self.lineEdit_motioncor_exe.text()
        param['gain_ref'] = self.lineEdit_gain_ref.text()
        param['pixel_size'] = self.lineEdit_pixel_size.text()
        param['frame_dose'] = self.lineEdit_frame_dose.text()
        param['gpu_ID'] = self.lineEdit_gpu_ID.text()
        param['ftbin'] = self.lineEdit_ftbin.text()
        param['input_file_type'] = self.comboBox_input_file_type.currentText()
        param['addtional_param'] = self.lineEdit_addtional_param.text()
        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))

    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 0:
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

    def getLogContent( self, fileName ):
        '''
        sets the member fileName to the value of the argument
        if the file exists.  Otherwise resets both the filename
        and file contents members.
        '''
        if self.isValid( fileName ):
            self.fileName = fileName
            content = open( fileName, 'r' ).read()
            return content
        else:
            return None
    

    def check_log_file(self, folder):
        if not os.path.exists(folder):
            os.mkdir(folder)
        try:
            file = open(self.log_file, 'r')
            file.close()
        except:
            pass
