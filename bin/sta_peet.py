#!/usr/bin/env python3
################ This script is designed for expand particles using PEET package #################

import sys,os
import numpy as np
import math
import subprocess
from multiprocessing import Pool
import glob

from TomoNet.objects.tomogram import Tomogram
from TomoNet.objects.prmFile import PRMFile
from TomoNet.util.star_metadata import MetaData
from TomoNet.objects.expand import Expand

'''
# testing using mpram
def read_mpram(fileName):
  host = []
  try:
    with open(fileName) as file:
          for line in file: 
            line = line.strip()
            host.append(line.split())
  except:
    pass
  return host
'''  
'''
# testing run_parallel with host name
def run_parallel(host, cmd_file, cpu_used):
  cmds = []
  params = []
  try:
    with open(cmd_file) as file:
          for line in file: 
            line = line.strip()
            cmds.append(line)
            param = {}
            param['staPath'] = line.split()[1][:-1]
            param['pyfile'] = line.split()[-1]
            params.append(param)
  except:
    pass
  if len(host) > 0:
    host_p = [[x[0],int(x[1]),x[2],x[3],x[4]] for x in host]
    host_num = len(host)
    for i, p in enumerate(params):
      which_host = i % host_num
      while host_p[which_host][1] < 0:
        which_host = (which_host+1) % host_num
      
      host_p[which_host][1] -= 1
      #print(which_host, host_p[which_host][0])
      p['ssh'] = host_p[which_host][0]
      p['hostname'] = host_p[which_host][3]
    
    pool = Pool(cpu_used)
    pool.map(alignNT_host, params)
  else:
    pool = Pool(cpu_used)
    pool.map(alignNT, params)
'''

def run_parallel(cmd_file, cpu_used):
  cmds = []
  params = []
  try:
    with open(cmd_file) as file:
          for line in file: 
            line = line.strip()
            cmds.append(line)
            param = {}
            param['staPath'] = line.split()[1][:-1]
            param['pyfile'] = line.split()[-1]
            params.append(param)
  except:
    pass
  pool = Pool(cpu_used)
  pool.map(alignNT, params)

def alignNT(p):
  path = p["staPath"]
  pyfile = p["pyfile"]
  
  cmd = "cd {}; python {}".format(path, pyfile)
  result = subprocess.run(cmd, shell=True)
  return result

