
from PyQt5.QtCore import QThread, QProcess

class TrainIsoNet(QThread):
    
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        self.p = None

    def run(self):
        #subprocess.check_output(self.cmd, shell=True)
        #subprocess.run(self.cmd, shell=True, encoding="utf-8")
        self.p = QProcess()

        self.p.start(self.cmd)
        res = self.p.waitForFinished(86400)
        #self.p.finished.connect(self.kill_process)
    
    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()
        try:
            self.kill_process()
        except:
            pass

    def kill_process(self):
        self.p.kill()
        self.p.terminate()
        #self.p.kill()
        #self.p.close()