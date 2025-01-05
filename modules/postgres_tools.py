import asyncio, asyncpg
import numpy as np
import pandas as pd
from config.conn import host, database, user, password
from datetime import datetime

# Write query
def get_query_write(table_name, column_names):
    pre_query = f""" INSERT INTO {table_name} ({', '.join(column_names)}) VALUES """
    data_placeholder = ', '.join([f"${i+1}" for i in range(len(column_names))])
    query = f"""{pre_query} ({data_placeholder});"""
    return query

def check_valid_module(modname):
    """ Example of module ID:  320MLF2CXCM0001 """
    try:
        modname = modname.replace('-','').upper()
        if modname[0:3] != "320":
            return False
        if modname[3:5] not in ["ML", "MH"]:
            return False
        if modname[5] not in ['F','T','B','L','R','5']:
            return False
        if modname[6] not in ['1','2','3']:
            return False
        if modname[7] not in ['T','W','P','C']:
            return False
        if modname[8] not in ['X','C','2','4']:
            return False
        if modname[9:11] not in ['CM','IH','NT','SB','TI','TT']:
            return False
        if not modname[-4:].isnumeric():
            return False
        return True
    except Exception as e: 
        print(e); return False
    

async def upload_PostgreSQL(pool, table_name, db_upload_data):
    async with pool.acquire() as connection: 
        query = get_query_write(table_name, db_upload_data.keys())
        try:
            await connection.execute(query, *db_upload_data.values())
            if 'module_name' in list(db_upload_data.keys()):
                print(f'Data for {db_upload_data["module_name"]} written into {table_name} table.')
        except Exception as e:
            print(e, f"for query {query}.")
            
def get_query_update(table_name, column_names, name_col):
    data_placeholder = ', '.join([f"{col} = ${i+1}" for i, col in enumerate(column_names)])
    pre_query = f""" UPDATE {table_name} SET {data_placeholder} WHERE """
    query = f""" {pre_query} {name_col} = ${1+len(column_names)}; """
    return query

async def update_PostgreSQL(pool, table_name, db_upload_data, name_col, part_name):
    async with pool.acquire() as connection: 
        query = get_query_update(table_name, list(db_upload_data.keys()), name_col)
        params = list(db_upload_data.values()) + [part_name]
        try:
            await connection.execute(query, *params)
            print(f'Data for {part_name} updated into {table_name} table.')
        except Exception as e:
            print(e, f"for query {query}.")

# Read query
async def fetch_PostgreSQL(pool, query):
    try:
        async with pool.acquire() as connection:  # Acquire a connection from the pool
            value = await connection.fetch(query)
        return value
    except Exception as e:
        print(e, f"for query {query}.")


async def add_new_to_db(pool, modname, hxbname = None):
    if len(str(modname)) != 0:
        hxbname = None if len(str(hxbname)) == 0 else str(hxbname)
        read_query = f"""SELECT EXISTS(SELECT REPLACE(module_name, '-','')
            FROM module_info
            WHERE REPLACE(module_name, '-','') ='{modname}');"""
        records = await fetch_PostgreSQL(pool, read_query)
        check = [dict(record) for record in records][0]
        if not check['exists']:
            try:
                db_upload = {'module_name' : modname, 'hxb_name' : hxbname}
                db_table_name = 'module_info'
                print(f"Uploading {modname}, {hxbname} to {db_table_name} since it doesn't exist...")
                await upload_PostgreSQL(pool, db_table_name, db_upload) 
                return True
            except asyncpg.exceptions.InsufficientPrivilegeError as e:
                print(e)
                print(f"Either change user in config/conn.py to `editor`  (OR) ")
                print(f"Use pgAdmin to add 'module_name', 'module_no', 'hxb_name' to 'module_info'.") # and 'module_assembly'.")
                # print(f"Use pgAdmin to add 'module_no', 'hxb_name' to 'hexaboard'   and 'hxb_pedestal_test'.")
                return False
            except Exception as e:
                print(f"Failed to upload data: {e}")
                return False
        return True
    return False


