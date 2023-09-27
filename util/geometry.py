import numpy as np
import math
from eulerangles import euler2euler, euler2matrix, matrix2euler

def get_rot_matrix_PEET(rot, tilt, psi):
  a = math.radians(rot)
  b = math.radians(tilt)
  c = math.radians(psi)
  cosa = math.cos(a)
  sina = math.sin(a)
  cosb = math.cos(b)
  sinb = math.sin(b)
  cosc = math.cos(c)
  sinc = math.sin(c)
  #relion rotate reference to match 
  #inverse matrix for 
  rm1 = np.array([[cosa,-sina,0],[sina,cosa,0],[0,0,1]])
  rm2 = np.array([[1,0,0],[0,cosb,-sinb],[0,sinb,cosb]])
  rm3 = np.array([[cosc,-sinc,0],[sinc,cosc,0],[0,0,1]])
  return rm3 @ (rm2 @ rm1)


def in_boundary(target, boundary, margin_dis):
  if (target[0] > margin_dis and target[0]<boundary[0]-margin_dis) and (target[1]>margin_dis and target[1]<boundary[1]-margin_dis) and (target[2]> margin_dis and target[2]<boundary[2]-margin_dis):
    return True
  else:
    return False

def closest_distance(node, nodes):
    #node = np.asarray(node)
    deltas = nodes - node
    dist = np.einsum('ij,ij->i', deltas, deltas)
    return math.sqrt(min(dist))

def get_raw_shifts_PEET(zxz_euler, shifts):
  #input_eulers_1 = np.array([138.435, 53.922, -125.874])
  output_matrix = euler2matrix(zxz_euler,
      axes='zxz',
      intrinsic=True,
      right_handed_rotation=False)
  output_vector = np.matmul(np.linalg.inv(output_matrix), shifts)
  return(output_vector) 

def apply_slicerRot_PEET(zxz_euler, rotation):
  output_matrix_1 = euler2matrix(np.array(zxz_euler),
                                axes='zxz',
                                intrinsic=True,
                                right_handed_rotation=False)
  output_matrix_2 = euler2matrix(np.array(rotation),
                                axes='xyz',
                                intrinsic=True,
                                right_handed_rotation=True)

  output_matrix = np.matmul(output_matrix_2, output_matrix_1)
  output_eulers = matrix2euler(output_matrix,
                                axes='zxz',
                                intrinsic=True,
                                right_handed_rotation=False)
  return(output_eulers)

def PEET2Relion(zxz_euler):
  output_eulers = euler2euler(np.array(zxz_euler),
                                source_axes='zxz',
                                source_intrinsic=True,
                                source_right_handed_rotation=False,
                                target_axes='zyz',
                                target_intrinsic=False,
                                target_right_handed_rotation=False,
                                invert_matrix=True)
  return output_eulers

def Relion2ChimeraX(zxz_euler):
  output_eulers = euler2euler(zxz_euler,
                                source_axes='zyz',
                                source_intrinsic=False,
                                source_right_handed_rotation=False,
                                target_axes='zyz',
                                target_intrinsic=True,
                                target_right_handed_rotation=True,
                                invert_matrix=False)
  
  output_matrix = euler2matrix(zxz_euler,
                                axes='zyz',
                                intrinsic=False,
                                right_handed_rotation=False)

  output_vector = np.matmul([0,0,1], np.linalg.inv(output_matrix))
  return [np.round(output_eulers,3), output_vector]


def getNeighbors(v, i, threashold_dis):
	neibors_index = []
	for j, d in enumerate(v):
		if i != j and d <= threashold_dis:
			neibors_index.append(j)

	return neibors_index