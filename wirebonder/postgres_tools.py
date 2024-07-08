import sys
import asyncio, asyncpg
import numpy as np
import pandas as pd
from conn import host, database, user, password
from datetime import datetime

# Write query

def get_query_write(table_name, column_names):
    pre_query = f""" INSERT INTO {table_name} ({', '.join(column_names)}) VALUES """
    data_placeholder = ', '.join(['${}'.format(i) for i in range(1, len(column_names)+1)])
    query = f"""{pre_query} {'({})'.format(data_placeholder)}"""
    return query

async def upload_PostgreSQL(table_name, db_upload_data):
    conn = await asyncpg.connect(
        host=host,
        database=database,
        user=user,
        password=password)

    schema_name = 'public'
    table_exists_query = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = $1
        AND table_name = $2
    );
    """
    table_exists = await conn.fetchval(table_exists_query, schema_name, table_name)  ### Returns True/False
    if table_exists:
        query = get_query_write(table_name, db_upload_data.keys())
        await conn.execute(query, *db_upload_data.values())
        print(f'Executing query: {query}')
        print(f'Data successfully uploaded to the {table_name}!')
    else:
        print(f'Table {table_name} does not exist in the database.')
    await conn.close()

# Read query

async def fetch_PostgreSQL(query):
    conn = await asyncpg.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )
    value = await conn.fetch(query)
    await conn.close()
    return value

# async def request_PostgreSQL(query):
#     result = await fetch_PostgreSQL(query)
#     return result

def read_from_db(modname, df_pad_map, df_backside_mbites_pos):
    d = {}
    d.update(read_front_db(modname, df_pad_map))
    d.update(read_back_db(modname, df_backside_mbites_pos))
    d.update(read_pull_db(modname))
    return d

#read frontside wirebonder information
def read_front_db(modname, df_pad_map):
    #read from front_wirebond to see if there is anything in it for this module
    read_query = f"""SELECT EXISTS(SELECT module_name
        FROM front_wirebond
        WHERE module_name ='{modname}');"""
    check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    #get module number
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    #set defaults
    df_front_states = pd.DataFrame(columns=["ID","state","grounded"]).set_index('ID')
    pull_info = {'avg_pull_strg_g': None, 'std_pull_strg_g': None, 'technician': None, 'comment': None}
    front_wirebond_info = {'technician': None, 'comment': None}
    back_wirebond_info = {'technician': None, 'comment': None}
    front_encaps_info = {'technician': None, 'comment': None}
    back_encaps_info = {'technician': None, 'comment': None}

    #test if front_wirebond has been filled in at all
    #if so, it's an old module and read from database
    #if not, it's a new module and just read in ground info
    if not check['exists']:
        read_query = f"""SELECT hexaboard.list_dead_cell_init, hexaboard.list_noisy_cell_init
                FROM module_info
                JOIN hexaboard ON module_info.module_no = hexaboard.module_no
                WHERE module_info.module_no = '{module_no}' LIMIT 1;"""
        res2 = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        dead = res2['list_dead_cell_init']
        noisy = res2['list_noisy_cell_init']
        ground = np.union1d(dead, noisy)
        for index, row in df_pad_map.iterrows():
            if int(df_pad_map.loc[index]['padnumber']) in ground:
                is_grounded = 1
            else:
                is_grounded = 0
            df_front_states.loc[df_pad_map.loc[index]['padnumber']] = {"state": 0,"grounded":is_grounded}
    else:
        #read from front_wirebond
        read_query = f"""SELECT cell_no, bond_count_for_cell, bond_type, technician, comment, module_no
            FROM front_wirebond
            WHERE module_name = '{modname}'
            ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""

        #I don't know why, but this doesn't work unless it's inside a list
        #so get the dictionary from inside the list
        front_res = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

        read_query = f"""SELECT technician, wedge_id, spool_batch, comment
        FROM front_wirebond
        WHERE module_name = '{modname}'
        ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""
        front_wirebond_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        '''
        read_query = f"""SELECT technician, comment
        FROM front_encap
        WHERE module_name = '{modname}'
        ORDER BY date_encap DESC, time_encap DESC LIMIT 1;"""

        front_encaps_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        '''
        for index, row in df_pad_map.iterrows():
            if int(df_pad_map.loc[index]['padnumber']) in front_res['cell_no']:
                state = 3-front_res['bond_count_for_cell'][front_res['cell_no'].index(df_pad_map.loc[index]['padnumber'])]
                if front_res['bond_type'][front_res['cell_no'].index(df_pad_map.loc[index]['padnumber'])] == "S":
                    is_grounded = 0
                elif front_res['bond_type'][front_res['cell_no'].index(df_pad_map.loc[index]['padnumber'])] == "N":
                    is_grounded = 1
                elif front_res['bond_type'][front_res['cell_no'].index(df_pad_map.loc[index]['padnumber'])] == "G":
                    is_grounded = 2
            else:
                state = is_grounded = 0
            df_front_states.loc[df_pad_map.loc[index]['padnumber']] = {'state' : state, 'grounded' : is_grounded}

    return {"df_front_states" : df_front_states,  "front_encaps_info":None,
        "front_wirebond_info": front_wirebond_info}

#read backside wirebonder information
def read_back_db(modname, df_backside_mbites_pos):
    #check if info on this module already exists
    read_query = f"""SELECT EXISTS(SELECT module_name
        FROM front_wirebond
        WHERE module_name ='{modname}');"""
    check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    #get module number
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    #set defaults
    df_back_states = pd.DataFrame(columns=["ID","state","grounded"]).set_index('ID')
    back_wirebond_info = {'technician': '', 'comment': ''}
    back_encaps_info = {'technician': '', 'comment': ''}

    #test if front_wirebond has been filled in at all
    #if so, it's an "old" module and read from database
    #if not, it's a new module and just read in ground info
    if not check['exists']:
        for index, row in df_backside_mbites_pos.iterrows():
            df_back_states.loc[df_backside_mbites_pos.loc[index]['padnumber']] = {"state": 0,"grounded":0}
    else:
        read_query = f"""SELECT mbite_no, bond_count_for_mbite
        FROM back_wirebond
        WHERE module_name = '{modname}'
        ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""
        back_wirebond_states = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

        read_query = f"""SELECT wedge_id, spool_batch, technician, comment
        FROM back_wirebond
        WHERE module_name = '{modname}'
        ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""
        back_wirebond_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

        '''
        read_query = f"""SELECT  comment, technician
            FROM back_encap
            WHERE module_name = '{modname}'
            ORDER BY date_encap DESC, time_encap DESC LIMIT 1;"""
        back_encaps_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        '''
        for index, row in df_backside_mbites_pos.iterrows():
            if int(df_backside_mbites_pos.loc[index]['padnumber']) in back_wirebond_states["mbite_no"]:
                state = 3-back_wirebond_states['bond_count_for_mbite'][back_wirebond_states['mbite_no'].index(df_backside_mbites_pos.loc[index]['padnumber'])]
            else:
                state = 0
            df_back_states.loc[df_backside_mbites_pos.loc[index]['padnumber']] = {"state": state,"grounded":0}

    return { "df_back_states": df_back_states, "back_encaps_info" : None,
       "back_wirebond_info": back_wirebond_info}

#read pull test information
def read_pull_db(modname):
    #check if info already exists
    read_query = f"""SELECT EXISTS(SELECT module_name
        FROM front_wirebond
        WHERE module_name ='{modname}');"""
    check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    #get module number
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    #set defaults
    pull_info = {'avg_pull_strg_g': 0, 'std_pull_strg_g': 0, 'technician': '', 'comment': ''}
    #test if front_wirebond has been filled in at all
    #if so, it's an old module and read from database
    #if not, it's a new module andleave as default
    if check['exists']:
        read_query = f"""SELECT avg_pull_strg_g, std_pull_strg_g, technician, comment
                FROM bond_pull_test
                WHERE module_name = '{modname}'
                ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""
        pull_info = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    return {"pull_info": pull_info}

