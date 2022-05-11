import sys
import os
import numpy as np
import pickle
import bisect

'''
Generates a drone trajectory at specified command rate
'''

def waypoints_to_trajectory(waypoints, command_rate = 10):
    waypoints_t = waypoints['t']
    waypoints_pos = waypoints['pos']
    waypoints_vel = waypoints['vel']

    total_print_time = waypoints_t[-1]
    total_trajectory_points = int(np.ceil(total_print_time * command_rate))

    trajectory_t = np.arange(0, total_trajectory_points) / command_rate
    trajectory_pos = np.empty((total_trajectory_points,3))
    trajectory_vel = np.empty((total_trajectory_points,3))
    
    for i in range(total_trajectory_points):
        curr_time = trajectory_t[i]
        right_index = bisect.bisect_right(waypoints_t, curr_time)
        trajectory_vel[i,:] = waypoints_vel[right_index,:]
    # For positions, do linear interpolation
    for j in range(3):
        trajectory_pos[:,j] = np.interp(trajectory_t, waypoints_t, waypoints_pos[:,j])

    trajectory_dictionary = {}
    trajectory_dictionary['t'] = trajectory_t
    trajectory_dictionary['pos'] = trajectory_pos
    trajectory_dictionary['vel'] = trajectory_vel
    return trajectory_dictionary

def main():
    if len(sys.argv) < 2:
        sys.exit('Must provide waypoints pickle filename')
    fname = sys.argv[1]

    COMMAND_RATE = 10   # [Hz] (default)
    if len(sys.argv) >= 3:
        COMMAND_RATE = int(sys.argv[2])

    if not os.path.isfile(fname):
        sys.exit('waypoints pickle file does not exist')

    # Load pickle file
    with open(fname, "rb") as pkl_handle:
        waypoints = pickle.load(pkl_handle)

    trajectory_dictionary = waypoints_to_trajectory(waypoints, command_rate = COMMAND_RATE)

    ### Save trajectory as a pickle file
    with open(fname[:-16]+"trajectory_"+str(COMMAND_RATE)+"Hz.pickle", "wb") as pkl_handle:
	    pickle.dump(trajectory_dictionary, pkl_handle)

if __name__ == '__main__':
    main()
