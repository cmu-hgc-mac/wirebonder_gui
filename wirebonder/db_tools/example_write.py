import numpy as np
import asyncio
from datetime import datetime
from postgres_tools import upload_PostgreSQL, fetch_PostgreSQL
from datetime import datetime

#import all: modname, module_no

#frontside import:
#df_front_states, technician, comment, buttons

def upload_front_wirebond(modname,  technician, comment, buttons):

    #check if the module already exists in the table
    read_query = f"""SELECT EXISTS(SELECT module_name
            FROM front_wirebond
            WHERE module_name ='{modname}');"""
    check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

    #read from front_wirebond
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""

    #I don't know why, but this doesn't work unless it's inside a list
    #so get the dictionary from inside the list
    module_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]["module_no"]

    #if it does exist, give it the same frwirebond_no
    if check["exists"]:
        read_query = f"""SELECT frwirebond_no
            FROM front_wirebond
            WHERE module_name = '{modname}'
            ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""
        front_wirebond_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]['frwirebond_no']
    #if not, give it a frwirebond_no one higher than the highest already existing
    else:
        read_query = f"""SELECT frwirebond_no
            FROM front_wirebond
            ORDER BY frwirebond_no DESC LIMIT 1;"""
        front_wirebond_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]['frwirebond_no'] + 1

    list_grounded_cells = []
    list_unbonded_cells = []
    cell_no = []
    bond_count_for_cell = []
    bond_type = []
    for button in buttons:
        if buttons[button].state == 3:
            list_unbonded_cells.append(button)
        if buttons[button].grounded == 1 and (buttons[button].state == 0 or buttons[button].state == 1):
            list_grounded_cells.append(button)
        if buttons[button].state != 0:
            cell_no.append(button)
            bond_count_for_cell.append(3-buttons[button].state)
            if buttons[button].grounded == 0:
                bond_type.append("N")
            else:
                bond_type.append("G")

    date = datetime.now().date()
    time = datetime.now().time()

    db_upload = {
        'frwirebond_no' : frwirebond_no,
        'module_name' : module_name,
        'list_grounded_cells' : list_grounded_cells,
        'list_unbonded_cells' : list_unbonded_cells,
        'cell_no' : cell_no,
        'bond_count_for_cell' : bond_count_for_cell,
        'bond_type' : bond_type,
        'date' : date,
        'time' : time,
        'technician' : technician,
        'comment' : comment,
        'module_no' : module_no
    }

    try:
        asyncio.run(upload_PostgreSQL('front_wirebond', db_upload)) ## python 3.7
    except:
        (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
    print(modname, 'uploaded!')

'''
#check if the module already exists in the table
read_query = f"""SELECT EXISTS(SELECT module_name
        FROM front_wirebond
        WHERE module_name ='{modname}');"""
check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]

#if it does exist, give it the same frwirebond_no
if check["exists"]:
    read_query = f"""SELECT frwirebond_no
        FROM front_wirebond
        WHERE module_name = '{modname}'
        ORDER BY date_bond DESC, time_bond DESC LIMIT 1;"""
    front_wirebond_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]['frwirebond_no']
#if not, give it a frwirebond_no one higher than the highest already existing
else:
    read_query = f"""SELECT frwirebond_no
        FROM front_wirebond
        ORDER BY frwirebond_no DESC LIMIT 1;"""
    front_wirebond_no = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]['frwirebond_no'] + 1

list_grounded_cells = []
list_unbonded_cells = []
cell_no = []
bond_count_for_cell = []
bond_type = []
for button in buttons:
    if buttons[button].state == 3:
        list_unbonded_cells.append(button)
    if buttons[button].grounded == 1 and (buttons[button].state == 0 or buttons[button].state == 1):
        list_grounded_cells.append(button)
    if buttons[button].state != 0:
        cell_no.append(button)
        bond_count_for_cell.append(3-buttons[button].state)
        if buttons[button].grounded == 0:
            bond_type.append("N")
        else:
            bond_type.append("G")

date = datetime.now().date()
time = datetime.now().time()

db_upload = {
    'frwirebond_no' = frwirebond_no,
    'module_name' = module_name,
    'list_grounded_cells' = list_grounded_cells,
    'list_unbonded_cells' = list_unbonded_cells,
    'cell_no' = cell_no,
    'bond_count_for_cell' = bond_count_for_cell,
    'bond_type' = bond_type,
    'date' = date,
    'time' = time,
    'technician' = technician,
    'comment' = comment,
    'module_no' = module_no
    }

try:
    asyncio.run(upload_PostgreSQL('front_wirebond', db_upload)) ## python 3.7
except:
    (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
print(modname, 'uploaded!')


#####################################################

db_table_name = 'back_wirebond'
db_table_name = 'front_wirebond'
db_table_name = 'bond_pull_test'

db_upload = {
    'module_name': modname,
    'wedge_id': wedge_id,
    'spool_batch': spool_batch,
    'technician': tech,
    'date_bond' : datetime.now().date(),
    'time_bond' : datetime.now().time(),
    'comment':comment
    }

if db_table_name == 'back_wirebond':
    db_upload.update({'bond_count': bond_count})
elif db_table_name == 'bond_pull_test':
    db_upload.update({'avg_pull_strg_g': avg_pull_strg_g, 'std_pull_strg_g': avg_pull_strg_g})
elif db_table_name == 'front_wirebond':
    db_upload.update({'list_grounded_cells': dummy_list_int,
                    'list_unbonded_cells': dummy_list_int,
                    'cell_no': dummy_list_int,
                    'bond_count_for_cell': dummy_list_int,
                    'bond_type': dummy_list_str
                    })
else:
    print('Table not found! Exiting...')
    exit()

try:
    asyncio.run(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.7
except:
    (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
print(modname, 'uploaded!')
'''
