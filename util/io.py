import os, shutil 
from PyQt5 import QtGui
from TomoNet.util.utils import getLogContent


def mkfolder(folder):
    try:
        os.makedirs(folder)
    except FileExistsError:
        if os.path.exists(folder+'~'):
            shutil.rmtree(folder+'~')
        os.system('mv {} {}'.format(folder, folder+'~'))
        os.makedirs(folder)

def mkfolder_ifnotexist(folder):
    try:
        os.makedirs(folder)
    except FileExistsError:
        pass

def update_log_window(log_window, txt):
    log_window.setText(getLogContent(txt).strip())
    log_window.moveCursor(QtGui.QTextCursor.End)
    
    custom_font = QtGui.QFont()
    custom_font.setPointSize(11)
    log_window.setCurrentFont(custom_font)

def log(logger, text, level="info"):
    if logger:
        if level == "error":
            logger.error(text)
        elif level == "warning":
            logger.warning(text)
        else:
            logger.info(text)
    else:
        print(text)
        