'''
def alignNT_host(p):
  path = p["staPath"]
  pyfile = p["pyfile"]
  cmd = "cd {}; python {}".format(path, pyfile)
  ssh = subprocess.Popen([p["ssh"], "%s" % p["hostname"], cmd], \
        shell=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  #print(pyfile, p["hostname"])
  result = ssh.stdout.readlines()
  
  return result
'''
def sta_peet_one(star_file, param_file, tomoName, cpus, first_round):
  ###################### load system params  ######################################
  #star_file = sys.argv[1]
  #param_file = sys.argv[2]
  #tomoName = sys.argv[3]
  #cpus = int(sys.argv[4])
  ################ Prepare files  ###################################

  md = MetaData()
  md.read(star_file)
  item = None
  for i in md:
    if i.rlnTomoName == tomoName:
      item = i
      break
  #######  create Folder, prepare *prm* file, mrc/rec , mod, rotaxes.csv , motl.csv  ###########
  if item != None:
    ###################### define the search parameters ##################################################
    from TomoNet.util.searchParam import SearchParam
    search_param = SearchParam(param_file)
    ###################### build current tomogram ##################################################
    tomo = Tomogram(item.rlnTomoName, initialParamFolder=item.rlnInitialParamFolder, \
      reconstructionPath=item.rlnReconstructionPath, pickingPath=item.rlnPickingPath, max_seed_num = search_param.max_seed_num)
    ########################  detect which round is going on ########################################
    cache_folder_path = "{}_cache".format(tomo.staPath)
    latest_round = -1
    
    if os.path.exists(cache_folder_path):
      rounds_num = [int(x.split("_")[1]) for x in os.listdir(cache_folder_path)]
      if len(rounds_num) > 0:
        latest_round = max(rounds_num)
      latest_cache_folder_path = "{}_cache/round_{}".format(tomo.staPath,latest_round)
      '''
      if not os.path.exists("{}/exp/{}_exp.mod".format(latest_cache_folder_path, tomo.tomoName)):
        cmd = "rm {}/* -rf".format(cache_folder_path) 
        latest_round = -1
        tomo.setInitialParams()
      else:
        tomo.updateAlignmentFile(latest_round, latest_cache_folder_path)
      '''
      if not os.path.exists("{}/exp/{}.mod".format(latest_cache_folder_path, tomo.tomoName)):
        cmd = "rm {}/* -rf".format(cache_folder_path) 
        latest_round = -1
        tomo.setInitialParams()
      elif first_round or (not os.path.exists("{}/exp/{}_exp.mod".format(latest_cache_folder_path, tomo.tomoName))):
        tomo.setInitialParams(less=False)
        target_cache_folder = "{}_cache/round_{}".format(tomo.staPath,latest_round)
        
        files_unmasked_mrc = [os.path.basename(x) for x in glob.glob("{}/unMasked*.mrc".format(target_cache_folder, tomoName))]
        files_unmasked_mrc_2 = []
        for unmasked_mrc in files_unmasked_mrc:
          if not "WGT" in unmasked_mrc:
            files_unmasked_mrc_2.append(unmasked_mrc)
        files_unmasked_mrc = files_unmasked_mrc_2
        nums = [int(x.split(".")[0].split("Ref")[1]) for x in files_unmasked_mrc]
        peet_iter = max(nums) - 1

        exp = Expand(tomo=tomo, search_param=search_param, target_cache_folder=target_cache_folder, peet_iter=peet_iter)
        exp.prepare_exp()
        exp.expand_one()
        if exp.stop_signal:
          return [tomo, search_param, target_cache_folder, peet_iter, exp.stop_signal]
        tomo.updateAlignmentFile(latest_round, latest_cache_folder_path)
      else:
        tomo.updateAlignmentFile(latest_round, latest_cache_folder_path)
    else:
      tomo.setInitialParams()
    
    tomo.setReconstructionPath()
    tomo.getParticleNumber()
    tomo.setTilt()

    prm= PRMFile(tomo)
    if latest_round >= 0:
      search_param.yaxisType = 3
      prm.setSearchParam(rotRanges=np.array(search_param.fineRotRanges),rot_steps=np.array(search_param.fineRot_steps), transRanges=np.array(search_param.fineTransRanges))
    else:
      if not tomo.rotaxesPath:
        search_param.yaxisType = 1
      prm.setSearchParam(rotRanges=np.array(search_param.rotRanges),rot_steps=np.array(search_param.rot_steps), transRanges=np.array(search_param.transRanges))
    #prm.setOtherParam(cpus=cpus, szVol=search_param.szVol, refPath=search_param.refPath, maskType=search_param.maskType, \
    #  yaxisType = search_param.yaxisType, flgNoReferenceRefinement=search_param.flgNoReferenceRefinement, flgAbsValue=search_param.flgAbsValue)
    if not search_param.reference:
      search_param.flgNoReferenceRefinement = 0
    prm.setOtherParam(cpus=cpus, szVol=search_param.box_sizes, refPath=search_param.reference, maskType=search_param.mask, \
      yaxisType = search_param.yaxisType, flgNoReferenceRefinement=search_param.flgNoReferenceRefinement, flgAbsValue=search_param.flgAbsValue)
    
    exp_ref = None
    if latest_round >=0:
      iters_len = len(glob.glob("{}/unMasked{}_Ref?.mrc".format(latest_cache_folder_path,tomo.tomoName)))
      exp_ref = "{}/unMasked{}_Ref{}.mrc".format(latest_cache_folder_path,tomo.tomoName,iters_len)
    prm.generate_prm(latest_round=latest_round, exp_ref=exp_ref)

    ######### prepare material into this tomogram folder ######################## + ########## generate job files ####################

    cmd = "cd {}; PEETCleanup *prm 1 ; prepareRef *prm ; prepareEM *prm; prmParser *prm".format(tomo.staPath)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    
    log_file_writer = open("{}/{}-exp.log".format(tomo.staPath, tomo.tomoName),"w")
    log_file_writer.write(result.stdout.decode()+"\n")

    cpu_used = int(math.ceil(tomo.numberParticles/prm.particlePerCPU))

    fill_degree = max(3,len(str(cpu_used * prm.iterNum)))

    ########### parellel run all the jobs #############################
    for k in range(prm.iterNum):
      if os.path.exists("Expand/STOP"):
        os.remove("Expand/STOP")
        sys.exit()
      out_file = "all_{}.com".format(k+1)
      cmd = "cd {}; rm -rf {}".format(tomo.staPath, out_file)
      subprocess.run(cmd,shell=True)
      for i in range(1,cpu_used+1):
        filled_num = str(k*(cpu_used+1) + i).zfill(fill_degree)

        com_file = "{}-{}.com".format(tomo.tomoName,filled_num)
        log_file = "{}-{}.log".format(tomo.tomoName,filled_num)
        py_file = "{}-{}.py".format(tomo.tomoName,filled_num)
        
        #generate py command file
        com_read = open("{}/{}".format(tomo.staPath,com_file),"r")
        alignsub_cmd = com_read.readlines()[0][1:-1]
        com_read.close()
        py_code = 'import subprocess\
          \ni=0\
          \nf=open(\"{}\",\"w\")\
          \nwhile i < 2:\
          \n  i+=1\
          \n  try:\
          \n    cmd=\'{}\'\
          \n    result=subprocess.run(cmd,shell=True,stdout=subprocess.PIPE)\
          \n    result = result.stdout.decode()\
          \n    f.write(result)\
          \n    if \"Error in alignSubset\" in str(result):\
          \n      continue\
          \n    else:\
          \n      break\
          \n  except:\
          \n    print(\"failed: {}{} times!\".format(i))\
          \nf.close()'.format(log_file, alignsub_cmd, "{", "}")
                
        f=open("{}/{}".format(tomo.staPath, py_file),"w")
        f.write(py_code)
        f.close()

        cmd = 'cd {}; echo \"cd {}; python {}\" >> {}'.format(tomo.staPath, tomo.staPath, py_file, out_file)

        subprocess.run(cmd,shell=True)

        cmd = "cd {}; rm -rf {}".format(tomo.staPath, com_file)
        subprocess.run(cmd,shell=True)

      run_parallel("{}/{}".format(tomo.staPath, out_file), cpu_used)      
      cmd = "cd {}; rm -rf *.py".format(tomo.staPath)
      subprocess.run(cmd,shell=True)

    ################## for sync #####################
      filled_num = str((k+1)*(cpu_used+1)).zfill(fill_degree)

      sync_log_file = "{}-{}-sync.log".format(tomo.tomoName,filled_num)
      sync_com_file = "{}-{}-sync.com".format(tomo.tomoName,filled_num)

      start_num = k*(cpu_used+1) + 1
      end_num = (k+1)*(cpu_used+1) -1
      if search_param.flgNoReferenceRefinement == 0:
        cmd = "cd {}; checkAlignmentLogs *.prm {} {} > {}; mergeEM *.prm {}; \
          averageAll *.prm {} both; cp {}_WGT_Iter{}.mrc unMasked{}_Ref{}_WGT.mrc; logWarningsAndErrors *.prm; rm -rf {}" \
        .format(tomo.staPath, start_num, end_num, sync_log_file, k+1, k+1, tomo.tomoName, k+1, tomo.tomoName, k+2, sync_com_file)
      else:
        cmd = "cd {}; checkAlignmentLogs *.prm {} {} > {}; mergeEM *.prm {}; \
          cp unMasked{}_Ref{}.mrc unMasked{}_Ref{}.mrc; cp {}_Ref{}.mrc {}_Ref{}.mrc; \
          averageAll *.prm {} averages ; logWarningsAndErrors *.prm; rm -rf {}" \
          .format(tomo.staPath, start_num, end_num, sync_log_file, k+1,tomo.tomoName, \
          k+1,tomo.tomoName,k+2, tomo.tomoName, k+1,tomo.tomoName,k+2, k+1, sync_com_file)
      
      result = subprocess.run(cmd,shell=True, stdout=subprocess.PIPE)
    log_file_writer.write(result.stdout.decode())
    #end_signal = True

    log_file_writer.close()
    motl_final = "{}/{}_MOTL_Tom1_Iter{}.csv".format(tomo.staPath,tomo.tomoName, prm.iterNum+1)
    motl_final_file=open(motl_final)
    data_motl=motl_final_file.readlines()
    c=0
    for i in data_motl[1:]:
      ccc = float(i.split(",")[0])
      if ccc >= search_param.threshold_CCC:
        c+=1
    target_cache_folder = "{}_cache/round_{}".format(tomo.staPath,latest_round+1)
    return [tomo, search_param, target_cache_folder, prm.iterNum, c]
  else:
    print("{} does not exist".format(tomoName))