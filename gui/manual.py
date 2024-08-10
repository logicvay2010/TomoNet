import logging
import os.path
import os, glob, subprocess
import imodmodel

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTabWidget, QHeaderView, QMessageBox, QTableWidgetItem
from TomoNet.util import metadata
from TomoNet.util import browse

class Manual(QTabWidget):
    def __init__(self):
        super().__init__()
        
        self.setting_file ="ManualPick/manual.setting"
        
        self.log_file = "ManualPick/manual.log"
        
        self.check_log_file("ManualPick")

        self.recon_folder = "Recon/eTomo"

        self.stalkInit_folder = "ManualPick/stalkInit_prep"

        self.initParams_folder = "ManualPick/initParams"

        self.check_or_create_path(self.stalkInit_folder)
        self.check_or_create_path(self.initParams_folder)

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
        self.reload_table()

    def setupUi(self):
        scriptDir = os.path.dirname(os.path.realpath(__file__))

        icon =  QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("{}/icons/icon_folder.png".format(scriptDir)), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
    
        #horizontalLayout_1
        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)

        self.label_map_for_pick = QtWidgets.QLabel(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_map_for_pick.sizePolicy().hasHeightForWidth())
        self.label_map_for_pick.setSizePolicy(sizePolicy)
        self.label_map_for_pick.setMinimumSize(QtCore.QSize(120, 0))
        self.label_map_for_pick.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_map_for_pick.setObjectName("label_map_for_pick")
        self.horizontalLayout_1.addWidget(self.label_map_for_pick)

        self.lineEdit_path_other_maps = QtWidgets.QLineEdit(self.tab)
        self.lineEdit_path_other_maps.setInputMask("")
        self.lineEdit_path_other_maps.setObjectName("lineEdit_path_other_maps")
        self.horizontalLayout_1.addWidget(self.lineEdit_path_other_maps)

        self.pushButton_other_maps = QtWidgets.QPushButton(self.tab)
        self.pushButton_other_maps.setText("")
        self.pushButton_other_maps.setIcon(icon)
        self.pushButton_other_maps.setIconSize(QtCore.QSize(24, 24))
        self.pushButton_other_maps.setMaximumSize(QtCore.QSize(160, 24))
        self.pushButton_other_maps.setMinimumSize(QtCore.QSize(60, 24))
        self.pushButton_other_maps.setObjectName("pushButton_other_maps")
        self.horizontalLayout_1.addWidget(self.pushButton_other_maps)

        self.tableView = QtWidgets.QTableWidget(self)
        self.model = QtGui.QStandardItemModel(self)


        header_labels = metadata.header_labels_manual
        self.tableView.setColumnCount(len(header_labels))
        self.tableView.setHorizontalHeaderLabels(header_labels)

        header = self.tableView.horizontalHeader()   
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tableView.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

        self.gridLayout_motioncor = QtWidgets.QGridLayout(self.tab)

        self.gridLayout_motioncor.addLayout(self.horizontalLayout_1, 0, 0, 1, 1)
        self.gridLayout_motioncor.addWidget(self.tableView, 1, 0)

        self.addTab(self.tab, "Results")

        self.tableView.doubleClicked.connect(self.table_doubleClick)
        self.tableView.doubleClicked.connect(self.table_click)

        self.lineEdit_path_other_maps.textChanged.connect(self.save_setting)
        self.lineEdit_path_other_maps.textChanged.connect(self.reload_table)

        self.pushButton_other_maps.clicked.connect\
            (lambda: browse.browseFolderSlot(self.lineEdit_path_other_maps)) 
        
        self.read_settting()
        self.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.retranslateUi()

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("Form", "Form"))
        
        self.label_map_for_pick.setText(_translate("Form", "Map for Pick:"))
        self.label_map_for_pick.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">The folder to tomograms to be picked, normally are binned and \
                contrast improved, for example SIRT reconstruction or IsoNet reconstruction.\
            </span></p></body></html>"))

        self.lineEdit_path_other_maps.setPlaceholderText(_translate("Form", \
            "YourPath/toMaps/usedForInitPick/"))
        self.lineEdit_path_other_maps.setToolTip(_translate("MainWindow", \
            "<html><head/><body><p><span style=\" \
            font-size:9pt;\">Path to the folder store your post processed tomogram,\
            for example you want to use Isonet Corrected maps, then \
            put the corrected images folder here.\
            </span></p></body></html>"))

    @QtCore.pyqtSlot(str)
    def update_log_window(self, txt):
        in_current_page = True
        for x in self.parentWidget().parentWidget().children():
            if x.objectName() == "listWidget":
                if not x.currentRow() == 4:
                    in_current_page = False
            elif x.objectName() == "log_window":
                if in_current_page:
                    self.log_window = x
                    self.log_window.setText(self.getLogContent(txt))
                    self.log_window.moveCursor(QtGui.QTextCursor.End)

                    custom_font = QtGui.QFont()
                    custom_font.setPointSize(11)
                    self.log_window.setCurrentFont(custom_font)

    def read_settting(self):
        if os.path.exists(self.setting_file):
            data = {}
            data['lineEdit_path_other_maps'] = ""
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
                self.lineEdit_path_other_maps.setText(data['lineEdit_path_other_maps'])
            except:
                print("error reading {}!".format(self.setting_file))
    
    def save_setting(self):
        param = {}
        param['lineEdit_path_other_maps'] = self.lineEdit_path_other_maps.text()
        try:
            with open(self.setting_file, 'w') as f: 
                for key, value in param.items(): 
                    f.write("{}:{}\n".format(key,value))
        except:
            print("error writing {}!".format(self.setting_file))

    def natural_keys(self, text):
        return int(text.split("_")[-1]) 

    def read_tomo(self):
        searchPath = "{}".format(self.lineEdit_path_other_maps.text())

        tomoNames_rec = [os.path.basename(x).split(".")[0] \
            for x in sorted(glob.glob("{}/*.rec".format(searchPath)))]
        tomoNames_mrc = [os.path.basename(x).split(".")[0] \
            for x in sorted(glob.glob("{}/*.mrc".format(searchPath)))]

        tomoNames = []
        tomoNames.extend(tomoNames_rec)
        tomoNames.extend(tomoNames_mrc)
        try:
            tomoNames.sort(key=self.natural_keys)
        except:
            pass

        self.tomoPaths = ["{}/{}.mrc".format(searchPath,x) if x in tomoNames_mrc else \
                         "{}/{}.rec".format(searchPath,x) for x in tomoNames]

        mod_counts = []
        for t in tomoNames:
            c = 0
            final_mod_file = "{}/{}.mod".format(self.initParams_folder, t)
            if os.path.exists(final_mod_file):
                df_mod = imodmodel.read(final_mod_file)
                c = df_mod.shape[0]

            mod_counts.append(c)

        return tomoNames, mod_counts
    
    def reload_table(self):
        tomoNames, mod_counts = self.read_tomo()
        
        self.tableView.setRowCount(0)
        self.tableView.setRowCount(len(tomoNames))
        if len(tomoNames) > 0:
            for i, tomo in enumerate(tomoNames):
                self.tableView.setItem(i, 0, QTableWidgetItem(tomo))
                action_top = QTableWidgetItem("Top")
                action_top.setBackground(QtGui.QColor("#4CAF50"))
                action_top.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 1, action_top)

                action_bottom = QTableWidgetItem("Bottom")
                action_bottom.setBackground(QtGui.QColor("#008CBA"))
                action_bottom.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 2, action_bottom)

                action_side = QTableWidgetItem("Side")
                action_side.setBackground(QtGui.QColor("#f75990"))
                action_side.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 3, action_side)

                action_combine = QTableWidgetItem("Combine All")
                action_combine.setBackground(QtGui.QColor("#d0bdf4"))
                action_combine.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 4, action_combine)

                action_stalkInit = QTableWidgetItem("StalkInit")
                action_stalkInit.setBackground(QtGui.QColor("#a0d2eb"))
                action_stalkInit.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 5, action_stalkInit)

                action_plot = QTableWidgetItem("Plot")
                action_plot.setBackground(QtGui.QColor("#fff685"))
                action_plot.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 6, action_plot)
                
                text_picked = "View {} picked".format(mod_counts[i]) if mod_counts[i] > 0 else ""
                action_view_picked = QTableWidgetItem(text_picked)
                action_view_picked.setBackground(QtGui.QColor("#4ecdc4"))
                action_view_picked.setFont(QFont("sans-serif", 8, QFont.Bold))
                self.tableView.setItem(i, 7, action_view_picked)

    def table_doubleClick(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.tableView.item(i, 0).text()
        tomoPath = self.tomoPaths[i]
        tomoFullName = os.path.basename(tomoPath)
        self.link_file(tomoPath, self.stalkInit_folder)
        
        #j == 1 top. norm towards larger Z
        if j == 1:
            mod_file = "{}_top.mod".format(tomoName)
            if os.path.exists("{}/{}".format(self.stalkInit_folder,mod_file)):
                cmd = "cd {}; 3dmod {} {}".format(self.stalkInit_folder, tomoFullName, mod_file)
            else:
                cmd = "cd {}; 3dmod {}".format(self.stalkInit_folder, tomoFullName)
            self.logger.info("3dmod open {} picking top particles!".format(tomoFullName))
            os.system(cmd)
            
        #j == 2 bottom. norm towards smaller Z
        elif j == 2:
            mod_file = "{}_bottom.mod".format(tomoName)
            if os.path.exists("{}/{}".format(self.stalkInit_folder,mod_file)):
                cmd = "cd {}; 3dmod {} {}".format(self.stalkInit_folder, tomoFullName, mod_file)
            else:
                cmd = "cd {}; 3dmod {}".format(self.stalkInit_folder, tomoFullName)
            self.logger.info("3dmod open {} picking bottom particles!".format(tomoFullName))
            os.system(cmd)
        #j == 3 side. need 2 points define a particle
        elif j == 3:
            mod_file = "{}_side.mod".format(tomoName)
            if os.path.exists("{}/{}".format(self.stalkInit_folder,mod_file)):
                cmd = "cd {}; 3dmod {} {}".format(self.stalkInit_folder, tomoFullName, mod_file)
            else:
                cmd = "cd {}; 3dmod {}".format(self.stalkInit_folder, tomoFullName)
            self.logger.info("3dmod open {} picking side particles!".format(tomoFullName))
            os.system(cmd)
        else:
            pass
    
    def link_file(self, file, folder):
        if not os.path.exists("{}/{}".format(folder, os.path.basename(file))):
            cmd = "ln -s {} {}/".format(file, folder)
            subprocess.check_output(cmd, shell=True)
            self.logger.info("link {} to folder {}".format(file, folder))
        else:
            pass
    
    def table_click(self, item):
        i = item.row()
        j = item.column()
        tomoName = self.tableView.item(i, 0).text()
        tomoPath = self.tomoPaths[i]
        combined_mod = "{}.mod".format(tomoName)
        if j == 4:
            ret = QMessageBox.question(self, 'Combine!', \
                "Do you want to combine particles from all views?\
                \n \nThe old {}.mod will be replaced if exists!"\
                .format(tomoName, combined_mod), QMessageBox.Yes | QMessageBox.No, \
                QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.combine_mods(tomoName)
        elif j == 5:
            ret = QMessageBox.question(self, 'StalkInit!', \
                "Do you want to perform StalkInit? \n\nThe old result will be replaced if exist!"\
                .format(tomoName, combined_mod), QMessageBox.Yes | QMessageBox.No, \
                QMessageBox.No)
            if ret == QMessageBox.Yes:
                ret = QMessageBox.question(self, 'StalkInit!', \
                    "Do you want to apply a pseudo-random rotation around the Y-axis?"\
                    .format(tomoName, combined_mod), QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.stalkInit(tomoName,tomoPath, 1)
                else:
                    self.stalkInit(tomoName,tomoPath, 0)
                self.reload_table()
            else:
                pass
        elif j == 6:
            ret = QMessageBox.question(self, 'Plot!', \
                "Plot the manual picking for {}?"\
                .format(tomoName), QMessageBox.Yes | QMessageBox.No, \
                QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.plot_rotAxes(tomoName)
        elif j == 7:
            if not self.tableView.item(i, 7).text() == "":
                ret = QMessageBox.question(self, 'Picked Particles', \
                    "Display the picked particle location for {}?"\
                    .format(tomoName), QMessageBox.Yes | QMessageBox.No, \
                    QMessageBox.No)
                if ret == QMessageBox.Yes:
                    self.plot_picked_particle(tomoName)
            
    def check_or_create_path(self, folder):
        if not os.path.exists(folder):
            os.mkdir(folder)

    def plot_picked_particle(self, tomoName):
        mod_name = "{}.mod".format(tomoName)
        tomo_mrc = "{}.mrc".format(tomoName)
        tomo_rec = "{}.rec".format(tomoName)
        if not os.path.exists("{}/{}".format(self.initParams_folder,mod_name)):
            self.logger.error("{} not detected in folder {}!"\
                .format(mod_name, os.path.basename(self.initParams_folder)))
        tomo_name = tomo_mrc if os.path.exists("{}/{}".format(self.initParams_folder,tomo_mrc)) else tomo_rec
        if not os.path.exists("{}/{}".format(self.initParams_folder, tomo_name)):
            self.logger.error("{} not detected in folder {}!"\
                .format(tomo_name, os.path.basename(self.initParams_folder)))
        else:
            #cmd = "cd {}; 3dmod -B 2 {} {}"\
            #   .format(self.initParams_folder, tomo_name, mod_name)
            cmd = "cd {}; 3dmod {} {}"\
                .format(self.initParams_folder, tomo_name, mod_name)
            os.system(cmd)

    def plot_rotAxes(self, tomoName):
        mod_name = "{}.mod".format(tomoName)
        rot_name = "{}_RotAxes.csv".format(tomoName)
        if not os.path.exists("{}/{}".format(self.initParams_folder,mod_name)):
            self.logger.error("{} not detected in folder {}!"\
                .format(mod_name, os.path.basename(self.initParams_folder)))
        elif not os.path.exists("{}/{}".format(self.initParams_folder,rot_name)):
            self.logger.error("{} not detected in folder {}!"\
                .format(rot_name, os.path.basename(self.initParams_folder)))
        else:
            cmd = "cd {}; plotRotAxes {} {}"\
                .format(self.initParams_folder, mod_name, rot_name)
            os.system(cmd)
            self.logger.info("Plotted picking for {}!".format(tomoName))

    def plot_rotAxes_2(self, tomoName):
        mod_name = "{}.mod".format(tomoName)
        rot_name = "{}_RotAxes.csv".format(tomoName)
        if not os.path.exists("{}/{}".format(self.initParams_folder,mod_name)):
            self.logger.error("{} not detected in folder {}!"\
                .format(mod_name, os.path.basename(self.initParams_folder)))
        elif not os.path.exists("{}/{}".format(self.initParams_folder,rot_name)):
            self.logger.error("{} not detected in folder {}!"\
                .format(rot_name, os.path.basename(self.initParams_folder)))
        else:
            self.logger.info("Plotted picking for {}!".format(tomoName))

    def combine_mods(self, tomoName):
        top_mod_name = "{}_top.mod".format(tomoName)
        top_pts_name = "{}_top.pts".format(tomoName)
        bottom_mod_name = "{}_bottom.mod".format(tomoName)
        bottom_pts_name = "{}_bottom.pts".format(tomoName)
        side_mod_name = "{}_side.mod".format(tomoName)
        side_pts_name = "{}_side.pts".format(tomoName)

        #in order top, bottom, side
        particle_pairs = []
        if os.path.exists("{}/{}".format(self.stalkInit_folder, top_mod_name)):
            self.logger.info("{} detected!".format(top_mod_name))
            
            cmd = "cd {}; model2point {} {}".format\
                (self.stalkInit_folder,top_mod_name, top_pts_name)
            subprocess.check_output(cmd, shell=True)
            
            with open("{}/{}".format(self.stalkInit_folder, top_pts_name)) as f:
                for line in f:
                    x,y,z = [float(p) for p in line.strip().split()]
                    z1 = z+10
                    z2 = z-10
                    particle_pairs.append([x,y,z1])
                    particle_pairs.append([x,y,z2])

            os.remove("{}/{}".format(self.stalkInit_folder, top_pts_name))

        if os.path.exists("{}/{}".format(self.stalkInit_folder, bottom_mod_name)):
            self.logger.info("{} detected!".format(bottom_mod_name))

            cmd = "cd {}; model2point {} {}".format\
                (self.stalkInit_folder,bottom_mod_name, bottom_pts_name)
            subprocess.check_output(cmd, shell=True)

            with open("{}/{}".format(self.stalkInit_folder, bottom_pts_name)) as f:
                for line in f:
                    x,y,z = [float(p) for p in line.strip().split()]
                    z1 = z+10
                    z2 = z-10
                    particle_pairs.append([x,y,z2])
                    particle_pairs.append([x,y,z1])
            os.remove("{}/{}".format(self.stalkInit_folder, bottom_pts_name))
            
        if os.path.exists("{}/{}".format(self.stalkInit_folder, side_mod_name)):
            self.logger.info("{} detected!".format(side_mod_name))

            cmd = "cd {}; model2point {} {}".format\
                (self.stalkInit_folder, side_mod_name, side_pts_name)
            subprocess.check_output(cmd, shell=True)

            with open("{}/{}".format(self.stalkInit_folder, side_pts_name)) as f:
                for line in f:
                    x,y,z = [float(p) for p in line.strip().split()]
                    particle_pairs.append([x,y,z])
            os.remove("{}/{}".format(self.stalkInit_folder, side_pts_name))

        if len(particle_pairs) == 0:
            self.logger.error("No particle detected!".format(bottom_mod_name))
        else:
            with open("{}/{}.tmp".format(self.stalkInit_folder, tomoName), 'w') as f: 
                for line in particle_pairs:
                    f.write("{}\n".format(" ".join([str(x) for x in line])))
            
            cmd = "cd {}; point2model {}.tmp {}.mod -nu 2".format\
                (self.stalkInit_folder, tomoName, tomoName)
            subprocess.check_output(cmd, shell=True)
            os.remove("{}/{}.tmp".format(self.stalkInit_folder, tomoName))

            self.logger.info("Combined {} particles for {}!"\
                .format(len(particle_pairs)//2,tomoName))

    def stalkInit(self, tomoName, tomoPath, flgRandomize):
        mod_name = "{}.mod".format(tomoName)
        if not os.path.exists("{}/{}".format(self.stalkInit_folder,mod_name)):
            self.logger.error("{} not detected!".format(mod_name))
        else:
            cmd = "cd {}; stalkInit {} flgRandomize {}"\
                .format(self.stalkInit_folder, mod_name, flgRandomize)
            try:
                subprocess.check_output(cmd, shell=True)
            except:
                self.logger.error("StalkInit error for {}! The mod file may have strange number per contour".format(tomoName))
                return
            
            cmd = "mv {}/centroid.mod {}/{}.mod; mv {}/{}_InitMOTL.csv {}/;\
                  mv {}/{}_RotAxes.csv {}/; rm {}/{}; rm {}/{}"\
                    .format(self.stalkInit_folder, self.initParams_folder, tomoName, \
                    self.stalkInit_folder, tomoName, self.initParams_folder, \
                    self.stalkInit_folder, tomoName, self.initParams_folder, \
                    self.stalkInit_folder, "head.mod", self.stalkInit_folder, "tail.mod")
            subprocess.check_output(cmd, shell=True)
            
            self.link_file(tomoPath, self.initParams_folder)

            self.logger.info("StalkInit done for {}!".format(tomoName))

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