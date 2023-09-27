import os
def string2float(s, d=2):
        try:
            n = round(float(s),d)
        except:
            return None
        return n

def string2int(s):
        try:
            n = int(s)
        except:
            return None
        return n

def mkfolder(folder):
    import os
    try:
        os.makedirs(folder)
    except FileExistsError:
        #logging.warning("The {0} folder already exists  \n The old {0} folder will be renamed (to {0}~)".format(folder))
        import shutil
        if os.path.exists(folder+'~'):
            shutil.rmtree(folder+'~')
        os.system('mv {} {}'.format(folder, folder+'~'))
        os.makedirs(folder)

def natural_keys(text, delimiter='_', index=-1):
        return int(text.split(delimiter)[index])

def getRGBs(a):
	ratio = min(1, a/30)
	r = round(255*ratio,2)
	g = round(255*(1-ratio))
	b = 0
	return r,g,b

def check_or_create_path(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)

def isValid(fileName):
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
    
def check_log_file(log_file, folder):
    if not os.path.exists(folder):
        os.mkdir(folder)
    try:
        file = open(log_file, 'r')
        file.close()
    except:
        pass
        #print("fatal error when open log file {}!".format(self.log_file))
        #self.logger.error("fatal error when open log file {}!".format(self.log_file))

def getLogContent(fileName):
    '''
    sets the member fileName to the value of the argument
    if the file exists.  Otherwise resets both the filename
    and file contents members.
    '''
    if isValid(fileName):
        content = open(fileName, 'r').read()
        return content
    else:
        return None
    

def idx2list(tomo_idx):
    if tomo_idx is not None:
            if type(tomo_idx) is tuple:
                tomo_idx = list(map(str,tomo_idx))
            elif type(tomo_idx) is int:
                tomo_idx = [str(tomo_idx)]
            else:
                # tomo_idx = tomo_idx.split(',')
                txt=str(tomo_idx)
                txt=txt.replace(',',' ').split()
                tomo_idx=[]
                for everything in txt:
                    if everything.find("-")!=-1:
                        everything=everything.split("-")
                        for e in range(int(everything[0]),int(everything[1])+1):
                            tomo_idx.append(str(e))
                    else:
                        tomo_idx.append(str(everything))
    return tomo_idx