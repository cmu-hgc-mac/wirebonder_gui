import asyncio, asyncpg, sys, math
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget,  QLabel, QTextEdit, QLineEdit, QCheckBox
from PyQt5.QtCore import Qt,  QPoint, QTimer
from PyQt5.QtGui import QPainter, QPen,  QPixmap, QFont, QBrush
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QComboBox
from qasync import QEventLoop, asyncSlot
from PyQt5.QtGui import QCloseEvent
import numpy as np
from modules.postgres_tools import (fetch_PostgreSQL, read_from_db, read_encaps, upload_front_wirebond, check_valid_module,
                                    upload_back_wirebond, upload_bond_pull_test, find_to_revisit, upload_encaps, add_new_to_db)
from modules.wirebonder_gui_buttons import (Hex, HexWithButtons, WedgeButton, GreyButton, SetToNominal, ResetButton, rotate_point,
                                            SaveButton, ResetButton2, HalfHexWithButtons, HalfHex, GreyCircle, HomePageButton, ScrollLabel)
import geometries.module_type_at_mac as mod_type_mac
from geometries.hxb_orientation import hxb_orientation
import config.conn as conn
from config.graphics_config import scroll_width, scroll_height, w_width, w_height, add_x_offset, add_y_offset, text_font_size, autosize
from config.conn import host, database, user, password

pool = None
scaling_factor = 90
hex_length = 0
x_offset, y_offset = 0, 0
num_non_signal = 12

async def init_pool():
    global pool
    pool = await asyncpg.create_pool(
        host=host,
        database=database,
        user=user,
        password=password,
        min_size=10,  # minimum number of connections in the pool
        max_size=50   # maximum number of connections in the pool
        )
    print('Connection pool initialized!')

async def close_pool():
    global pool
    if pool:
        await pool.close()
        print("Connection pool closed.")
        pool = None

async def async_check(pool, read_query):
    try:
        result = [dict(record) for record in await fetch_PostgreSQL(pool, read_query)]
        return result[0] if result else {}
    except Exception as e:
        print(f"Error in async_check: {e}")
        return {}