#get list of modules to revisit
async def find_to_revisit(pool,):
    bad_modules = {}

    read_query = f"""WITH 
            latest_fr_wb AS (SELECT DISTINCT ON (module_no) * FROM front_wirebond ORDER BY module_no DESC, (date_bond + time_bond) DESC),
            latest_bk_wb AS (SELECT DISTINCT ON (module_no) * FROM back_wirebond ORDER BY module_no DESC, (date_bond + time_bond) DESC)
            SELECT mi.module_name, fw.wb_fr_marked_done, bw.wb_bk_marked_done
            FROM module_info mi
            LEFT JOIN latest_fr_wb fw ON mi.module_no = fw.module_no
            LEFT JOIN latest_bk_wb bw ON mi.module_no = bw.module_no
            WHERE (fw.wb_fr_marked_done = false OR fw.wb_fr_marked_done IS NULL)
            OR (bw.wb_bk_marked_done = false OR bw.wb_bk_marked_done IS NULL)"""

    records = await fetch_PostgreSQL(pool, read_query)
    if records is not None:
        check = [dict(record) for record in records]
        for mod in check:
            mod["wb_fr_marked_done"] = False if mod["wb_fr_marked_done"] is None else mod["wb_fr_marked_done"]
            mod["wb_bk_marked_done"] = False if mod["wb_bk_marked_done"] is None else mod["wb_bk_marked_done"]                
            bad_modules[mod['module_name']] = [mod["wb_fr_marked_done"], mod["wb_bk_marked_done"]]
            
    return(bad_modules)

async def read_from_db(pool, modname, df_pad_map, df_backside_mbites_pos):
    d = {}
    try:
        d.update(await read_front_db(pool, modname, df_pad_map))
    except Exception as e:
        print(f"Error in reading frontside from db: {e}")
    try:
        d.update(await read_back_db(pool, modname, df_backside_mbites_pos))
    except Exception as e:
        print(f"Error in reading backside from db: {e}")
    try:
        d.update(await read_pull_db(pool, modname))
    except Exception as e:
        print(f"Error in reading pull from db: {e}")
    return d

