import os
import glob
import numpy as np
import imodmodel
import scipy.cluster.hierarchy as hcluster
import subprocess
from TomoNet.util.io import mkfolder

class Tomogram:
  def __init__(self, tomoName, tiltSeriesPath=None, rawtltPath=None, reconstructionPath=None, initialParamFolder=None, pickingPath=None, max_seed_num = 200):
    self.tomoName = tomoName
    self.tiltSeriesPath = tiltSeriesPath
    self.rawtltPath = rawtltPath
    self.reconstructionPath = reconstructionPath
    self.initialParamFolder = initialParamFolder
    self.pickingPath = pickingPath
    self.max_seed_num = max_seed_num
    self.staPath = "{}/{}".format(pickingPath, tomoName)
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
        elif (filename.endswith("MOTL.csv") or filename.endswith("motl.csv")) and "less" not in filename:
          if not (self.motlPath == "{}_MOTL.csv".format(self.tomoName) or self.motlPath == "{}_InitMOTL.csv".format(self.tomoName)):
            self.motlPath = filename
        elif filename.endswith((".mrc",".rec")):
          self.tomogramPickPath = filename
          self.originTomogramPickPath = filename
        else:
          pass
    
    if os.path.exists(self.modPath):
      actual_particle_num = len(np.array(imodmodel.read(self.modPath))[:,2:])
      if self.max_seed_num > actual_particle_num:
        less = False
        self.max_seed_num = actual_particle_num
    else:
      less = False
      print("error: .mod file has not found for {}!".format(self.tomoName))

    if self.motlPath == None or less:
      use_motl_info = not (self.motlPath == None)
      self.set_model_less(use_motl_info)

  def set_model_less(self, use_motl_info=False):
    less_folder = "{}/less_{}".format(self.initialParamFolder, self.tomoName)
    mkfolder(less_folder)
    
    #less_modPath = "{}_less.mod".format(self.modPath.split(".mod")[0])
    #less_ptsPath = "{}_less.pts".format(self.modPath.split(".mod")[0])
    less_modPath = "{}/{}".format(less_folder, os.path.basename(self.modPath))
    less_ptsPath = "{}.pts".format(less_modPath.split(".mod")[0])

    #a parameter for defining using less particles from the input to improve efficiency
    less_number = self.max_seed_num
    if os.path.exists(self.modPath):
      particle_list = np.array(imodmodel.read(self.modPath))[:,2:]
      clusters = hcluster.fclusterdata(particle_list, t=less_number, criterion="maxclust")
      new_particle_list = []
      for i in range(len(set(clusters))):
        new_particle_list.append(particle_list[np.argwhere(clusters == i+1)][0][0])

    #new_particle_list = particle_list
    with open(less_ptsPath, "w") as f_pts:
      for p in new_particle_list:
        f_pts.write("{} {} {}\n".format(p[0],p[1],p[2]))

    cmd = "point2model {} {}".format(less_ptsPath, less_modPath)
    subprocess.check_output(cmd, shell=True)
    self.modPath = less_modPath

    
    less_tomogramPickPath = "{}/{}".format(less_folder, os.path.basename(self.tomogramPickPath))
    less_rotaxesPath = "{}/{}".format(less_folder, os.path.basename(self.rotaxesPath))
    cmd = "cd {}; ln -s ../{} ./;".format(less_folder, os.path.basename(self.tomogramPickPath))
    subprocess.run(cmd,shell=True)

    f_rot = open(self.rotaxesPath, "r")
    with open(less_rotaxesPath, "w") as f_rot_less:
      lines = np.array(f_rot.readlines())
      for c in range(len(set(clusters))):
        f_rot_less.write(lines[np.argwhere(clusters == c+1)][0][0])

    self.tomogramPickPath = less_tomogramPickPath
    self.rotaxesPath = less_rotaxesPath
    
    if use_motl_info:
      f_motl = open(self.motlPath, "r")
      #less_motlPath = "{}_less_MOTL.csv".format(self.motlPath.split("motl.csv")[0]) if self.motlPath.endswith("motl.csv") \
      #    else "{}_less_MOTL.csv".format(self.motlPath.split("MOTL.csv")[0]) 
      less_motlPath = "{}/{}".format(less_folder, os.path.basename(self.motlPath))

      with open(less_motlPath, "w") as f_motl_less:
        lines = f_motl.readlines()
        lines_no_header = np.array(lines[1:])
        f_motl_less.write(lines[0])
        for c in range(len(set(clusters))):
          new_line = lines_no_header[np.argwhere(clusters == c+1)][0][0]
          new_line_split = new_line.split(',')
          new_line_split[3] = str(c+1)

          f_motl_less.write(','.join(new_line_split))
        
      self.motlPath = less_motlPath
    
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


