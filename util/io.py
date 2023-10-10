from PyQt5 import QtGui
from TomoNet.util.utils import getLogContent
import os

def mkfolder(folder):

    try:
        os.makedirs(folder)
    except FileExistsError:
        logging.warning("The {0} folder already exists  \n The old {0} folder will be renamed (to {0}~)".format(folder))
        import shutil
        if os.path.exists(folder+'~'):
            shutil.rmtree(folder+'~')
        os.system('mv {} {}'.format(folder, folder+'~'))
        os.makedirs(folder)


# from PyQt5.QtGui import QTextCharFormat, QColor, QTextCursor, QFont
# from PyQt5.QtCore import QRegExp

# def highlight(log_window, color, text):
#     col = QColor(color)
#     fmt = QTextCharFormat()
#     fmt.setForeground(col)
#     fmt.setFontWeight(QFont.Bold)
#     # 正则
#     expression = QRegExp(text)
#     log_window.moveCursor(QTextCursor.Start)
#     cursor = log_window.textCursor()

#     # 循环查找设置颜色
#     pos = 0
#     index = expression.indexIn(log_window.toPlainText(), pos)
#     while index >= 0:
#         cursor.setPosition(index)
#         cursor.movePosition(QTextCursor.Right,
#                             QTextCursor.KeepAnchor, len(text))
#         cursor.mergeCharFormat(fmt)
#         pos = index + expression.matchedLength()
#         index = expression.indexIn(log_window.toPlainText(), pos)

#     log_window.moveCursor(QtGui.QTextCursor.End)


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
        