#hexaboard/"requirements" page
class FrontPage(QMainWindow):
    def __init__(self, modname, df_pad_map, df_backside_mbites_pos, df_pad_to_channel, info_dict, rotate_by_angle = 0):
        super().__init__()

        self.pageid = "frontpage"
        self.setGeometry(0, 0, w_width, w_height)

        self.scroll = QScrollArea()

        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setCentralWidget(self.scroll)
        self.rotate_by_angle = rotate_by_angle
        self.widget = QWidget()
        self.scroll.setWidget(self.widget)
        self.widget.resize(scroll_width, scroll_height);
        self.vbox = QVBoxLayout()  # Create a layout for the buttons
        self.widget.setLayout(self.vbox)  # Set the layout for the widget contained within the scroll area
        self.buttons = {}
        self.modname = modname
        self.df_pad_map = df_pad_map
        self.df_backside_mbites_pos = df_backside_mbites_pos
        self.info_dict = info_dict
        self.df_pad_to_channel = df_pad_to_channel

        self.fwb_lastsave = self.info_dict["front_wirebond_info"]
        self.fpi_lastsave = self.info_dict["pull_info"]
        self.df_front_states = self.info_dict["df_front_states"]
        self.df_back_states = self.info_dict["df_back_states"]
        #set state counter
        self.state_counter = {0: len(self.df_front_states[self.df_front_states['state'] == 0]), 
                              1: len(self.df_front_states[self.df_front_states['state'] == 1]),
                              2: len(self.df_front_states[self.df_front_states['state'] == 2]), 
                              3: len(self.df_front_states[self.df_front_states['state'] == 3])}
        self.state_counter_labels = {}
        self.ground_tracker_labels = {}
        self.state_button_labels = {}
        tobegroundedlist = self.df_front_states.index[self.df_front_states['grounded'] == 1].tolist()
        tobegroundedlist = str([int(i) for i in tobegroundedlist])
        groundedlist = self.df_front_states.index[self.df_front_states['grounded'] == 2].tolist()
        groundedlist = str([int(i) for i in groundedlist])
        
        #make label of state counter
        for state in self.state_counter:
            lab = QLabel(f"{state} missing bonds: {self.state_counter[state]}", self.widget)
            lab.setGeometry(20,10 + state * 20,250, 20)
            self.state_counter_labels[state] = lab

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        #side bar buttons and text entry
        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, 
                                      self.modname, "Set to nominal", self.buttons, 90, 25, self.widget, ground_tracker_labels = self.ground_tracker_labels)
        nominal_button.setGeometry(200,75, nominal_button.width, nominal_button.height)
        nominal_button.show()

        lab6 = QLabel("<b>Wirebonding Information:</b>", self.widget)
        lab6.setGeometry(20,275, 200, 25)
        lab6 = QLabel("Technician CERN ID:", self.widget)
        lab6.setGeometry(20,300, 150, 25)
        self.techname = QLineEdit(self.widget)
        self.techname.setGeometry(20,325, 150, 25)
        self.techname.setText(self.info_dict["front_wirebond_info"]["technician"])
        lab4 = QLabel("Comments:", self.widget)
        lab4.setGeometry(20,515,150,50)
        self.comments = QTextEdit(self.widget)
        self.comments.setGeometry(20, 560, 150, 150)
        self.comments.setText(self.info_dict["front_wirebond_info"]["comment"])
        lab4 = QLabel("Wedge ID:", self.widget)
        lab4.setGeometry(20,340,150,50)
        self.wedgeid = QLineEdit(self.widget)
        self.wedgeid.setGeometry(20, 380, 150, 25)
        self.wedgeid.setText(self.info_dict["front_wirebond_info"]["wedge_id"])
        lab4 = QLabel("Spool batch:", self.widget)
        lab4.setGeometry(20,400,150,50)
        self.spool = QLineEdit(self.widget)
        self.spool.setGeometry(20, 440, 150, 25)
        self.spool.setText(self.info_dict["front_wirebond_info"]["spool_batch"])
        lab4 = QLabel("Date and time:", self.widget)
        lab4.setGeometry(20,455,150,50)
        self.wb_time = QLineEdit(self.widget)
        self.wb_time.setGeometry(20, 500, 150, 25)
        self.wb_time.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))


        labellegend = QLabel("<b>Legend:</b><br><b>Black mesh</b>: \
                        Needs to be grounded(R-clk)<br>Black fill: Grounded(R-clk)<br>Blue: nominal;  Yellow: 1 failed bond<br>Orange: \
                        2 failed bonds; Red: 3 failed bonds<br>",
                        self.widget)
        lfont = QFont()
        lfont.setPointSize(10)  
        labellegend.setFont(lfont)
        labellegend.setWordWrap(True)
        labellegend.setTextFormat(Qt.RichText)

        labellegend.setGeometry(20,90, 300,80)
        labeltbgrounded = QLabel(f"ToBeGrounded: {tobegroundedlist}", self.widget)
        labelgrounded = QLabel(f"Grounded: {groundedlist}", self.widget)
        labelgrounded.setFont(lfont)
        labeltbgrounded.setFont(lfont)
        labelgrounded.setWordWrap(True)
        labeltbgrounded.setWordWrap(True)
        labeltbgrounded.setGeometry(20,90+80, 300,20)
        labelgrounded.setGeometry(20,90+100, 300,20)
        self.ground_tracker_labels['tobegroundedlist'] = labeltbgrounded
        self.ground_tracker_labels['groundedlist'] = labelgrounded

        info_label = QLabel("<a href=\"https://github.com/cmu-hgc-mac/wirebonder_gui/blob/main/README.md\">Help",self.widget)
        info_label.setOpenExternalLinks(True)
        info_label.setGeometry(250, 110, 100, 25)

        self.marked_done = QCheckBox("Frontside complete", self.widget)
        self.marked_done.setGeometry(20,245,150,25)
        if self.info_dict["front_wirebond_info"]["wb_fr_marked_done"]:
            self.marked_done.setCheckState(Qt.Checked)

        lab6 = QLabel("<b>Pull Test (optional):</b>", self.widget)
        lab6.setGeometry(20,735, 200, 25)
        lab6 = QLabel("Technician CERN ID:", self.widget)
        lab6.setGeometry(20,760, 150, 25)
        self.pull_techname = QLineEdit(self.widget)
        self.pull_techname.setGeometry(20,785, 150, 25)
        lab4 = QLabel("Comments:", self.widget)
        lab4.setGeometry(20,980,150,50)
        self.pull_comments = QTextEdit(self.widget)
        self.pull_comments.setGeometry(20, 1025, 150, 150)
        lab4 = QLabel("Mean:", self.widget)
        lab4.setGeometry(20,800,150,50)
        self.mean = QLineEdit(self.widget)
        self.mean.setGeometry(20, 840, 150, 25)
        lab4 = QLabel("Standard deviation:", self.widget)
        lab4.setGeometry(20,860,150,50)
        self.std = QLineEdit(self.widget)
        self.std.setGeometry(20, 900, 150, 25)
        lab4 = QLabel("Date and time:", self.widget)
        lab4.setGeometry(20,925,150,50)
        self.pull_time = QLineEdit(self.widget)
        self.pull_time.setGeometry(20, 965, 150, 25)
        self.pull_time.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))


        #load pull test data
        self.pull_techname.setText(str(self.info_dict["pull_info"]["technician"]))
        self.mean.setText(str(self.info_dict["pull_info"]["avg_pull_strg_g"]))
        self.std.setText(str(self.info_dict["pull_info"]["std_pull_strg_g"]))
        self.pull_comments.setText(str(self.info_dict["pull_info"]["comment"]))

        reset_button = ResetButton2(self.modname, "front", self.df_pad_map, self.techname, 
                                    self.comments , "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50,
            self.pull_techname, self.pull_comments, self.std, self.mean, self.widget, pool = pool, ground_tracker_labels = self.ground_tracker_labels)
        reset_button.setGeometry(200,10, reset_button.width, reset_button.height)
        reset_button.show()

        pads = []
        for index,row0 in self.df_pad_map.iterrows():   #make all the cells
            padnumber = int(df_pad_map.loc[index]['padnumber'])
            #row of the dataframe that converts between pad and the channel number of the channel on that pad
            row1 = self.df_pad_to_channel.loc[padnumber]
            #row of the dataframe that gives the pad ID, channel state, and whether or not it's grounded
            row2 = self.df_front_states.loc[padnumber]
            if row1['Channeltype'] == 0 and index > -1:
                pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, 
                                        self.state_button_labels,row2['state'],row2['grounded'], hex_length, str(padnumber), [0,0],
                                        str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget, rotate_by_angle = self.rotate_by_angle, ground_tracker_labels = self.ground_tracker_labels)
                #wedge buttons associated with cells are automatically added to button dictionary
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 +x_offset),
                                int(float(row0["yposition"]*-1*scaling_factor + y_offset+ w_height/2)), int(pad.radius*2), int(pad.radius*2))
                pad.raise_()  #set pad position
            
            elif row1['Channeltype'] == 2 and index > -1:  #create half hexagon cells
                pad = HalfHexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, 
                                         self.state_button_labels,row2['state'],row2['grounded'], hex_length, str(padnumber), [0,0],
                                         str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8',row1['Channeltype'],  self.widget, rotate_by_angle = self.rotate_by_angle, ground_tracker_labels = self.ground_tracker_labels)
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 +x_offset),
                                int(float(row0["yposition"]*-1*scaling_factor + y_offset+ w_height/2)), int(pad.radius*2), int(pad.radius*2))
            elif row1['Channeltype'] == 3 and index > -1:
                pad = HalfHexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, 
                                         self.state_button_labels,row2['state'],row2['grounded'], hex_length, str(padnumber), [0,0],
                                         str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8',row1['Channeltype'],  self.widget, rotate_by_angle = self.rotate_by_angle, ground_tracker_labels = self.ground_tracker_labels)
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 + x_offset),
                                int(float(row0["yposition"]*-1*scaling_factor + y_offset+ w_height/2)), int(pad.radius*2), int(pad.radius*2))

                
            #create calibration channels
            elif self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 1 and padnumber > 0:
                hex_before, hex_after = False, False
                hexchanpos = self.df_pad_map.loc[index]['padnumber']
                hexnumafter = self.df_pad_map.loc[index+1]['padnumber']
                hex_after = (self.df_pad_map.loc[index+1]['xposition'] == row0["xposition"] and 
                                 self.df_pad_map.loc[index+1]['yposition'] == row0["yposition"]
                        and self.df_pad_to_channel.loc[hexnumafter]['Channeltype'] == 0)
                hexnumbefore = self.df_pad_map.loc[index-1]['padnumber']
                hex_before = (self.df_pad_map.loc[index-1]['xposition'] == row0["xposition"] and 
                                  self.df_pad_map.loc[index-1]['yposition'] == row0["yposition"]
                        and self.df_pad_to_channel.loc[hexnumbefore]['Channeltype'] == 0)
                if hex_after:
                    hexchanpos = self.df_pad_to_channel.loc[hexnumafter]['Channelpos']
                elif hex_before:
                    hexchanpos = self.df_pad_to_channel.loc[hexnumbefore]['Channelpos']
                
                xoff, yoff = 0,0
                if hex_after or hex_before:
                    angoff = (((hexchanpos+3)%6) * np.pi/3 ) - np.pi/2 - self.rotate_by_angle
                    xoff, yoff = pad.radius*np.cos(angoff)/2, pad.radius*np.sin(angoff)/2
                    
                pad = WedgeButton(self.state_counter, self.state_counter_labels, 
                                  self.state_button_labels, row2['state'], row2['grounded'],
                                  str(row1['Channel']), 6, str(padnumber), [0,0], hex_length/3, self.widget, rotate_by_angle = self.rotate_by_angle, ground_tracker_labels = self.ground_tracker_labels)
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 + hex_length*2/3 +x_offset + xoff),
                                int(float(row0["yposition"]*-1*scaling_factor + y_offset+w_height/2+hex_length*2/3) + yoff), int(pad.radius*2), int(pad.radius*2))
                self.buttons[str(padnumber)] = pad #add manually to list of buttons
                pad.raise_()
            #create mousebites and guardrails
            else:  #want these to be circular so pass channel_pos = 6
                size = hex_length/3 if padnumber < -12 else 13 # guardrail button size; mousebite size
                pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'],
                    str(padnumber), 6, str(chr(64+abs(padnumber))), [0,0], size, self.widget, ground_tracker_labels = self.ground_tracker_labels)
                pad.setGeometry(int(float(row0["xposition"])*scaling_factor + scroll_width/2 + scaling_factor*0.25 + x_offset),
                                int(float(row0["yposition"]*-1*scaling_factor + y_offset + w_height/2 + scaling_factor*0.25)),
                    int(pad.radius*2), int(pad.radius*2))
                self.buttons[str(padnumber)] = pad  #manually add to list of buttons
            
            pads.append(pad)  #add to list of pads
            

        #this brings pads in position 3 to the front to remove problematic overlap in clicking areas
        for pad in pads:
            if pad.channel_pos == 3:
                pad.activateWindow()
                pad.raise_()
            if pad.channel_pos == 6:
                pad.activateWindow()
                pad.raise_()

