import numpy as np
import os, subprocess
import math

class PRMFile():
  def __init__(self, tomo):
    self.tomo = tomo

  def getSearchRangeList(self, range, step):
    step_list = []
    step_i = step
    while step_i <=32:
      if step_i >= 16 and step_i < 30:
        step_i = 15
      step_list.append(step_i)
      step_i = step_i*2

    
    if len(step_list) == 0 or range < step*3:
      return [0], [1]

    ranges = []
    steps = []
    break_point = len(step_list) - 1
    for i, item in enumerate(step_list):
      if range >= item*3:
        ranges.append(item*3)
        steps.append(item)
      else:
        break_point = i - 1
        break
    ranges[-1] = ((range-1)//step_list[break_point]+1)*step_list[break_point]

    ranges.reverse()
    steps.reverse()
    #return list of ranges and correspond steps
    return ranges, steps

  def setSearchParam(self, rotRanges, rot_steps, transRanges):
    
    print(rotRanges, rot_steps, transRanges)
    rangexyz_list = []
    stepxyz_list = []
    max_iter = 1
    for i in range(3):
      ranges, steps = self.getSearchRangeList(rotRanges[i],rot_steps[i])
      max_iter = max(len(ranges), max_iter )
      rangexyz_list.append(ranges)
      stepxyz_list.append(steps)
    
    trans_list = []
    trans_divide = np.array(transRanges)/max_iter
    for i in range(max_iter):
      trans = []
      for j in range(3):
        tmp = max(1, int(transRanges[j] - i*trans_divide[j]))
        trans.append(tmp)
      trans_list.append(trans)
    
    for i in range(3):
      if len(rangexyz_list[i]) < max_iter:
        for j in range(max_iter - len(rangexyz_list)):
          rangexyz_list[i].append(rangexyz_list[i][-1])
          stepxyz_list[i].append(stepxyz_list[i][-1])
    
    '''
    self.dTheta = "{}-{}:{}:{}{}".format('{',rotRanges[0],rot_steps[0],rotRanges[0],'}')        
    self.dPhi = "{}-{}:{}:{}{}".format('{',rotRanges[1],rot_steps[1],rotRanges[1],'}')
    self.dPsi = "{}-{}:{}:{}{}".format('{',rotRanges[2],rot_steps[2],rotRanges[2],'}')

    self.searchRadius = "{}[{} {} {}]{}".format('{',transRanges[0], transRanges[1], transRanges[2],'}')

    self.lowCutoff = "{}[0, 0.05]{}".format('{',"}")
    self.hiCutoff = "{}[0.15, 0.05]{}".format('{',"}")
    refThreshold = int(self.tomo.numberParticles*0.75)

    self.refThreshold = "{}{}{}".format('{',refThreshold,"}")
    '''
    print(rangexyz_list, stepxyz_list)
    dPhi = dTheta = dPsi = searchRadius = lowCutoff = hiCutoff = refThreshold = "{}".format("{")
    
    if len(rangexyz_list[0]) > len(rangexyz_list[1]):
      m_i = 0
      m_iter_num = len(rangexyz_list[0])
    else:
      m_i = 1
      m_iter_num = len(rangexyz_list[1])
    
    if len(rangexyz_list[2]) > m_iter_num:
      m_i = 2
      m_iter_num = len(rangexyz_list[2])

    l_0 = len(rangexyz_list[0])
    l_1 = len(rangexyz_list[1])
    l_2 = len(rangexyz_list[2])

    for i in range(max_iter):
      r_0_i = rangexyz_list[0][i] if i < l_0 else rangexyz_list[m_i][-1]
      r_1_i = rangexyz_list[1][i] if i < l_1 else rangexyz_list[m_i][-1]
      r_2_i = rangexyz_list[2][i] if i < l_2 else rangexyz_list[m_i][-1]
      s_0_i = stepxyz_list[0][i] if i < l_0 else stepxyz_list[m_i][-1]
      s_1_i = stepxyz_list[1][i] if i < l_1 else stepxyz_list[m_i][-1]
      s_2_i = stepxyz_list[2][i] if i < l_2 else stepxyz_list[m_i][-1]
      tmp_theta = "-{}:{}:{}".format(r_0_i,s_0_i,r_0_i)        
      tmp_phi = "-{}:{}:{}".format(r_1_i,s_1_i,r_1_i)
      tmp_psi = "-{}:{}:{}".format(r_2_i,s_2_i,r_2_i)

      tmp_search = "[{} {} {}]".format(trans_list[i][0], trans_list[i][1], trans_list[i][2])


      #cmd = "echo tmp_search={}; ".format(tmp_search)
      #subprocess.run(cmd,shell=True)
      tmp_lowCutoff = "[0, 0.05]"
      tmp_hiCutoff = "[0.15, 0.05]"
      tmp_refThreshold = int(self.tomo.numberParticles*0.75)
      if i < max_iter - 1:
        tmp_phi = "{}, ".format(tmp_phi)
        tmp_theta = "{}, ".format(tmp_theta)
        tmp_psi = "{}, ".format(tmp_psi)
        tmp_search = "{}, ".format(tmp_search)
        tmp_lowCutoff = "{}, ".format(tmp_lowCutoff)
        tmp_hiCutoff = "{}, ".format(tmp_hiCutoff)
        tmp_refThreshold = "{}, ".format(tmp_refThreshold)
      dPhi = "{}{}".format(dPhi, tmp_phi)
      dTheta = "{}{}".format(dTheta, tmp_theta)
      dPsi = "{}{}".format(dPsi, tmp_psi)
      searchRadius = "{}{}".format(searchRadius, tmp_search)
      lowCutoff = "{}{}".format(lowCutoff,tmp_lowCutoff)
      hiCutoff = "{}{}".format(hiCutoff,tmp_hiCutoff)
      refThreshold = "{}{}".format(refThreshold,tmp_refThreshold)

    self.dPhi = "{}{}".format(dPhi,"}")
    self.dTheta = "{}{}".format(dTheta,"}")
    self.dPsi = "{}{}".format(dPsi,"}")
    self.searchRadius = "{}{}".format(searchRadius,"}")
    self.lowCutoff = "{}{}".format(lowCutoff,"}")
    self.hiCutoff = "{}{}".format(hiCutoff,"}")
    self.refThreshold = "{}{}".format(refThreshold,"}")
    
    self.iterNum = max_iter

  def setSearchParam_old(self, rotSteps=np.array([[4,4,4],[2,2,2],[1,1,1]]), transRange=np.array([[3,3,3], [2,2,2], [1,1,1]])):
    #if rotRange == None:
    #  rotRange = np.array([[[15,5],[30,10],[15,5]]])
    #if transRange == None:
    #  transRange = np.array([[6]])
    #if len(rotRange.shape) == 2:
    #  rotRange = np.reshape(rotRange, (1,rotRange.shape[0],rotRange.shape[1]))
    iterNum1 = rotSteps.shape[0]
    iterNum2 = transRange.shape[0]
    searchIter = 3
    self.iterNum = iterNum1
    if iterNum1 != iterNum2:
      print("setSearchParam: iteration numbers for rotation and translation are not same!")
    else:
      dPhi = dTheta = dPsi = searchRadius = lowCutoff = hiCutoff = refThreshold = "{}".format("{")
      for i in range(iterNum1):
        rot = [round(x,1) for x in rotSteps[i]]
        trans = transRange[i]
        tmp_theta = "-{}:{}:{}".format(rot[0]*searchIter,rot[0],rot[0]*searchIter)        
        tmp_phi = "-{}:{}:{}".format(rot[1]*searchIter,rot[1],rot[1]*searchIter)
        tmp_psi = "-{}:{}:{}".format(rot[2]*searchIter,rot[2],rot[2]*searchIter)

        if len(trans) == 1:
          tmp_search = "[{}]".format(trans[0])
        elif len(trans) == 3:
          tmp_search = "[{} {} {}]".format(trans[0], trans[1], trans[2])
        else:
          print("setSearchParam: please input correct transpaltion format!")

        #cmd = "echo tmp_search={}; ".format(tmp_search)
        #subprocess.run(cmd,shell=True)
        tmp_lowCutoff = "[0, 0.05]"
        tmp_hiCutoff = "[0.15, 0.05]"
        tmp_refThreshold = int(self.tomo.numberParticles*0.75)
        if i < iterNum1 - 1:
          tmp_phi = "{}, ".format(tmp_phi)
          tmp_theta = "{}, ".format(tmp_theta)
          tmp_psi = "{}, ".format(tmp_psi)
          tmp_search = "{}, ".format(tmp_search)
          tmp_lowCutoff = "{}, ".format(tmp_lowCutoff)
          tmp_hiCutoff = "{}, ".format(tmp_hiCutoff)
          tmp_refThreshold = "{}, ".format(tmp_refThreshold)
        dPhi = "{}{}".format(dPhi, tmp_phi)
        dTheta = "{}{}".format(dTheta, tmp_theta)
        dPsi = "{}{}".format(dPsi, tmp_psi)
        searchRadius = "{}{}".format(searchRadius, tmp_search)
        lowCutoff = "{}{}".format(lowCutoff,tmp_lowCutoff)
        hiCutoff = "{}{}".format(hiCutoff,tmp_hiCutoff)
        refThreshold = "{}{}".format(refThreshold,tmp_refThreshold)

      self.dPhi = "{}{}".format(dPhi,"}")
      self.dTheta = "{}{}".format(dTheta,"}")
      self.dPsi = "{}{}".format(dPsi,"}")
      self.searchRadius = "{}{}".format(searchRadius,"}")
      self.lowCutoff = "{}{}".format(lowCutoff,"}")
      self.hiCutoff = "{}{}".format(hiCutoff,"}")
      self.refThreshold = "{}{}".format(refThreshold,"}")

  def setOtherParam(self, refPath, szVol=[100,100,100],cpus=24, maskType="none", yaxisType=1, flgNoReferenceRefinement=1, flgAbsValue=1):
    self.reference = refPath
    self.fnOutput = self.tomo.tomoName
    self.szVol = "[{}, {}, {}]".format(szVol[0],szVol[1],szVol[2])
    self.edgeShift = 1
    self.debugLevel = 3
    self.lstThresholds = "[{}]".format(self.tomo.numberParticles)    
    self.refFlagAllTom = 1
    self.lstFlagAllTom = 1
    self.particlePerCPU = int(math.ceil(self.tomo.numberParticles/cpus))
    self.yaxisType = yaxisType
    self.flgWedgeWeight = 1
    self.nWeightGroup = 8
    self.flgAbsValue = flgAbsValue
    self.flgNoReferenceRefinement = flgNoReferenceRefinement
    self.flgStrictSearchLimits = 1
    self.sampleSphere = "'none'"
    self.maskType = "'{}'".format(maskType)

  def generate_prm(self,latest_round=-1, exp_ref=None):
    try:     
      folderPath = "{}/{}".format(self.tomo.pickingPath, self.tomo.tomoName)
      prmFile = "{}/{}.prm".format(folderPath, self.tomo.tomoName)
      
      if os.path.exists("{}".format(prmFile)):
        os.rename(prmFile,"{}~".format(prmFile))
        
      cmd = "mkdir -p {};touch {}".format(folderPath,prmFile)
      subprocess.run(cmd,shell=True)
      
      f = open(prmFile, "w")
      
      line = "### This prm file is create by Hui Wang (UCLA) with the format defined by eTomo###\n\n"
      f.write(line)
      #print(self.tomo)
      line = "fnVolume = {}'{}'{}\n\n".format("{",self.tomo.tomogramPickPath,"}")
      f.write(line)
      line = "fnModParticle = {}'{}'{}\n\n".format("{",self.tomo.modPath,"}")
      f.write(line)
      if self.tomo.motlPath == None:
        line = "initMOTL = {}\n\n".format(0)
      else:
        line = "initMOTL = {}'{}'{}\n\n".format("{",self.tomo.motlPath,"}")
      f.write(line)
      line = "tiltRange = {}[{}, {}]{}\n\n".format("{",min(self.tomo.tlt),max(self.tomo.tlt),"}")
      f.write(line)
      line = "dPhi = {}\n\n".format(self.dPhi)
      f.write(line)
      line = "dTheta = {}\n\n".format(self.dTheta)
      f.write(line)
      line = "dPsi = {}\n\n".format(self.dPsi)
      f.write(line)
      line = "searchRadius = {}\n\n".format(self.searchRadius)
      f.write(line)
      line = "lowCutoff = {}\n\n".format(self.lowCutoff)
      f.write(line)
      line = "hiCutoff = {}\n\n".format(self.hiCutoff)
      f.write(line)
      line = "refThreshold = {}\n\n".format(self.refThreshold)
      f.write(line)
      if self.reference == None:
        if latest_round >=0:
          line = "reference = '{}'\n\n".format(exp_ref)
        else:
          line = "reference = {}\n\n".format('[1, 1]')
      else:
        line = "reference = '{}'\n\n".format(self.reference)
      f.write(line)
      line = "fnOutput = '{}'\n\n".format(self.fnOutput)
      f.write(line)
      line = "szVol = {}\n\n".format(self.szVol)
      f.write(line)
      line = "edgeShift = {}\n\n".format(self.edgeShift)
      f.write(line)
      line = "debugLevel = {}\n\n".format(self.debugLevel)
      f.write(line)
      line = "lstThresholds = {}\n\n".format(self.lstThresholds)
      f.write(line)
      line = "refFlagAllTom = {}\n\n".format(self.refFlagAllTom)
      f.write(line)
      line = "lstFlagAllTom = {}\n\n".format(self.lstFlagAllTom)
      f.write(line)
      line = "particlePerCPU = {}\n\n".format(self.particlePerCPU)
      f.write(line)
      line = "yaxisType = {}\n\n".format(self.yaxisType)
      f.write(line)
      line = "sampleSphere = {}\n\n".format(self.sampleSphere)
      f.write(line)
      line = "maskType = {}\n\n".format(self.maskType)
      f.write(line)
      line = "flgWedgeWeight = {}\n\n".format(self.flgWedgeWeight)
      f.write(line)
      line = "nWeightGroup = {}\n\n".format(self.nWeightGroup)
      f.write(line)
      line = "flgAbsValue = {}\n\n".format(self.flgAbsValue)
      f.write(line)
      line = "flgStrictSearchLimits = {}\n\n".format(self.flgStrictSearchLimits)
      f.write(line)
      line = "flgNoReferenceRefinement = {}\n\n".format(self.flgNoReferenceRefinement)
      f.write(line)

      f.close()
    except:
      print("generate prm file failed!")
      return -1
