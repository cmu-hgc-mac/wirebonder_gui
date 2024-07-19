import numpy as np
import asyncio
import pandas as pd
from postgres_tools import fetch_PostgreSQL

#001 is an "old" module, 002 is "new"
modname = '320-ML-F2CX-CM-003'

#loading these files to get list of IDs from indexes
fname = '../hex_positions.csv'
df_pad_map = pd.DataFrame()
with open(fname, 'r') as file:
    #read in all the pad positions
    df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['padnumber', 'xposition', 'yposition', 'type', 'optional'])
    df_pad_map = df_pad_map[["padnumber","xposition","yposition"]].set_index("padnumber")

fname = '../mousebite_graphics_pos.csv'
df_mousebites_pos = pd.DataFrame()
with open(fname, 'r') as file:
    df_mousebites_pos = pd.read_csv(file).set_index("ID")

#read from front_wirebond
read_query = f"""SELECT cell_no, bond_count_for_cell, bond_type, technician, comment, module_no
    FROM front_wirebond
    WHERE module_name = '{modname}'
    ORDER BY frwirebond_no DESC LIMIT 1;"""

#I don't know why, but this doesn't work unless it's inside a list
#so get the dictionary from inside the list
front_res = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

#I don't know why, but this doesn't work unless it's inside a list
#so get the dictionary from inside the list
front_res = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

#set defaults
df_states = pd.DataFrame(columns=["ID","state","grounded"]).set_index('ID')
pull_info = {'avg_pull_strg_g': None, 'std_pull_strg_g': None, 'technician': None, 'comment': None}
front_wirebond_info = {'technician': None, 'comment': None}
back_wirebond_info = {'technician': None, 'comment': None}
front_encaps_info = {'technician': None, 'comment': None}
back_encaps_info = {'technician': None, 'comment': None}

#test if front_wirebond has been filled in at all
#if so, it's an old module and read from database
#if not, it's a new module and just read in ground info
if front_res['cell_no'] == None:
    read_query = f"""SELECT hexaboard.list_dead_cell_init, hexaboard.list_noisy_cell_init
            FROM module_info
            JOIN hexaboard ON module_info.module_no = hexaboard.module_no
            WHERE module_info.module_no = '{front_res["module_no"]}' LIMIT 1;"""
    res2 = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
    print(res2)
    dead = res2['list_dead_cell_init']
    noisy = res2['list_noisy_cell_init']
    ground = np.union1d(dead, noisy)
    for index, row in df_pad_map.iterrows():
        if index < 0 or index >198: #these are pads that don't correspond to pads on the board
            continue
        if int(index) in ground:
            is_grounded = 1
        else:
            is_grounded = 0
        df_states.loc[index] = {"state": 0,"grounded":is_grounded}
    for index, row in df_mousebites_pos.iterrows():
        if index[0] == 'm':
            df_states.loc[index] = {"state": 0,"grounded":0}
else:
    for index, row in df_pad_map.iterrows():
        if index < 0 or index >198: #these are pads that don't correspond to pads on the board
            continue
        if int(index) in front_res['cell_no']:
            state = 3-front_res['bond_count_for_cell'][front_res['cell_no'].index(int(index))]
            if front_res['bond_type'][front_res['cell_no'].index(int(index))] == "N":
                is_grounded = 0
            else:
                is_grounded = 1
        else:
            state = is_grounded = 0
        df_states.loc[index] = {'state' : state, 'grounded' : is_grounded}
    for index, row in df_mousebites_pos.iterrows():
        if index[0] == 'm':
            df_states.loc[index] = {"state": 0,"grounded":0}

    read_query = f"""SELECT avg_pull_strg_g, std_pull_strg_g, technician, comment
    FROM bond_pull_test
    WHERE module_name = '{modname}'
    ORDER BY pulltest_no DESC LIMIT 1;"""

    pull_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    read_query = f"""SELECT technician, comment
    FROM front_wirebond
    WHERE module_name = '{modname}'
    ORDER BY frwirebond_no DESC LIMIT 1;"""

    front_wirebond_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    read_query = f"""SELECT technician, comment
    FROM back_wirebond
    WHERE module_name = '{modname}'
    ORDER BY bkwirebond_no DESC LIMIT 1;"""

    back_wirebond_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    read_query = f"""SELECT technician, comment
    FROM front_encap
    WHERE module_name = '{modname}'
    ORDER BY frencap_no DESC LIMIT 1;"""

    front_encaps_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    read_query = f"""SELECT technician, comment
    FROM back_encap
    WHERE module_name = '{modname}'
    ORDER BY bkencap_no DESC LIMIT 1;"""

    back_encaps_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