#hexaboard/"requirements" page
class BackPage(QMainWindow):
    def __init__(self, modname, df_pad_map, df_backside_mbites_pos, df_pad_to_channel, info_dict, rotate_by_angle = 0, load_pin_padnum = [0,1]):
        super().__init__()
        self.pageid = "backpage"
        self.setGeometry(0, 0, w_height, w_height)
        self.rotate_by_angle = rotate_by_angle
        self.load_pin_padnum = load_pin_padnum
        self.scroll = QScrollArea()

        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setCentralWidget(self.scroll)

        self.widget = QWidget()
        self.scroll.setWidget(self.widget)
        self.widget.resize(scroll_width, scroll_height);
        self.vbox = QVBoxLayout()  # Create a layout for the buttons
        self.widget.setLayout(self.vbox)  # Set the layout for the widget contained within the scroll area
        self.buttons = {}
        self.modname = modname
        self.df_pad_map = df_pad_map
        self.df_backside_mbites_pos = df_backside_mbites_pos
        self.info_dict = info_dict
        self.df_pad_to_channel = df_pad_to_channel
        
        self.bwb_lastsave = self.info_dict["back_wirebond_info"]
        #self.df_front_states = self.info_dict["df_front_states"]
        self.df_back_states = self.info_dict["df_back_states"]
        #set state counter
        self.state_counter = {0: len(self.df_back_states[self.df_back_states['state'] == 0]), 
                              1: len(self.df_back_states[self.df_back_states['state'] == 1]),
                              2: len(self.df_back_states[self.df_back_states['state'] == 2]), 
                              3: len(self.df_back_states[self.df_back_states['state'] == 3])}
        self.state_counter_labels = {}
        self.state_button_labels = {}

        #make label of state counter
        for state in self.state_counter:
            lab = QLabel(f"{state} missing bonds: {self.state_counter[state]}", self.widget)
            lab.setGeometry(20,10 + state * 20,250, 20)
            self.state_counter_labels[state] = lab

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, self.modname, "Set to nominal", self.buttons, 90, 25, self.widget)
        nominal_button.setGeometry(200, 75, nominal_button.width, nominal_button.height)
        nominal_button.show()
        info_label = QLabel("<a href=\"https://github.com/cmu-hgc-mac/wirebonder_gui/blob/main/README.md\">Help",self.widget)
        info_label.setOpenExternalLinks(True)
        info_label.setGeometry(200, 110, 100, 25)

        lab6 = QLabel("Technician CERN ID:", self.widget)
        lab6.setGeometry(20,100, 150, 25)
        self.techname = QLineEdit(self.widget)
        self.techname.setGeometry(20,125, 150, 25)
        self.techname.setText(self.info_dict["back_wirebond_info"]["technician"])
        lab4 = QLabel("Comments:", self.widget)
        lab4.setGeometry(20,365,150,50)
        self.comments = QTextEdit(self.widget)
        self.comments.setGeometry(20, 405, 150, 150)
        self.comments.setText(self.info_dict["back_wirebond_info"]["comment"])
        lab4 = QLabel("Wedge ID:", self.widget)
        lab4.setGeometry(20,140,150,50)
        self.wedgeid = QLineEdit(self.widget)
        self.wedgeid.setGeometry(20, 180, 150, 25)
        self.wedgeid.setText(self.info_dict["back_wirebond_info"]["wedge_id"])
        lab4 = QLabel("Spool batch:", self.widget)
        lab4.setGeometry(20,200,150,50)
        self.spool = QLineEdit(self.widget)
        self.spool.setGeometry(20, 240, 150, 25)
        self.spool.setText(self.info_dict["back_wirebond_info"]["spool_batch"])
        self.marked_done = QCheckBox("Backside complete", self.widget)
        self.marked_done.setGeometry(20,280,150,25)
        if self.info_dict["back_wirebond_info"]["wb_bk_marked_done"]:
            self.marked_done.setCheckState(Qt.Checked)

        lab4 = QLabel("Date and time:", self.widget)
        lab4.setGeometry(20,305,150,50)
        self.wb_time = QLineEdit(self.widget)
        self.wb_time.setGeometry(20, 345, 150, 25)
        self.wb_time.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

        reset_button = ResetButton(self.modname, "back", self.df_backside_mbites_pos, self.techname, self.comments , "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50, self.widget, pool = pool)
        reset_button.setGeometry(200,10, reset_button.width, reset_button.height)
        reset_button.show()

        pads = []
        min_padnum = self.df_pad_map[self.df_pad_map['padnumber'] > 0]['padnumber'].min()
        max_padnum = self.df_pad_map['padnumber'].max()

        #make all the cells
        for index,row0 in self.df_pad_map.iterrows():
            padnumber = int(row0['padnumber'])
            padlabel = str(int(row0['padnumber'])) if row0['padnumber'] == min_padnum or row0['padnumber'] == max_padnum else ''
            #normal cells without buttons
            if self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 0 and index > -1:
                pad = Hex(hex_length, padlabel, [0,0],'#d1d1d1', self.widget, rotate_by_angle=-self.rotate_by_angle)
                pad.setGeometry(int(float(row0["xposition"]*-1*scaling_factor) + scroll_width/2 +x_offset),int(float(row0["yposition"]*-1*scaling_factor + w_height/2 + y_offset)), int(pad.radius*2), int(pad.radius*2))
            #half hexagons->   2<->3 swapped for backside by doing 5-channeltype
            elif (self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 2 or self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 3) and index > -1:
                pad = HalfHex(hex_length, padlabel, [0,0],'#d1d1d1', int(5 - self.df_pad_to_channel.loc[row0['padnumber']]['Channeltype']), self.widget, rotate_by_angle=-self.rotate_by_angle)
                pad.setGeometry(int(float(row0["xposition"]*-1*scaling_factor) + scroll_width/2 +x_offset),int(float(row0["yposition"]*-1*scaling_factor + w_height/2 + y_offset)), int(pad.radius*2), int(pad.radius*2))

            pads.append(pad)

        for index,row in self.df_backside_mbites_pos.iterrows():
            padnumber = int(row['padnumber'])
            #want these to be circular so pass channel_pos = 6
            pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, self.df_back_states.loc[padnumber]['state'], self.df_back_states.loc[padnumber]['grounded'],
                str(padnumber), 6, str(chr(64+abs(padnumber))), [0,0], 13, self.widget, rotate_by_angle=self.rotate_by_angle)
            pad.setGeometry(int(float(row["xposition"])*-1*scaling_factor + scroll_width/2+ scaling_factor*0.25 + x_offset),int(float(row["yposition"]*-1*scaling_factor + w_height/2+ y_offset + scaling_factor*0.3)), int(pad.radius*2), int(pad.radius*2))
            self.buttons[str(padnumber)] = pad

        for lp in range(len(self.load_pin_padnum)):
            xpos = list(self.df_pad_map.loc[self.df_pad_map['padnumber'] == int(self.load_pin_padnum[lp]), 'xposition'])
            ypos = list(self.df_pad_map.loc[self.df_pad_map['padnumber'] == int(self.load_pin_padnum[lp]), 'yposition'])
            if len(xpos) != 0 :
                xoff, yoff = hex_length/2, hex_length/2
                pad2 = GreyCircle(13, 0, 0, self.widget)
                pad2.setGeometry(int(float(xpos[0]*-1*scaling_factor) + scroll_width/2 +x_offset + xoff),
                                int(float(ypos[0]*-1*scaling_factor + w_height/2 + y_offset) + yoff), int(pad.radius*2), int(pad.radius*2))
        


