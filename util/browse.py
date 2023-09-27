import os
from PyQt5 import QtWidgets

def switch_btn(widget, btn):
    switcher = {
        "recon_dir": widget.line_edit_recon_dir
    }
    return switcher.get(btn, "Invaid btn name")

def browseSlot(lineEdit, type='*'):
    ''' Called when the user presses the Browse button
    '''
    #lineEdit = switch_btn(widget, btn)
    
    #pwd = os.getcwd().replace("\\","/")
    
    options = QtWidgets.QFileDialog.Options()
    options |= QtWidgets.QFileDialog.DontUseNativeDialog
    
    flt = "All Files (*)"
    
    if type == "map":
        flt = "mrc file (*.mrc);;rec file (*.rec);;All Files (*)"
    elif type == "star":
        flt = "star file (*.star);;All Files (*)"
    elif type == "params":
        flt = "param file (*.params);;All Files (*)"
    elif type == "h5":
        flt = "param file (*.h5);;All Files (*)"
    
    fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                    None,
                    "Choose File",
                    "",
                    flt,
                    options=options)
    if fileName:
        lineEdit.setText(fileName)


def browseFolderSlot(lineEdit):
    ''' 
        Called when the user presses the Browse folder button
        TODO: add file name filter
    '''
    try:
        pwd = os.getcwd().replace("\\","/") 
        dir_path=QtWidgets.QFileDialog.getExistingDirectory(None,"Choose Directory",pwd)

        if len(dir_path) > 0:
            lineEdit.setText(dir_path)
    except:
        ##TODO: record to log.
        pass