#save front wirebonder information to database
def upload_front_wirebond(modname,  technician, comment, wedge_id, spool_batch, buttons):
    #get module number
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""
    print([dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))])
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    list_grounded_cells = []
    list_unbonded_cells = []
    cell_no = []
    bond_count_for_cell = []
    bond_type = []
    for button in buttons:
        if buttons[button].state == 3:
            list_unbonded_cells.append(int(button))
        if buttons[button].grounded == 1 and buttons[button].state != 3:
            list_grounded_cells.append(int(button))
        if buttons[button].state != 0:
            cell_no.append(int(button))
            bond_count_for_cell.append(3-buttons[button].state)
            if buttons[button].grounded == 0:
                bond_type.append("S")
            elif buttons[button].grounded == 1:
                bond_type.append("N")
            elif buttons[button].grounded == 2:
                bond_type.append("G")

    date = datetime.now().date()
    time = datetime.now().time()

    db_upload = {
        'module_name' : modname,
        'list_grounded_cells' : list_grounded_cells,
        'list_unbonded_cells' : list_unbonded_cells,
        'cell_no' : cell_no,
        'bond_count_for_cell' : bond_count_for_cell,
        'bond_type' : bond_type,
        'date_bond' : date,
        'time_bond' : time,
        'technician' : technician,
        'comment' : comment,
        'wedge_id' : wedge_id,
        'spool_batch': spool_batch,
        'module_no' : int(module_no)
    }

    try:
        asyncio.run(upload_PostgreSQL('front_wirebond', db_upload)) ## python 3.7
    except:
        (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
    print(modname, 'uploaded!')

#save back wirebonder information to database
def upload_back_wirebond(modname, technician, comment, wedge_id, spool_batch, buttons):
    #get module number
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    cell_no = []
    bond_count_for_cell = []
    bond_type = []
    for button in buttons:
        if buttons[button].state != 0:
            cell_no.append(int(button))
            bond_count_for_cell.append(3-buttons[button].state)

    date = datetime.now().date()
    time = datetime.now().time()

    db_upload = {
        'module_name' : modname,
        'mbite_no' : cell_no,
        'bond_count_for_mbite' : bond_count_for_cell,
        'date_bond' : date,
        'time_bond' : time,
        'technician' : technician,
        'comment' : comment,
        'wedge_id' : wedge_id,
        'spool_batch': spool_batch,
        'module_no' : int(module_no)
    }

    try:
        asyncio.run(upload_PostgreSQL('back_wirebond', db_upload)) ## python 3.7
    except:
        (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
    print(modname, 'uploaded!')

#for later:
#def upload_front_encap()
#def upload_back_encap()

#save pull test information to database
def upload_bond_pull_test(modname, avg, sd, technician, comment):
    #get module number
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    date = datetime.now().date()
    time = datetime.now().time()

    db_upload = {
        'module_name' : modname,
        'avg_pull_strg_g' : float(avg),
        'std_pull_strg_g' : float(sd),
        'date_bond' : date,
        'time_bond' : time,
        'technician' : technician,
        'comment' : comment,
        'module_no' : int(module_no)
    }

    try:
        asyncio.run(upload_PostgreSQL('bond_pull_test', db_upload)) ## python 3.7
    except:
        (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
    print(modname, 'uploaded!')
