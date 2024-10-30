import os, subprocess 
import imodmodel
import numpy as np

from TomoNet.util.geometry import get_rot_matrix_PEET, in_boundary, closest_distance
from TomoNet.util.utils import mkfolder

class Expand:
    def __init__(self, tomo, search_param, target_cache_folder, peet_iter):
        self.tomo = tomo
        self.search_param = search_param
        self.current_folder = tomo.staPath
        self.target_cache_folder = target_cache_folder
        self.peet_iter = peet_iter
        self.threshold_CCC = search_param.threshold_CCC
        self.stop_signal=False

    def migrate(self):
        ##################  create cache folder, and move file into the cache folder  ###########################
        cmd = "mkdir -p {}".format(self.target_cache_folder)
        subprocess.run(cmd,shell=True)
        if os.path.exists(self.current_folder):
            cmd = "mv {}/* {}".format(self.current_folder, self.target_cache_folder)
            subprocess.run(cmd,shell=True)
        
    def prepare_exp(self):
        cmd = "cd {}; createAlignedModel *prm {} {}".format(self.target_cache_folder, self.peet_iter, self.threshold_CCC)
        subprocess.run(cmd,shell=True, stdout=subprocess.PIPE)
        mkfolder("{}/exp".format(self.target_cache_folder))
        prefix = os.path.basename(self.tomo.modPath).split(".")[0]

        ########################### mrc, mod. MOTL files #########################
        if os.path.exists("{}/{}_Tom1_Iter{}.mod".format(self.target_cache_folder, prefix, self.peet_iter)):
            #cmd = "cd {}/exp; ln -s ../{}_Tom1_Iter{}.mod ./{}.mod; ln -s ../{}_Tom1_Iter{}.csv ./{}_MOTL.csv; ln -s {} ./{}.mrc;".format( \
            #    self.target_cache_folder, prefix, self.peet_iter, self.tomo.tomoName, prefix, \
            #    self.peet_iter, self.tomo.tomoName, self.tomo.originTomogramPickPath, self.tomo.tomoName)
            cmd = "cd {}/exp; model2point ../{}_Tom1_Iter{}.mod ./{}.pts; point2model ./{}.pts ./{}.mod; ln -s ../{}_Tom1_Iter{}.csv ./{}_MOTL.csv; ln -s {} ./{}.mrc;".format( \
                self.target_cache_folder, prefix, self.peet_iter, self.tomo.tomoName, self.tomo.tomoName, self.tomo.tomoName, prefix, \
                self.peet_iter, self.tomo.tomoName, self.tomo.originTomogramPickPath, self.tomo.tomoName)
        else:
            #cmd = "cd {}/exp; ln -s ../{}_exp_Tom1_Iter{}.mod ./{}.mod; ln -s ../{}_exp_Tom1_Iter{}.csv ./{}_MOTL.csv; ln -s {} ./{}.mrc;".format( \
            #    self.target_cache_folder, prefix, self.peet_iter, self.tomo.tomoName, prefix, \
            #    self.peet_iter, self.tomo.tomoName, self.tomo.originTomogramPickPath, self.tomo.tomoName)
            cmd = "cd {}/exp; model2point ../{}_exp_Tom1_Iter{}.mod ./{}.pts; point2model ./{}.pts ./{}.mod; ln -s ../{}_exp_Tom1_Iter{}.csv ./{}_MOTL.csv; ln -s {} ./{}.mrc;".format( \
               self.target_cache_folder, prefix, self.peet_iter, self.tomo.tomoName, self.tomo.tomoName, self.tomo.tomoName, prefix, \
               self.peet_iter, self.tomo.tomoName, self.tomo.originTomogramPickPath, self.tomo.tomoName)
        subprocess.run(cmd,shell=True)
        
    def expand_one(self):
        ########################### RotAxes files #########################
        motlfile=open('{}/exp/{}_MOTL.csv'.format(self.target_cache_folder,self.tomo.tomoName))
        data_motl=motlfile.readlines()
        data_mod=imodmodel.read('{}/exp/{}.mod'.format(self.target_cache_folder,self.tomo.tomoName))
        with open("{}/exp/{}_RotAxes.csv".format(self.target_cache_folder,self.tomo.tomoName),"w") as f:
            for i in range(len(data_motl)-1):
                pair_motl = data_motl[i+1].split(",")[16:19]
                alpha, gama, beta = [float(x) for x in pair_motl]
                yAxis = get_rot_matrix_PEET(alpha,beta,gama) @ np.array([0,1,0])
                yAxis = [str(round(x,2)) for x in yAxis]
                if i == len(data_motl)-1:
                    f.write("{}".format(",".join(yAxis)))
                else:
                    f.write("{}\n".format(",".join(yAxis)))
        motlfile.close()
        axesfile=open('{}/exp/{}_RotAxes.csv'.format(self.target_cache_folder,self.tomo.tomoName))
        data_axes=axesfile.readlines()
        axesfile.close()

        ##################  generate new files for the next round of expansion  ###########################
        coords = []
        eulers = []
        rots = []
        qualified = []
        self.tomo.readTomo()
        boundX, boundY, boundZ = self.tomo.boundary
        threshold_dis_pixel = round(self.search_param.threshold_dis/self.tomo.apix,2)
        dis_to_bound_pixel = threshold_dis_pixel*2
        exist_particles = self.tomo.readModData()
        
        #get final coords for each of the tomograms
        transition_list = np.array(self.search_param.transition_list).reshape(-1,3)
        for i in range(0, len(data_motl)-1):
            pair_motl = data_motl[i+1].split(",")[16:19]
            X,Y,Z = [data_mod.x[i], data_mod.y[i], data_mod.z[i]]
            pair_rot = data_axes[i].split(",")

            alpha,gama,beta = [float(x) for x in pair_motl]
            rotX,rotY,rotZ = [float(x) for x in pair_rot]
            
            for i,trans in enumerate(transition_list):
                target_coords = [X,Y,Z] + get_rot_matrix_PEET(alpha,beta,gama) @ np.array(trans)
                if in_boundary(target_coords,[boundX,boundY,boundZ], dis_to_bound_pixel) and closest_distance(target_coords,exist_particles) >= threshold_dis_pixel:
                    coords.append(target_coords)
                    eulers.append([alpha,gama,beta])
                    rots.append([rotX,rotY,rotZ])
                    qualified.append(i)
                    exist_particles = np.vstack((exist_particles,target_coords))
        
        cmd = "cd {}/exp; head -n 1 {}_MOTL.csv > {}_exp_MOTL.csv".format(self.target_cache_folder, self.tomo.tomoName, self.tomo.tomoName)
        subprocess.run(cmd,shell=True)

        try:
            min_count_to_continue = self.search_param.min_count_to_continue
        except:
            min_count_to_continue = 5
        if len(coords) > min_count_to_continue:
            with open('{}/exp/{}_exp.pts'.format(self.target_cache_folder,self.tomo.tomoName),"w") as fcoord:
                with open('{}/exp/{}_exp_MOTL.csv'.format(self.target_cache_folder,self.tomo.tomoName),"a") as fmotl:
                    with open('{}/exp/{}_exp_RotAxes.csv'.format(self.target_cache_folder,self.tomo.tomoName),"w") as frot:
                        index = 0
                        for i,coord in enumerate(coords):
                            index+=1
                            motl_line = ",".join([str(x) for x in [1,0,0,index,1,0,0,0,0,0,0,0,0,0,0,0,eulers[i][0],eulers[i][1],eulers[i][2],0]]) + "\n"
                            fmotl.write(motl_line)
                            fcoord.write(" ".join([str(x) for x in coord])+"\n")
                            frot.write(",".join([str(x) for x in rots[i]])+"\n")

            cmd = "cd {}/exp; ln -s {}.mrc {}_exp.mrc; point2model {}_exp.pts {}_exp.mod ; rm {}_exp.pts".format(self.target_cache_folder, \
                self.tomo.tomoName, self.tomo.tomoName, self.tomo.tomoName, self.tomo.tomoName, self.tomo.tomoName)
            subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
        else:
            self.stop_signal=True