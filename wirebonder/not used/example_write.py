import numpy as np
import asyncio
from datetime import datetime
from postgres_tools import upload_PostgreSQL, fetch_PostgreSQL
from datetime import datetime

def upload_front_wirebond(modname,  technician, comment, buttons):
    #read from front_wirebond
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""

    #I don't know why, but this doesn't work unless it's inside a list
    #so get the dictionary from inside the list
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
                bond_type.append("N")
            else:
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
        'module_no' : int(module_no)
    }

    try:
        asyncio.run(upload_PostgreSQL('front_wirebond', db_upload)) ## python 3.7
    except:
        (asyncio.get_event_loop()).run_until_complete(upload_PostgreSQL(db_table_name, db_upload)) ## python 3.6
    print(modname, 'uploaded!')

def upload_back_wirebond(modname, technician, comment, buttons):
    #read from front_wirebond
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""

    #I don't know why, but this doesn't work unless it's inside a list
    #so get the dictionary from inside the list
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
                bond_type.append("N")
            else:
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

def upload_bond_pull_test(modname, avg, sd, technician, comment):
    #read from front_wirebond
    read_query = f"""SELECT module_no
        FROM module_info
        WHERE module_name = '{modname}';"""

    #I don't know why, but this doesn't work unless it's inside a list
    #so get the dictionary from inside the list
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
