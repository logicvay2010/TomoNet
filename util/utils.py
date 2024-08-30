import os, shutil

def string2float(s, d=3):
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
    try:
        os.makedirs(folder)
    except FileExistsError:
        if os.path.exists(folder+'~'):
            shutil.rmtree(folder+'~')
        os.system('mv {} {}'.format(folder, folder+'~'))
        os.makedirs(folder)

def natural_keys(text, delimiter='_', index=-1):
        return int(text.split(delimiter)[index])

def getRGBs(a, max_angle=15, avg_angle=0):
    offset = max(1e-12, max_angle - avg_angle)
    a_offset = max(1e-12, a - avg_angle)
    ratio = min(1, a_offset/offset)
    r = round(255*ratio)
    g = 155
    b = 0
    return r, g, b

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