#read frontside wirebonder information
async def read_front_db(pool, modname, df_pad_map):
    #read from front_wirebond to see if there is anything in it for this module
    read_query = f"""SELECT EXISTS(SELECT REPLACE(module_name, '-','')
        FROM front_wirebond
        WHERE REPLACE(module_name, '-','') ='{modname}');"""
    records = await fetch_PostgreSQL(pool, read_query)
    check = [dict(record) for record in records][0]

    #set defaults
    ground = []
    df_front_states = pd.DataFrame(columns=["ID","state","grounded"]).set_index('ID')
    front_wirebond_info = {'technician': None, 'comment': None, 'wedge_id':'','spool_batch':'', 'wb_fr_marked_done':False}
    front_wirebond_info.update({'list_grounded_cells':[], 'list_unbonded_cells':[], 'cell_no':[], 'bond_count_for_cell':[], 'bond_type':[]})
    front_encaps_info = {'technician': None, 'comment': None}

    #test if front_wirebond has been filled in at all
    #if so, it's an old module and read from database
    #if not, it's a new module and just read in ground info
    if not check['exists']:
        # read_query = f"""SELECT hexaboard.list_dead_cell_init, hexaboard.list_noisy_cell_init
        #        FROM module_info
        #        JOIN hexaboard ON module_info.module_no = hexaboard.module_no
        #        WHERE module_info.module_no = '{module_no}' LIMIT 1;"""
        read_query = f"""SELECT hxb_pedestal_test.list_dead_cells, hxb_pedestal_test.list_noisy_cells
                        FROM hxb_pedestal_test
                        JOIN module_info ON module_info.hxb_name = hxb_pedestal_test.hxb_name
                        WHERE REPLACE(module_info.module_name, '-','') = '{modname}'
                        ORDER BY hxb_pedestal_test.hxb_pedtest_no DESC LIMIT 1; """
        records = await fetch_PostgreSQL(pool, read_query)
        if len(records) != 0:
            res2 = [dict(record) for record in records][0]
            dead = res2['list_dead_cells']
            noisy = res2['list_noisy_cells']
            if dead != None:
                ground = np.union1d(dead, noisy) if noisy != None else dead                    
            else:
                ground = noisy if noisy != None else []
        else:
            print(f"No hexaboard record found for module {modname}.")

        for index, row in df_pad_map.iterrows():
            is_grounded = 1 if int(df_pad_map.loc[index]['padnumber']) in ground else 0
            df_front_states.loc[df_pad_map.loc[index]['padnumber']] = {"state": 0,"grounded":is_grounded}
    else:
        #I don't know why, but this doesn't work unless it's inside a list
        #so get the dictionary from inside the list
        # records = await fetch_PostgreSQL(pool, read_query)
        # front_res = [dict(record) for record in records][0]

        read_query = f"""SELECT technician, wedge_id, spool_batch, comment, wb_fr_marked_done,
        cell_no, bond_count_for_cell, bond_type, module_no,
        list_grounded_cells, list_unbonded_cells, cell_no, bond_count_for_cell, bond_type
        FROM front_wirebond
        WHERE REPLACE(module_name, '-','') = '{modname}'
        ORDER BY frwirebond_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        front_wirebond_return = [dict(record) for record in records][0]

        front_res = {tkey: front_wirebond_return[tkey]  for tkey in ['cell_no', 'bond_count_for_cell', 'bond_type', 'technician', 'comment', 'module_no']}
        front_wirebond_info = {tkey: front_wirebond_return[tkey]  for tkey in ['wedge_id', 'spool_batch', 'wb_fr_marked_done', 'technician', 'comment','list_grounded_cells', 'list_unbonded_cells', 'cell_no', 'bond_count_for_cell', 'bond_type']}

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

    #autofill wedge_id and spool_batch with the most recent one used if it's blank
    if front_wirebond_info['wedge_id'] == None or front_wirebond_info['wedge_id'] == '':
        old_w_i = {'wedge_id':"","spool_batch":""}
        read_query = f"""SELECT REPLACE(module_name, '-','') AS module_name, wedge_id
        FROM front_wirebond
        ORDER BY frwirebond_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        old_w_i_list = [dict(record) for record in records]
        if (len(old_w_i_list) > 0):
            old_w_i = old_w_i_list[0]
        front_wirebond_info['wedge_id'] = old_w_i['wedge_id']

    if front_wirebond_info['spool_batch'] == None or front_wirebond_info['spool_batch'] == '':
        read_query = f"""SELECT REPLACE(module_name, '-','') AS module_name, spool_batch
        FROM front_wirebond
        ORDER BY frwirebond_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        old_w_i_list = [dict(record) for record in records]
        if (len(old_w_i_list) > 0):
            old_w_i = old_w_i_list[0]
        front_wirebond_info['spool_batch'] = old_w_i['spool_batch']

    return {"df_front_states" : df_front_states,  "front_encaps_info": None,
        "front_wirebond_info": front_wirebond_info}

#read backside wirebonder information
async def read_back_db(pool, modname, df_backside_mbites_pos):
    #check if info on this module already exists
    read_query = f"""SELECT EXISTS(SELECT REPLACE(module_name, '-','')
        FROM back_wirebond
        WHERE REPLACE(module_name, '-','') ='{modname}');"""
    records = await fetch_PostgreSQL(pool, read_query)
    check = [dict(record) for record in records][0]

    #set defaults
    df_back_states = pd.DataFrame(columns=["ID","state","grounded"]).set_index('ID')
    back_wirebond_info = {'technician': None, 'comment': None, 'wedge_id':'','spool_batch':'', "wb_bk_marked_done":False}
    back_wirebond_info.update({"mbite_no":[], "bond_count_for_mbite":[]})
    back_encaps_info = {'technician': '', 'comment': ''}

    #test if front_wirebond has been filled in at all
    #if so, it's an "old" module and read from database
    #if not, it's a new module and just read in ground info
    if not check['exists']:
        for index, row in df_backside_mbites_pos.iterrows():
            df_back_states.loc[df_backside_mbites_pos.loc[index]['padnumber']] = {"state": 0,"grounded":0}
    else:
        
        read_query = f"""SELECT wedge_id, spool_batch, technician, comment, wb_bk_marked_done, mbite_no, bond_count_for_mbite
        FROM back_wirebond
        WHERE REPLACE(module_name, '-','') = '{modname}'
        ORDER BY bkwirebond_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        back_wirebond_return = [dict(record) for record in records][0]

        back_wirebond_states = {tkey: back_wirebond_return[tkey]  for tkey in ['mbite_no', 'bond_count_for_mbite']}
        back_wirebond_info = {tkey: back_wirebond_return[tkey]  for tkey in ['wedge_id', 'spool_batch', 'wb_bk_marked_done', 'technician', 'comment', 'mbite_no', 'bond_count_for_mbite']}

        for index, row in df_backside_mbites_pos.iterrows():
            if int(df_backside_mbites_pos.loc[index]['padnumber']) in back_wirebond_states["mbite_no"]:
                state = 3-back_wirebond_states['bond_count_for_mbite'][back_wirebond_states['mbite_no'].index(df_backside_mbites_pos.loc[index]['padnumber'])]
            else:
                state = 0
            df_back_states.loc[df_backside_mbites_pos.loc[index]['padnumber']] = {"state": state,"grounded":0}

        #autofill wedge_id and spool_batch with the most recent one used if it's blank
    if back_wirebond_info['wedge_id'] == None or back_wirebond_info['wedge_id'] == '':
        old_w_i = {"wedge_id":"", "spool_batch":""}
        read_query = f"""SELECT REPLACE(module_name, '-','') AS module_name, wedge_id
        FROM back_wirebond
        ORDER BY bkwirebond_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        old_w_i_list = [dict(record) for record in records]
        if (len(old_w_i_list)>0):
            old_w_i = old_w_i_list[0]
        back_wirebond_info['wedge_id'] = old_w_i['wedge_id']

    if back_wirebond_info['spool_batch'] == None or back_wirebond_info['spool_batch'] == '':
        read_query = f"""SELECT REPLACE(module_name, '-','') AS module_name, spool_batch
        FROM back_wirebond
        ORDER BY bkwirebond_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        old_w_i_list = [dict(record) for record in records]
        if (len(old_w_i_list)>0):
            old_w_i = old_w_i_list[0]
        back_wirebond_info['spool_batch'] = old_w_i['spool_batch']

    return { "df_back_states": df_back_states, "back_encaps_info" : None,
       "back_wirebond_info": back_wirebond_info}