class EncapsPage(QMainWindow):
    def __init__(self, parent = None):
        super().__init__(parent)
        encap_space = 7
        encap_left_align = 300
        self.pageid = "encapspage"
        self.setWindowTitle("Tri-State Buttons")
        self.setGeometry(0, 0, w_width, w_height)

        self.scroll = QScrollArea()
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)  # Allow the widget inside the scroll area to resize
        self.setCentralWidget(self.scroll)

        self.widget = QWidget()
        self.scroll.setWidget(self.widget)
        self.vbox = QVBoxLayout()  # Create a layout for the buttons
        self.widget.setLayout(self.vbox)  # Set the layout for the widget contained within the scroll area
        self.widget.adjustSize()

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        self.timestatlabel = QLabel(self) #"Module type:",self)
        self.timestatlabel.setGeometry(10, 5, 700, 25)
        self.timestatlabel.show()

        lab2 = QLabel("Encapsulation Technician CERN ID:", self)
        lab2.setGeometry(encap_left_align, 40, 400, 25)
        self.techname = QLineEdit(self)
        self.techname.setGeometry(encap_left_align,45+20, 150, 25)

        label = QLabel("Epoxy Batch:", self)
        label.setGeometry(encap_left_align,70+20, 100, 25)
        self.epoxy_batch = QLineEdit(self)
        self.epoxy_batch.setText("Waiting for batch...")
        self.epoxy_batch.setGeometry(encap_left_align,95+20, 150, 25)
        
        label = QLabel("Time of Encapsulation (YYYY/MM/DD, HH:MM in 24h time):", self)
        label.setGeometry(encap_left_align,120+30, 400, 25)
        label = QLabel("Date: ", self)
        label.setGeometry(encap_left_align,145+30, 40, 25)
        self.enc_date = QLineEdit(self)
        self.enc_date.setGeometry(10 + label.geometry().left() + label.geometry().width(),145+30, 150, 25)
        label = QLabel("Time: ", self)
        label.setGeometry(10 + self.enc_date.geometry().left() + self.enc_date.geometry().width(),145+30, 40, 25)
        self.enc_time = QLineEdit(self)
        self.enc_time.setGeometry(10 + label.geometry().left() + label.geometry().width(),145+30, 150, 25)
        nowbutton1 = GreyButton("Now", 50, 25, self)
        nowbutton1.setGeometry(10 + self.enc_time.geometry().left() + self.enc_time.geometry().width(), 145+30, 50, 25)
        nowbutton1.clicked.connect(lambda: self.set_to_now(self.enc_date, self.enc_time))

        labelline1 = QLabel("----------------------------------------------------------------------", self)
        labelline1.setGeometry(encap_left_align, 180+30-5, 500, 25)

        label = QLabel("Cure <b>start</b> (YYYY/MM/DD, HH:MM in 24h time):", self)
        label.setGeometry(encap_left_align,205+30-5, 400, 25)
        label = QLabel("Date: ", self)
        label.setGeometry(encap_left_align,230+30-5, 40, 25)
        self.start_date = QLineEdit(self)
        self.start_date.setGeometry(10 + label.geometry().left() + label.geometry().width(),230+30-5, 150, 25)
        label = QLabel("Time: ", self)
        label.setGeometry(10 + self.start_date.geometry().left() + self.start_date.geometry().width(),230+30-5, 40, 25)
        self.start_time = QLineEdit(self)
        self.start_time.setGeometry(10 + label.geometry().left() + label.geometry().width(),230+30-5, 150, 25)
        nowbutton2 = GreyButton("Now", 50, 25, self)
        nowbutton2.setGeometry(10 + self.start_time.geometry().left() + self.start_time.geometry().width(), 230+30-5, 50, 25)
        nowbutton2.clicked.connect(lambda: self.set_to_now(self.start_date, self.start_time))

        label = QLabel("Temperature:", self)
        label.setGeometry(encap_left_align,255+30-5, 150, 25)
        self.temperature = QLineEdit(self)
        self.temperature.setGeometry(encap_left_align,280+30-5, 150, 25)
        label = QLabel("Relative Humidity:",self)
        label.setGeometry(15 + self.temperature.geometry().left() + self.temperature.geometry().width(),255+30-5, 150, 25)
        self.rel_hum = QLineEdit(self)
        self.rel_hum.setGeometry(15 + self.temperature.geometry().left() + self.temperature.geometry().width(),280+30-5, 150, 25)

        labelline2 = QLabel("----------------------------------------------------------------------", self)
        labelline2.setGeometry(encap_left_align, 335, 500, 25)

        label = QLabel("Cure <b>end</b> (YYYY/MM/DD, HH:MM in 24h time):", self)
        label.setGeometry(encap_left_align,360, 400, 25)
        label = QLabel("Date: ", self)
        label.setGeometry(encap_left_align,385, 40, 25)
        self.end_date = QLineEdit(self)
        self.end_date.setGeometry(10 + label.geometry().left() + label.geometry().width(),385, 150, 25)
        label = QLabel("Time: ", self)
        label.setGeometry(10 + self.end_date.geometry().left() + self.end_date.geometry().width(),385, 40, 25)
        self.end_time = QLineEdit(self)
        self.end_time.setGeometry(10 + label.geometry().left() + label.geometry().width(),385, 150, 25)
        nowbutton3 = GreyButton("Now", 50, 25, self)
        nowbutton3.setGeometry(10 + self.end_time.geometry().left() + self.end_time.geometry().width(), 385, 50, 25)
        nowbutton3.clicked.connect(lambda: self.set_to_now(self.end_date, self.end_time))
        
        labelline3 = QLabel("----------------------------------------------------------------------", self)
        labelline3.setGeometry(encap_left_align, 410, 500, 25)

        lab6 = QLabel("Comments:", self)
        lab6.setGeometry(encap_left_align,435, 150, 25)
        self.comments= QTextEdit(self)
        self.comments.setGeometry(encap_left_align, 460, 300, 150)

        self.label2 = QLabel("Module ID:",self)
        self.label2.setGeometry(20, 70, 150, 25)
        self.modid = QLineEdit(self)
        self.modid.setGeometry(20, 100, 150, 25)
        self.scrolllabel = ScrollLabel(self)
        self.scrolllabel.setGeometry(20, 300, 250, 150)
        self.problemlabel = QLabel("This module isn't available.", self)
        self.problemlabel.setGeometry(20,260, 200, 25)
        self.problemlabel.hide()

        addbutton = GreyButton("Add", 75, 25, self)
        addbutton.setGeometry(20, 180, 75, 25)
        addbutton.clicked.connect(self.add)
        removebutton = GreyButton("Remove", 75, 25, self)
        removebutton.setGeometry(125, 180, 75, 25)
        removebutton.clicked.connect(self.remove)
        addbutton = GreyButton("Clear All", 90, 25, self)
        addbutton.setGeometry(20, 220, 100, 25)
        addbutton.clicked.connect(self.clearall)
        self.combobox2 = QComboBox(self)
        self.combobox2.addItems(["frontside", "backside"])
        self.combobox2.setGeometry(15, 140, 150, 25)
        self.modules = {}
        self.modnos = {}
        self.async_epoxy_batch()

    def run_async_function(self):
        asyncio.ensure_future(self.async_task())
    
    @asyncSlot()
    async def async_epoxy_batch(self):
        result = await read_encaps(pool)  
        self.epoxy_batch.setText(result["epoxy_batch"])

    async def check_mod_exists_encap(self,modname):
        read_query = f"""SELECT( SELECT module_no FROM module_info WHERE REPLACE(module_name, '-','') = '{modname}' LIMIT 1) as in_info;"""
        check = await async_check(pool, read_query)
        if check['in_info'] is not None:
            self.modules[modname] = self.combobox2.currentText()
            self.modnos[modname] = check['in_info']
            string = "\n".join(f"{module} {self.modules[module]}" for module in self.modules)
            self.scrolllabel.setText(string)
        else:
            self.problemlabel.show()

    def add(self):
        self.problemlabel.hide()
        modname = (self.modid.text()).replace("-","")
        try:
            asyncio.create_task(self.check_mod_exists_encap(modname=modname))
        except Exception as e:
            print(e)

    def remove(self):
        modname = (self.modid.text()).replace("-","")
        if modname in self.modules and self.modules[modname] == self.combobox2.currentText():
            del self.modules[modname]
            del self.modnos[modname]
        string = ""
        for module in self.modules:
            string = string + module +' ' + self.modules[module] + "\n"
        self.scrolllabel.setText(string)
    
    def clearall(self):
        self.modules = {}
        self.modnos = {}
        self.scrolllabel.setText("")

    def set_to_now(self,date, time):
        now = datetime.now()
        date.setText(str(now.strftime("%Y")) + "/" + str(now.strftime("%m")) + "/" + str(now.strftime("%d")))
        time.setText(str(now.strftime("%H"))+":"+str(now.strftime("%M")))

