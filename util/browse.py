import os
from PyQt5 import QtWidgets

def sim_path(path):
    pwd = os.getcwd()
    if pwd in path:
        return "." + path[len(pwd):]
    else:
        return path

def switch_btn(widget, btn):
    switcher = {
        "recon_dir": widget.line_edit_recon_dir
    }
    return switcher.get(btn, "Invaid btn name")

def browseSlot(lineEdit, type='*', location=""):
    ''' 
        Called when the user presses the Browse button
    '''    
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
    elif type == "json":
        flt = "param file (*.json);;All Files (*)"
    
    fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                    None,
                    "Choose File",
                    location,
                    flt,
                    options=options)
    if fileName:
        try:
            lineEdit.setText(sim_path(fileName))
        except:
            lineEdit.setText(fileName)

def browseFolderSlot(lineEdit, location=""):
    ''' 
        Called when the user presses the Browse folder button
    '''
    if location == "":
        location = os.getcwd().replace("\\","/")
    try:
        pwd = os.getcwd().replace("\\","/") 
        dir_path=QtWidgets.QFileDialog.getExistingDirectory(None, "Choose Directory", location)

        if len(dir_path) > 0:
            try:
                lineEdit.setText(sim_path(dir_path))
            except:
                lineEdit.setText(dir_path)
    except:
        ##TODO: record to log.
        pass