#read pull test information
async def read_pull_db(pool, modname):
    #check if info already exists
    read_query = f"""SELECT EXISTS(SELECT REPLACE(module_name, '-','')
        FROM bond_pull_test
        WHERE REPLACE(module_name, '-','') ='{modname}');"""
    records = await fetch_PostgreSQL(pool, read_query)
    check = [dict(record) for record in records][0]

    #set defaults
    pull_info = {'avg_pull_strg_g': 0, 'std_pull_strg_g': 0, 'technician': None, 'comment': None}
    #test if front_wirebond has been filled in at all
    #if so, it's an old module and read from database
    #if not, it's a new module andleave as default
    if check['exists']:
        read_query = f"""SELECT avg_pull_strg_g, std_pull_strg_g, technician, comment
                FROM bond_pull_test
                WHERE REPLACE(module_name, '-','') = '{modname}'
                ORDER BY pulltest_no DESC LIMIT 1;"""
        records = await fetch_PostgreSQL(pool, read_query)
        pull_info = [dict(record) for record in records][0]

    return {"pull_info": pull_info}

async def read_encaps(pool, ):
    encaps_info = {}
    encaps_info['epoxy_batch'] = ""
    read_query = f"""SELECT epoxy_batch
     FROM front_encap
    ORDER BY frencap_no DESC LIMIT 1;"""
    records = await fetch_PostgreSQL(pool, read_query)
    res = [dict(record) for record in records]
    if (len(res)>0):
        encaps_info['epoxy_batch'] = res[0]['epoxy_batch']
    return encaps_info