#overarching window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #first, display place to input module name
        space = 7
        left_align = int(w_width/3)
        labelll = QLabel("<b>Multi-module Encapsulation:</b>", self)
        labelll.setGeometry(left_align, int(w_height/10), 350, 25)

        self.load_button4 = GreyButton("Encapsulation", 75, 25, self)
        self.load_button4.setGeometry(left_align, space + labelll.geometry().top() + labelll.geometry().height(), 75, 25)
        self.load_button4.clicked.connect(lambda: self.load("encapspage"))

        labelline = QLabel("<b>-------------------------------------------------------</b>", self)
        labelline.setGeometry(left_align, 10 + self.load_button4.geometry().top() + self.load_button4.geometry().height(), 500, 25)
        
        labell = QLabel("<b>Wirebonding:</b>", self)
        labell.setGeometry(left_align, 3 + space + labelline.geometry().top() + labelline.geometry().height() , 150, 25)
        
        self.label = QLabel(self) #"Module type:",self)
        self.label.setGeometry(w_width-90-20-225, 0, 225+600, 25)
        self.label.hide()
        # self.label.setGeometry(left_align, 350, 150, 25)
        # commented out to move from dropdown to just a textbox entry system
        #self.combobox = QComboBox(self)
        #inst_code = conn.inst_code
        #mod_list = mod_type_mac.module_type[inst_code]
        #self.combobox.addItems(mod_list)
        #self.combobox.setGeometry(int(w_width/2-80), 375, 150, 25)
        self.label2 = QLabel("Module ID:",self)
        self.label2.setGeometry(left_align, space + labell.geometry().top() + labell.geometry().height(), 150, 25)
        self.modid = QLineEdit(self)
        self.modid.setGeometry(left_align, space + self.label2.geometry().top() + self.label2.geometry().height(), 150, 25)

        self.labelhxb = QLabel("Hexaboard ID:",self)
        self.labelhxb.setGeometry(self.label2.geometry().left() + self.label2.geometry().width() + 10, self.label2.geometry().top(), 150, 25)
        self.labelhxb.hide()
        self.hxbid = QLineEdit(self)
        self.hxbid.setGeometry(self.modid.geometry().left() + self.modid.geometry().width() + 10, self.modid.geometry().top() , 150, 25)
        self.hxbid.hide()

        self.load_button = GreyButton("Load front", 75, 25, self)
        self.load_button.setGeometry(left_align, space + self.modid.geometry().top() + self.modid.geometry().height(), 75, 25)
        self.load_button.clicked.connect(lambda: self.load("frontpage"))
        
        self.load_button2 = GreyButton("Load back", 75, 25, self)
        self.load_button2.setGeometry(30 + self.load_button.geometry().left() + self.load_button.geometry().width(), self.load_button.geometry().top(), 75, 25)
        self.load_button2.clicked.connect(lambda: self.load("backpage"))

        self.df_pad_map = pd.DataFrame()
        self.df_backside_mbites_pos = pd.DataFrame()
        self.df_pad_to_channel = pd.DataFrame()

        self.logolabel = QLabel(self)
        logo = QPixmap('images/CMU_Logo_Stack_Red.png').scaled(75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logolabel.setPixmap(logo)
        self.logolabel.setGeometry(10, 30, 90, 75)
        self.namelabel = QLabel("<a href=\"https://github.com/cmu-hgc-mac/wirebonder_gui\">Created by <br>Nedjma Kalliney</a>",self)
        self.namelabel.setOpenExternalLinks(True)
        self.namelabel.setGeometry(10, 90, 130, 50)
        self.widget = QStackedWidget(self)
        self.widget.setGeometry(0, 25, w_width, w_height)
        self.label3 = QLabel(self)
        self.modname = ''
        self.modno = 0

        self.label5 = QLabel("",self)
        self.label5.setGeometry(left_align, space + self.load_button.geometry().top() + self.load_button.geometry().height(), 350, 50)
        self.addbutton = GreyButton("Add module and/or hexaboard",230,25,self)
        self.addbutton.hide()
        self.addbutton.setGeometry(left_align, space + self.label5.geometry().top() + self.label5.geometry().height(), 300, 70)
        self.addbutton.clicked.connect(self.add_new_to_db_helper)
        self.scrolllabel = ScrollLabel(self)
        self.scrolllabel.setGeometry(left_align, space + self.addbutton.geometry().top() + self.addbutton.geometry().height(), 300, 300)
        self.scrolllabel.setText("Waiting for modules...")

        self.homebutton = HomePageButton("Home page", 75, 25, self)
        self.homebutton.setGeometry(0, 0, self.homebutton.width, self.homebutton.height)
        self.save_button = SaveButton(self.widget, "", "", 90, 25, "Save", self)
        self.save_button.setGeometry(self.homebutton.width+10, 0, self.save_button.width, self.save_button.height)
        self.homebutton.hide()
        self.save_button.hide()
        self.init_and_show()
        self.opened_once = False
        self.bad_modules = None
        self.rotate_by_angle = math.radians(0) #*0

        global x_offset, y_offset
        y_offset += 40
        x_offset+=add_x_offset

    @asyncSlot()
    async def init_and_show(self):
        await init_pool()
        self.show_start()
            
    def closeEvent(self,  event: QCloseEvent):
        print("Window closing...")
        event.ignore() 
        asyncio.ensure_future(self.cleanup_and_close(event))

    async def cleanup_and_close(self, event):
        if self.opened_once == True:
            saved = await self.save(self.widget, home_seq=True)
            if saved:
                self.label.setText("Closing db conn, wait & try again.")
                while self.bad_modules is not None: ### Gracious handling of connection pool
                    await close_pool(); break
        else:
            self.label5.setText("Closing db conn; wait & try again.")
            self.label5.show()
            while self.bad_modules is not None: ### Gracious handling of connection pool
                await close_pool(); break
        if pool is None:
            print(f"Async cleanup finished, now closing the window.")
            try:
                event.accept(); 
            except:
                pass
            sys.exit()
    
    #showing home page
    @asyncSlot()
    async def show_start(self):
        print("Currently on MainWindow")
        self.modno = 0
        self.scrolllabel.setText("Waiting for modules...")
        self.bad_modules = None
        self.opened_once = False
        self.widget.hide()
        self.modid.setText('')
        self.modid.show()
        self.hxbid.setText('')
        #self.combobox.show()
        self.label2.show()
        self.label3.setText("Wirebonding and Encapsulation")
        self.label3.setGeometry(int(w_width/3), 0, 400, 25)
        self.load_button.show()
        self.scrolllabel.show()
        self.logolabel.show()
        self.namelabel.show()
        self.label.hide()
        self.label5.hide()
        self.hxbid.hide()
        self.labelhxb.hide()
        self.addbutton.hide()
        self.homebutton.hide()
        self.save_button.hide()
        string = 'Incomplete or unstarted modules:\n'
        self.bad_modules = await find_to_revisit(pool)
        for module in self.bad_modules:
            mod_str = module + ' '
            if not self.bad_modules[module][0]: #true = frontside done
                mod_str = mod_str + "fr "
            if not self.bad_modules[module][1]: # true = backside done
                mod_str = mod_str + " bk"
            string = string + (mod_str+ "\n")
        self.scrolllabel.setText(string)
        
    async def check_mod_exists_main(self, page):
        if page == "encapspage":
            asyncio.create_task(self.begin_program(page))
        else:
            combined_query = f""" SELECT 
            (SELECT module_no FROM module_info WHERE REPLACE(module_name, '-','') = '{self.modname}' LIMIT 1) AS in_info,
            (SELECT module_no FROM front_wirebond WHERE REPLACE(module_name, '-','') = '{self.modname}' LIMIT 1) AS in_fr_wirebond,
            (SELECT module_no FROM back_wirebond WHERE REPLACE(module_name, '-','') = '{self.modname}' LIMIT 1) AS in_bk_wirebond; """
            combined_check = await async_check(pool, combined_query)
            if combined_check['in_info'] is not None: #or combined_check['in_fr_wirebond'] or combined_check['in_bk_wirebond']:
                self.modno = combined_check['in_info']
                print(f"Loading {self.modname} with module_no {self.modno}...")
                asyncio.create_task(self.begin_program(page))
            else:
                self.label5.setText("Information not found,\nPlease enter valid module ID or")
                self.label5.show()
                self.hxbid.show()
                self.labelhxb.show()
                self.addbutton.show()

    def load(self, page):
        #check if the module exists
        self.modname = (self.modid.text()).replace("-","")
        try:
            asyncio.create_task(self.check_mod_exists_main(page=page))
        except Exception as e:
            print(e)

    #create pages, button to switch between pages, button to save
    async def begin_program(self,page):
        self.label5.hide()
        self.addbutton.hide()
        self.opened_once = True
        self.hxbid.hide()
        self.labelhxb.hide()

        if page != "encapspage":
            hexaboard_type = (self.modname).replace("-","")[4] + (self.modname).replace("-","")[5]
            global hex_length, num_non_signal
            if self.modname.replace("-","")[4] == "L":
                hex_length = 38
            elif self.modname.replace("-","")[4] == "H":
                hex_length = 25
            self.rotate_by_angle_fr = math.radians(hxb_orientation[hexaboard_type]['rot_ang_fr'])
            self.rotate_by_angle_bk = math.radians(hxb_orientation[hexaboard_type]['rot_ang_bk'])
            #load position files
            if self.modname.replace("-","")[5] == "5":
                num_non_signal = 10
            elif self.modname.replace("-","")[5] == "L" or self.modname.replace("-","")[5] == "R":
                num_non_signal = 8
            fname = f'./geometries/{hexaboard_type}_hex_positions.csv'
            with open(fname, 'r') as file:
                #read in all the pad positions
                self.df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['padnumber', 'xposition', 'yposition', 'type', 'optional'])
                self.df_pad_map = self.df_pad_map[["padnumber","xposition","yposition"]]

            if page == "frontpage":
                for p in self.df_pad_map['xposition'].keys():
                    self.df_pad_map.loc[p,'xposition'], self.df_pad_map.loc[p,'yposition'] = rotate_point(self.df_pad_map.loc[p,'xposition'], self.df_pad_map.loc[p,'yposition'], angle_deg = self.rotate_by_angle_fr)
            elif page == "backpage":
                for p in self.df_pad_map['xposition'].keys():
                    self.df_pad_map.loc[p,'xposition'], self.df_pad_map.loc[p,'yposition'] = rotate_point(self.df_pad_map.loc[p,'xposition'], self.df_pad_map.loc[p,'yposition'], angle_deg = -self.rotate_by_angle_bk)

            fname = f'./geometries/{hexaboard_type}_backside_mbites_pos.csv'
            with open(fname, 'r') as file:
                self.df_backside_mbites_pos = pd.read_csv(file, skiprows = 1, names = ['padnumber','xposition','yposition'])
            if page == "backpage":
                for p in self.df_backside_mbites_pos['xposition'].keys():
                    self.df_backside_mbites_pos.loc[p,'xposition'], self.df_backside_mbites_pos.loc[p,'yposition'] = rotate_point(self.df_backside_mbites_pos.loc[p,'xposition'], self.df_backside_mbites_pos.loc[p,'yposition'], angle_deg = -self.rotate_by_angle_bk)

            #load pad to channel mappings
            fname = f'./geometries/{hexaboard_type}_pad_to_channel_mapping.csv'
            with open(fname, 'r') as file:
                #read in all the channels and what pad they're connected to (not used but possibly useful in the future)
                self.df_pad_to_channel = pd.read_csv(file, skiprows = 1, names = ['padnumber', 'ASIC','Channel','Channeltype','Channelpos'])
                self.df_pad_to_channel = self.df_pad_to_channel.set_index("padnumber")

        self.modid.hide()
        #self.combobox.hide()
        self.label2.hide()
        self.scrolllabel.hide()
        self.label.hide()
        self.load_button.hide()
        self.logolabel.hide()
        self.namelabel.hide()

        if page == "encapspage":
            self.encapspage = EncapsPage(self)
            self.widget.addWidget(self.encapspage)
            self.widget.setCurrentWidget(self.encapspage)
            self.label3.setText("Encapsulation")
            self.label3.setGeometry(self.save_button.geometry().left()+ self.save_button.width+20, 0, 160, 25)
            self.label3.show()
        else:
            info_dict = await read_from_db(pool, self.modname, self.df_pad_map, self.df_backside_mbites_pos)
            if page == "frontpage":
                frontpage = FrontPage(self.modname, self.df_pad_map, self.df_backside_mbites_pos, self.df_pad_to_channel, info_dict, rotate_by_angle = self.rotate_by_angle_fr)
                self.widget.addWidget(frontpage)
                self.widget.setCurrentWidget(frontpage)
            elif page == "backpage":
                load_pin_padnum = hxb_orientation[hexaboard_type]['load_pin']
                backpage = BackPage(self.modname,self.df_pad_map, self.df_backside_mbites_pos, self.df_pad_to_channel, info_dict, rotate_by_angle = -self.rotate_by_angle_bk, load_pin_padnum = load_pin_padnum)
                self.widget.addWidget(backpage)
                self.widget.setCurrentWidget(backpage)
            self.label3.setText(self.modname)
            self.label3.setGeometry(self.save_button.geometry().left()+ self.save_button.width+20, 0, 160, 25)
            self.label3.show()

        self.widget.show()
        self.label.setText("Last Saved: Unsaved since opened")
        self.label.setGeometry(self.label3.geometry().left() + self.label3.width() +100, 0, 225+1200, 25)
        self.label.show()

        self.homebutton = HomePageButton("Home page", 75, 25, self)
        self.homebutton.clicked.connect(lambda: self.home_button_helper(self.widget, self.save_button))
        self.homebutton.show()

        self.save_button = SaveButton(self.widget, self.modname, self.label, 90, 25, "Save", self)
        self.save_button.clicked.connect(lambda: self.save_button_helper(self.widget, self.save_button))
        self.save_button.setGeometry(self.homebutton.width+10, 0, self.save_button.width, self.save_button.height)
        self.save_button.show()

    @asyncSlot()
    async def home_button_helper(self, widget, save_button):
        saved = await self.save(widget, home_seq=True)
        if saved: 
            await self.show_start()
        # asyncio.create_task(self.save(widget))
        # await self.show_start()
    
    @asyncSlot()
    async def save_button_helper(self, widget, save_button, home_seq = None):
        saved = await self.save(widget, home_seq=home_seq)
        if saved: 
            save_button.updateAboveLabel()

    async def save(self, widget, home_seq = None):
        saved = True
        page = widget.currentWidget()
        print('Currently on page', page.pageid)
        if page.pageid == "frontpage":
            saved, page.fwb_lastsave = await upload_front_wirebond(pool, self.modname, self.modno, page.techname.text(), page.comments.toPlainText(), page.wedgeid.text(), page.spool.text(), page.marked_done.isChecked(),  page.wb_time.text(), page.buttons, lastsave_fwb = page.fwb_lastsave, home_seq=home_seq)
            savedp, page.fpi_lastsave = await upload_bond_pull_test(pool, self.modname, self.modno, page.mean.text(), page.std.text(), page.pull_techname.text(), page.pull_comments.toPlainText(), page.pull_time.text(), lastsave_fpi = page.fpi_lastsave, home_seq=home_seq)
            saved = saved and savedp
        elif page.pageid == "backpage":
            saved, page.bwb_lastsave = await upload_back_wirebond(pool, self.modname, self.modno, page.techname.text(), page.comments.toPlainText(), page.wedgeid.text(), page.spool.text(), page.marked_done.isChecked(),page.wb_time.text(), page.buttons, lastsave_bwb = page.bwb_lastsave, home_seq=home_seq)
        elif page.pageid == "encapspage":
            enc_full = f"{page.enc_date.text()} {page.enc_time.text()}:00"
            cure_start_full = f"{page.start_date.text()} {page.start_time.text()}:00"
            cure_end_full = f"{page.end_date.text()} {page.end_time.text()}:00"
            if len(page.modules) != 0:
                if home_seq: 
                    self.encapspage.timestatlabel.setText("To exit, <b>clear all modules</b>.")
                    self.encapspage.timestatlabel.setStyleSheet("color: blue;")
                    return False
                saved = await upload_encaps(pool, page.modules, page.modnos, page.techname.text(), enc_full, cure_start_full, cure_end_full, page.temperature.text(), page.rel_hum.text(), page.epoxy_batch.text(), page.comments.toPlainText())
                if not saved:
                    self.encapspage.timestatlabel.setText("To save, provide  <b>encap+start</b>  time (and/or)  <b>end</b>  time.") #<br>To exit, <b>remove modules</b>.")
                    self.encapspage.timestatlabel.setStyleSheet("color: blue;")
                else:
                    self.encapspage.timestatlabel.setText("")
            else: 
                return True
        if not saved:
            self.save_button.updateAboveLabel(message = 'Either save or reset current changes to exit.')
        return saved

    @asyncSlot()
    async def add_new_to_db_helper(self):
        if check_valid_module(modname = self.modid.text()):
            return_state = await add_new_to_db(pool, self.modid.text().upper(), self.hxbid.text().upper())
            if return_state:
                self.label5.setText(f"{self.modid.text()}\nnow in module_info table.")
            else:
                self.label5.setText("See terminal for message.")
        else:
            self.label5.setText("Not a valid module ID.\nSee postgres_tools/check_valid_module().")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        painter.drawLine(QPoint(0,25),QPoint(w_width,25))

def main():
    app = QApplication(sys.argv)
    global scroll_width, scroll_height, w_width, w_height, add_x_offset, add_y_offset, text_font_size, y_offset, x_offset
    if autosize:
        print("Autosizing window...")
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        # if w_width > screen.width():
        #     add_y_offset = w_width - screen.width()
        # if w_height > int(screen.height()):
        #     add_x_offset = w_height - screen.height()
        # w_width = screen.width()
        # w_height = screen.height()
        del screen, QDesktopWidget
    
    y_offset = 0*add_y_offset
    x_offset = 0
    font = QFont("Calibri", text_font_size)
    font.setWeight(text_font_size)
    QApplication.setFont(font, "QLabel")
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_pool())
    mainWindow = MainWindow()
    mainWindow.setGeometry(0, 0, w_width, w_height)
    mainWindow.show()
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()
