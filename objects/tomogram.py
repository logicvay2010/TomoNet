import os
import glob
import numpy as np
import imodmodel
import scipy.cluster.hierarchy as hcluster
import subprocess

class Tomogram:
  def __init__(self, tomoName, tiltSeriesPath=None, rawtltPath=None, reconstructionPath=None, initialParamFolder=None, pickingPath=None):
    self.tomoName = tomoName
    self.tiltSeriesPath = tiltSeriesPath
    self.rawtltPath = rawtltPath
    self.reconstructionPath = reconstructionPath
    self.initialParamFolder = initialParamFolder
    self.pickingPath = pickingPath
    self.staPath = "{}/{}".format(pickingPath,tomoName)
    self.rotaxesPath = None
    self.modPath = None
    self.motlPath = None

  def setInitialParams(self, initialParamFolder=None, less=True):
    if self.initialParamFolder == None and initialParamFolder == None:
      print("error: initialParamFolder has not defined yet!")
    else:
      if initialParamFolder != None:
        self.initialParamFolder = initialParamFolder
      listing = glob.glob("{}/{}[!0-9]*".format(self.initialParamFolder, self.tomoName))
      for filename in listing:
        #if filename.endswith(".mod")
        if filename.endswith("{}.mod".format(self.tomoName)):
          self.modPath = filename
        elif filename.endswith("RotAxes.csv"):
          self.rotaxesPath = filename
        #elif filename.endswith("InitMOTL.csv"):
        elif filename.endswith("MOTL.csv"):
          if not (self.motlPath == "{}_MOTL.csv".format(self.tomoName) or self.motlPath == "{}_InitMOTL.csv".format(self.tomoName)):
            self.motlPath = filename
        elif filename.endswith((".mrc",".rec")):
          self.tomogramPickPath = filename
          self.originTomogramPickPath = filename
        else:
          pass
    if self.motlPath == None and less:
      self.set_model_less()

  def set_model_less(self):
    less_modPath = "{}_less.mod".format(self.modPath.split(".mod")[0])
    less_ptsPath = "{}_less.pts".format(self.modPath.split(".mod")[0])
    
    # a parameter for defining using less particles from the input to improve efficiency
    less_number = 1000
    if os.path.exists(self.modPath):
      particle_list = np.array(imodmodel.read(self.modPath))[:,2:]
      print(particle_list)
      print(less_number)
      clusters = hcluster.fclusterdata(particle_list, less_number, criterion="maxclust")
      new_particle_list = []
      for i in range(len(set(clusters))):
        new_particle_list.append(particle_list[np.argwhere(clusters == i+1)][0][0])

    with open(less_ptsPath, "w") as f_pts:
      for p in new_particle_list:
        f_pts.write("{} {} {}\n".format(p[0],p[1],p[2]))
    
    cmd = "point2model {} {}".format(less_ptsPath, less_modPath)
    subprocess.check_output(cmd, shell=True)
    self.modPath = less_modPath
    

  def getInitialParams(self):
    try:
      return [self.tomogramPickPath, self.modPath, self.motlPath, self.rotaxesPath]
    except:
      print("initialParams not defined yet.")
      return -1
      
  def setReconstructionPath(self, reconstructionPath=None):
    if self.reconstructionPath == None and reconstructionPath == None:
      print("error: reconstructionPath has not defined yet!")
    else:
      if reconstructionPath != None:
        self.reconstructionPath = reconstructionPath
      self.tltPath = "{}/{}.tlt".format(self.reconstructionPath,self.tomoName)
      if os.path.exists("{}/{}.rawtlt".format(self.reconstructionPath,self.tomoName)):
        self.rawtltPath = "{}/{}.rawtlt".format(self.reconstructionPath,self.tomoName)
  
  def setTilt(self):
    try:
      tlt = []
      with open(self.tltPath) as file:
        for line in file: 
          line = line.strip() #or some other preprocessing
          tlt.append(float(line)) 
      self.tlt = tlt
    except:
      self.tlt = [-60, 60]
      
  def setPickingPath(self, pickingPath=None):
    if self.pickingPath == None and pickingPath == None:
      print("error: pickingPath has not defined yet!")
    else:
      if pickingPath != None:
        self.pickingPath = pickingPath

  def getParticleNumber(self):
    if os.path.exists(self.modPath):
      df = imodmodel.read(self.modPath)
      self.numberParticles = df.shape[0]

  def readTomo(self):
    import mrcfile
    with mrcfile.open(self.tomogramPickPath) as mrc:
      z,y,x = mrc.data.shape
      self.boundary = [x,y,z]
      self.apix = round(mrc.voxel_size.x*1,2)
  
  def updateAlignmentFile(self, latest_round, latest_cache_folder_path):
    print(latest_round)
    if latest_round < 0:
      self.setInitialParams()
    else:
      self.setInitialParams(less=False)
      exp_folder = "{}/exp".format(latest_cache_folder_path)
      listing = glob.glob("{}/{}*".format(exp_folder, self.tomoName))
      for filename in listing:
        if filename.endswith("exp.mod"):
          self.modPath = filename
        elif filename.endswith("exp_RotAxes.csv"):
          self.rotaxesPath = filename
        elif filename.endswith("exp_MOTL.csv"):
          self.motlPath = filename
        elif filename.endswith(("exp.mrc","exp.rec")):
          self.tomogramPickPath = filename

  def readModData(self):
    cache_folder_path = "{}_cache".format(self.staPath)
    #latest_round = -1
    points = np.array([])
    if os.path.exists(cache_folder_path):
      rounds = os.listdir(cache_folder_path)
      for r in rounds:
        exp_path = "{}/{}/exp".format(cache_folder_path, r)
        if os.path.exists(exp_path):
          modfile = "{}/{}.mod".format(exp_path,self.tomoName)
          df_mod = imodmodel.read(modfile)
          a = np.vstack((df_mod.x, df_mod.y, df_mod.z))
          if len(points) == 0:
            points = a.transpose()
          else:
            points = np.vstack((points, a.transpose()))
    return points