#save front wirebonder information to database
async def upload_front_wirebond(pool, modname, module_no, technician, comment, wedge_id, spool_batch, marked_done = False, wb_time = None, buttons = None, lastsave_fwb = None, home_seq = None):
    #get module number
    # read_query = f"""SELECT module_no
    #     FROM module_info
    #     WHERE REPLACE(module_name, '-','') = '{modname}';"""
    # #print([dict(record) for record in asyncio.run(fetch_PostgreSQL(pool, read_query))])
    # records = await fetch_PostgreSQL(pool, read_query)
    # module_no = [dict(record) for record in records][0]["module_no"]

    technician = None if len(technician) == 0 else technician
    comment    = None if len(comment)    == 0 else comment
    technician = None if technician == 'None' else technician
    comment    = None if comment    == 'None' else comment

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
        if buttons[button].state != 0 or buttons[button].grounded != 0:
            cell_no.append(int(button))
            bond_count_for_cell.append(3-buttons[button].state)
            if buttons[button].grounded == 0:
                bond_type.append("S")
            elif buttons[button].grounded == 1:
                bond_type.append("N")
            elif buttons[button].grounded == 2:
                bond_type.append("G")
                list_grounded_cells.append(int(button))

    date_time = datetime.strptime(wb_time, "%Y/%m/%d %H:%M:%S")

    date = date_time.date()
    time = date_time.time()

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
        'module_no' : int(module_no),
        'wb_fr_marked_done': marked_done
    }

    # checkcols = ['list_grounded_cells', 'list_unbonded_cells', 'cell_no', 'bond_count_for_cell', 'bond_type', 'wedge_id' ,'spool_batch']
    lastsave_fwb_new = {tkey: db_upload[tkey] for tkey in list(lastsave_fwb.keys())}
    dict_unchanged = lastsave_fwb_new == lastsave_fwb
    if dict_unchanged:
        print(f"Data for {modname} unchanged. No new entry saved for front wirebond.")
        return True, lastsave_fwb
    else:
        if home_seq: 
            print("Either save or reset current changes to exit.")
            return False, lastsave_fwb
        db_table_name = 'front_wirebond'
        try:
            await upload_PostgreSQL(pool, db_table_name, db_upload)
            lastsave_fwb_new = {tkey: db_upload[tkey] for tkey in list(lastsave_fwb.keys())}
            return True, lastsave_fwb_new
        except Exception as e:
            print(f"Failed to upload data: {e}")
            return False, lastsave_fwb

#save back wirebonder information to database
async def upload_back_wirebond(pool, modname, module_no, technician, comment, wedge_id, spool_batch, marked_done, wb_time, buttons, lastsave_bwb = None, home_seq=None):
    #get module number
    # read_query = f"""SELECT module_no
    #     FROM module_info
    #     WHERE REPLACE(module_name, '-','') = '{modname}';"""
    # records = await fetch_PostgreSQL(pool, read_query)
    # module_no = [dict(record) for record in records][0]["module_no"]


    technician = None if len(technician) == 0 else technician
    comment    = None if len(comment)    == 0 else comment
    technician = None if technician == 'None' else technician
    comment    = None if comment    == 'None' else comment

    cell_no = []
    bond_count_for_cell = []
    bond_type = []
    for button in buttons:
        if buttons[button].state != 0:
            cell_no.append(int(button))
            bond_count_for_cell.append(3-buttons[button].state)

    date_time = datetime.strptime(wb_time, "%Y/%m/%d %H:%M:%S")

    date = date_time.date()
    time = date_time.time()

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
        'module_no' : int(module_no),
        'wb_bk_marked_done': marked_done
    }

    lastsave_bwb_new = {tkey: db_upload[tkey] for tkey in list(lastsave_bwb.keys())}
    dict_unchanged = lastsave_bwb_new == lastsave_bwb
    if dict_unchanged:
        print(f"Data for {modname} unchanged. No new entry saved for back wirebond.")
        return True, lastsave_bwb
    else:
        if home_seq: 
            print("Either save or reset current changes to exit.")
            return False, lastsave_bwb
        db_table_name = 'back_wirebond'
        try:
            await upload_PostgreSQL(pool, db_table_name, db_upload)
            return True, lastsave_bwb_new
        except Exception as e:
            print(f"Failed to upload data: {e}")
            return False, lastsave_bwb

