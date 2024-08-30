import time, subprocess, logging, psutil 
from PyQt5.QtCore import QThread

class Expand_CMDS(QThread):

    def __init__(self, cmds):
        super().__init__()
        self.cmds = cmds

        self.log_file = "Expand/expand.log"

        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler(filename=self.log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        formatter.datefmt = "%y-%m-%d %H:%M:%S"
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def run(self):        
        for cmd in self.cmds:
            if cmd.split()[4] == '0':
                    self.logger.info("Start generating a new final folder for {}".format(cmd.split()[3]))
            else:
                self.logger.info("Start expand {} for {} rounds".format(cmd.split()[3],cmd.split()[4]))
            subprocess.check_output(cmd, shell=True)
            try:
                if cmd.split()[4] == '0':
                    self.logger.info("Finish generating a new final folder for {}".format(cmd.split()[3]))
                else:
                    self.logger.info("Finish expand {} for {} rounds".format(cmd.split()[3],cmd.split()[4]))
            except:
                pass

    def stop_process(self):
        self.terminate()
        self.quit()
        self.wait()
        
        with open("Expand/STOP","w") as w:
            pass

        while True:
            a = [p.info['pid'] for p in psutil.process_iter(attrs=['pid', 'name']) if ('python' == p.info['name'] or "MCR" in p.info['name'])]
            if len(a) > 0:
                [p.kill() for p in psutil.process_iter(attrs=['pid', 'name']) if ('python' == p.info['name'] or "MCR" in p.info['name'])]
            else:
                break
            time.sleep(3)
        
    