#save pull test information to database
async def upload_bond_pull_test(pool, modname, module_no, avg, sd, technician, comment, pull_time, lastsave_fpi = None, home_seq=None):
    technician = None if len(technician) == 0 else technician
    comment    = None if len(comment)    == 0 else comment
    technician = None if technician == 'None' else technician
    comment    = None if comment    == 'None' else comment

    # #get module number
    # read_query = f"""SELECT module_no
    #     FROM module_info
    #     WHERE REPLACE(module_name, '-','') = '{modname}';"""
    # records = await fetch_PostgreSQL(pool, read_query)
    # module_no = [dict(record) for record in records][0]["module_no"]

    date_time = datetime.strptime(pull_time, "%Y/%m/%d %H:%M:%S")

    date = date_time.date()
    time = date_time.time()

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

    lastsave_fpi_new = {tkey: db_upload[tkey] for tkey in list(lastsave_fpi.keys())}
    dict_unchanged = lastsave_fpi_new == lastsave_fpi
    if dict_unchanged:
        print(f"Data for {modname} unchanged. No new entry saved for bond pull test.")
        return True, lastsave_fpi
    else:
        if home_seq: 
            print("Either save or reset current changes to exit.")
            return False, lastsave_fpi
        db_table_name = 'bond_pull_test'
        try:
            await upload_PostgreSQL(pool, db_table_name, db_upload) 
            return True, lastsave_fpi_new
        except Exception as e:
            print(f"Failed to upload data: {e}")
            return False, lastsave_fpi

#save pull test information to database
async def upload_encaps(pool, modules, modnos, technician, enc, cure_start, cure_end, temperature, rel_hum, epoxy_batch, comment):
    #if this page is empty, don't save it (causes error with inputting date and time)
    #this tests if encapsulation page is empty
    #and returns false, since we didn't actually save it
    
    date_format = "%Y/%m/%d %H:%M:%S"

    if (enc != " :00" and cure_start != " :00"): 
        enc_time = datetime.strptime(enc, date_format).time()
        enc_date = datetime.strptime(enc, date_format).date()
        cure_start = datetime.strptime(cure_start, date_format)
        if cure_end != " :00":
            cure_end = datetime.strptime(cure_end, date_format)
    elif cure_end != " :00":
        cure_end = datetime.strptime(cure_end, date_format)
        if enc != " :00" and cure_start == " :00": 
            print('Returning false since time not provided.')
            return False
    else:
        print('Returning false since time not provided.')
        return False

    for module in modules:
        
        if (enc != " :00" and cure_start != " :00"): 
            db_upload = {
                'module_name' : module,
                'date_encap' : enc_date,
                'time_encap' : enc_time,
                'technician' : technician,
                'comment' : comment,
                'cure_start': cure_start,
                'temp_c': temperature,
                'rel_hum': rel_hum,
                'epoxy_batch': epoxy_batch,
                }
            if cure_end != " :00":
                db_upload.update({'cure_end': cure_end,})

            try:  #get module number
                db_upload.update({'module_no' : modnos[module]})
                # read_query = f"""SELECT module_no
                #     FROM module_info
                #     WHERE REPLACE(module_name, '-','') = '{module}';"""
                # records = await fetch_PostgreSQL(pool, read_query)
                # module_no = [dict(record) for record in records][0]["module_no"]
                # db_upload.update({'module_no' : int(module_no),})

            except:
                print('Module number for encapsulated module not found.')

            db_table_name = "front_encap" if modules[module] == "frontside" else "back_encap"

            try:
                await upload_PostgreSQL(pool, db_table_name, db_upload) 
            except Exception as e:
                print(f"Failed to upload data: {e}") 

        elif cure_end != " :00": # and enc == " :00" and cure_start == " :00":
            db_table_name = "front_encap" if modules[module] == "frontside" else "back_encap"

            try:  
                read_query = f"""SELECT comment
                    FROM {db_table_name}
                    WHERE REPLACE(module_name, '-','') = '{module}';"""
                records = await fetch_PostgreSQL(pool, read_query)
                comment_old = [dict(record) for record in records][0]["comment"]

                db_upload = {
                    'cure_end': cure_end,
                    'comment': f"{comment_old}; {comment}", }
                
                await update_PostgreSQL(pool, db_table_name, db_upload, name_col = 'module_name', part_name = module)
            except Exception as e:
                print(f"Failed to update data: {e}") 
        else:
            print("Something happened. Data didn't save")
            return False
    return True 
        #print(modname, 'uploaded!')
