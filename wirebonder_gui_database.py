import sys, csv
import numpy as np
import pandas as pd
from datetime import datetime
import os.path
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QLabel, QTextEdit, QLineEdit, QCheckBox
from PyQt5.QtCore import Qt, QRectF, QRect, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QRegion, QPainterPath, QPolygonF, QPixmap, QFont
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QComboBox
import asyncio

from postgres_tools import fetch_PostgreSQL, read_from_db, upload_front_wirebond, upload_back_wirebond, upload_bond_pull_test, find_to_revisit, upload_encaps
from wirebonder_gui_buttons import Hex, HexWithButtons, WedgeButton, GreyButton, SetToNominal, ResetButton, InfoButton, SwitchPageButton, SaveButton, ResetButton2, HalfHexWithButtons, HalfHex, GreyCircle, HomePageButton, ScrollLabel
import geometries.module_type_at_mac as mod_type_mac
import conn
from graphics_config import scroll_width, scroll_height, w_width, w_height, add_x_offset, add_y_offset, button_font_size, text_font_size

#test comment
scaling_factor = 90
hex_length = 0
y_offset = add_y_offset
x_offset = 0
num_non_signal = 12

#hexaboard/"requirements" page
class FrontPage(QMainWindow):
    def __init__(self, modname, df_pad_map, df_backside_mbites_pos, df_pad_to_channel, info_dict):
        super().__init__()

        self.pageid = "frontpage"
        self.setGeometry(0, 0, w_width, w_height)

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

        self.df_front_states = self.info_dict["df_front_states"]
        self.df_back_states = self.info_dict["df_back_states"]
        #set state counter
        self.state_counter = {0: len(self.df_front_states[self.df_front_states['state'] == 0]), 1: len(self.df_front_states[self.df_front_states['state'] == 1]),
            2: len(self.df_front_states[self.df_front_states['state'] == 2]), 3: len(self.df_front_states[self.df_front_states['state'] == 3])}
        self.state_counter_labels = {}
        self.state_button_labels = {}

        #make label of state counter
        for state in self.state_counter:
            lab = QLabel(f"{state} missing bonds: {self.state_counter[state]}", self.widget)
            lab.setFont(QFont('Arial', 14))
            lab.setGeometry(20,10 + state * 20,200, 20)
            self.state_counter_labels[state] = lab

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, self.modname, "Set to nominal", self.buttons, 90, 25, self.widget)
        nominal_button.setGeometry(scroll_width-10-nominal_button.width,75, nominal_button.width, nominal_button.height)
        nominal_button.show()
        info_label = QLabel("<a href=\"https://github.com/nkalliney1/wirebonder_gui/blob/main/README.md\">Help",self.widget)
        info_label.setOpenExternalLinks(True)
        info_label.setGeometry(scroll_width-40, 110, 100, 25)

        lab6 = QLabel("Technician CERN ID:", self.widget)
        lab6.setGeometry(20,100, 150, 25)
        self.techname = QLineEdit(self.widget)
        self.techname.setGeometry(20,125, 150, 25)
        self.techname.setText(self.info_dict["front_wirebond_info"]["technician"])
        lab4 = QLabel("Comments:", self.widget)
        lab4.setGeometry(20,285,150,50)
        self.comments = QTextEdit(self.widget)
        self.comments.setGeometry(20, 330, 150, 150)
        self.comments.setText(self.info_dict["front_wirebond_info"]["comment"])
        lab4 = QLabel("Wedge ID:", self.widget)
        lab4.setGeometry(20,140,150,50)
        self.wedgeid = QLineEdit(self.widget)
        self.wedgeid.setGeometry(20, 180, 150, 25)
        self.wedgeid.setText(self.info_dict["front_wirebond_info"]["wedge_id"])
        lab4 = QLabel("Spool batch:", self.widget)
        lab4.setGeometry(20,200,150,50)
        self.spool = QLineEdit(self.widget)
        self.spool.setGeometry(20, 240, 150, 25)
        self.spool.setText(self.info_dict["front_wirebond_info"]["spool_batch"])
        label5 = QLabel("<b>Legend:</b><br>Blue: nominal <br>Yellow: 1 failed bond<br>Orange: 2 failed bonds<br>Red: 3 failed bonds<br><b>Black outline</b>: Needs to be grounded<br>Black fill: Grounded",self.widget)
        label5.setWordWrap(True)
        label5.setTextFormat(Qt.RichText)
        label5.setGeometry(20,490, 170,150)
        self.marked_done = QCheckBox("Mark as done", self.widget)
        self.marked_done.setGeometry(20,275,150,25)
        if self.info_dict["front_wirebond_info"]["wb_fr_marked_done"]:
            self.marked_done.setCheckState(Qt.Checked)

        reset_button = ResetButton(self.modname, "front", self.df_pad_map, self.techname, self.comments , "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50, self.widget)
        reset_button.setGeometry(scroll_width-10-reset_button.width,10, reset_button.width, reset_button.height)
        reset_button.show()

        pads = []
        #make all the cells
        for index,row0 in self.df_pad_map.iterrows():
            padnumber = int(df_pad_map.loc[index]['padnumber'])
            #row of the dataframe that converts between pad and the channel number of the channel on that pad
            row1 = self.df_pad_to_channel.loc[padnumber]
            #row of the dataframe that gives the pad ID, channel state, and whether or not it's grounded
            row2 = self.df_front_states.loc[padnumber]
            if row1['Channeltype'] == 0 and index > -1:
                pad_after = False
                pad_before = False
                #tests for calibration channel before or after current cell
                if (index < (len(self.df_pad_map) - num_non_signal-1)):
                    padnumafter = df_pad_map.loc[index+1]['padnumber']
                    pad_after = (self.df_pad_map.loc[index+1]['xposition'] == row0["xposition"] and self.df_pad_map.loc[index+1]['yposition'] == row0["yposition"]
                        and self.df_pad_to_channel.loc[padnumafter]['Channeltype'] == 1)
                if index > 0:
                    padnumbefore = df_pad_map.loc[index-1]['padnumber']
                    pad_before = (self.df_pad_map.loc[index-1]['xposition'] == row0["xposition"] and self.df_pad_map.loc[index-1]['yposition'] == row0["yposition"]
                        and self.df_pad_to_channel.loc[padnumbefore]['Channeltype'] == 1)
                #create cells
                if pad_after or pad_before:
                    if row1['Channelpos'] == 0 or row1['Channelpos'] == 1 or row1['Channelpos'] == 5:
                        #move label position if button would cover it based on channelpos
                        pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'], hex_length,
                            str(padnumber), [0,18], str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                    else:
                        pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'],row2['grounded'], hex_length,
                            str(padnumber), [0,-18], str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                    pad.lower()
                else: #if there is no calibration channel, the label can be in the middle of the pad
                    pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels,row2['state'],row2['grounded'], hex_length, str(padnumber), [0,0],
                        str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                #wedge buttons associated with cells are automatically added to button dictionary
                #set pad position
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 +x_offset ),int(float(row0["yposition"]*-1*scaling_factor + y_offset+ w_height/2)), int(pad.radius*2), int(pad.radius*2))
            #create half hexagon cells
            elif row1['Channeltype'] == 2 and index > -1:
                pad = HalfHexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels,row2['state'],row2['grounded'], hex_length, str(padnumber), [hex_length/2,0],
                    str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8',row1['Channeltype'],  self.widget)
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 +x_offset),int(float(row0["yposition"]*-1*scaling_factor + y_offset+ w_height/2)), int(pad.radius), int(pad.radius*2))
            elif row1['Channeltype'] == 3 and index > -1:
                pad = HalfHexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels,row2['state'],row2['grounded'], hex_length, str(padnumber), [-hex_length/2,0],
                    str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8',row1['Channeltype'],  self.widget)
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 +pad.radius + x_offset),int(float(row0["yposition"]*-1*scaling_factor + y_offset+ w_height/2)), int(pad.radius), int(pad.radius*2))
            #create calibration channels
            elif self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 1 and padnumber > 0:
                pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'],
                    str(row1['Channel']), 6, str(padnumber), [0,0], hex_length/3, self.widget)
                pad.setGeometry(int(float(row0["xposition"]*scaling_factor) + scroll_width/2 + hex_length*2/3 +x_offset),int(float(row0["yposition"]*-1*scaling_factor + y_offset+w_height/2+hex_length*2/3)), int(pad.radius*2), int(pad.radius*2))
                #add manually to list of buttons
                self.buttons[str(padnumber)] = pad
                pad.raise_()
            #create mousebites and guardrails
            else:
                #want these to be circular so pass channel_pos = 6
                if padnumber < -12:
                    #guardrail button size
                    size = hex_length/3
                else:
                    #mousebite size
                    size = 13
                pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'],
                    str(padnumber), 6, str(padnumber), [0,0], size, self.widget)
                pad.setGeometry(int(float(row0["xposition"])*scaling_factor + scroll_width/2 + scaling_factor*0.25 + x_offset),int(float(row0["yposition"]*-1*scaling_factor + y_offset + w_height/2 + scaling_factor*0.25)),
                    int(pad.radius*2), int(pad.radius*2))
                #manually add to list of buttons
                self.buttons[str(padnumber)] = pad
            #add to list of pads
            pads.append(pad)

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
    def __init__(self, modname, df_pad_map, df_backside_mbites_pos, df_pad_to_channel, info_dict):
        super().__init__()
        self.pageid = "backpage"
        self.setGeometry(0, 0, w_height, w_height)

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

        self.df_front_states = self.info_dict["df_front_states"]
        self.df_back_states = self.info_dict["df_back_states"]
        #set state counter
        self.state_counter = {0: len(self.df_back_states[self.df_back_states['state'] == 0]), 1: len(self.df_back_states[self.df_back_states['state'] == 1]),
            2: len(self.df_back_states[self.df_back_states['state'] == 2]), 3: len(self.df_back_states[self.df_back_states['state'] == 3])}
        self.state_counter_labels = {}
        self.state_button_labels = {}

        #make label of state counter
        for state in self.state_counter:
            lab = QLabel(f"{state} missing bonds: {self.state_counter[state]}", self.widget)
            lab.setFont(QFont('Arial', 14))
            lab.setGeometry(20,10 + state * 20,200, 20)
            self.state_counter_labels[state] = lab

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, self.modname, "Set to nominal", self.buttons, 90, 25, self.widget)
        nominal_button.setGeometry(scroll_width-10-nominal_button.width,75, nominal_button.width, nominal_button.height)
        nominal_button.show()
        info_label = QLabel("<a href=\"https://github.com/nkalliney1/wirebonder_gui/blob/main/README.md\">Help",self.widget)
        info_label.setOpenExternalLinks(True)
        info_label.setGeometry(scroll_width-40, 110, 100, 25)

        lab6 = QLabel("Technician CERN ID:", self.widget)
        lab6.setGeometry(20,100, 150, 25)
        self.techname = QLineEdit(self.widget)
        self.techname.setGeometry(20,125, 150, 25)
        self.techname.setText(self.info_dict["back_wirebond_info"]["technician"])
        lab4 = QLabel("Comments:", self.widget)
        lab4.setGeometry(20,285,150,50)
        self.comments = QTextEdit(self.widget)
        self.comments.setGeometry(20, 330, 150, 150)
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
        self.marked_done = QCheckBox("Mark as done", self.widget)
        self.marked_done.setGeometry(20,275,150,25)
        if self.info_dict["back_wirebond_info"]["wb_bk_marked_done"]:
            self.marked_done.setCheckState(Qt.Checked)

        reset_button = ResetButton(self.modname, "back", self.df_backside_mbites_pos, self.techname, self.comments , "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50, self.widget)
        reset_button.setGeometry(w_width-10-reset_button.width,10, reset_button.width, reset_button.height)
        reset_button.show()

        pads = []

        #make all the cells
        for index,row0 in self.df_pad_map.iterrows():
            padnumber = int(row0['padnumber'])
            #normal cells without buttons
            if self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 0 and index > -1:
                pad = Hex(hex_length, str(padnumber), [0,0],'#d1d1d1', self.widget)
                pad.setGeometry(int(float(row0["xposition"]*-1*scaling_factor) + scroll_width/2 +x_offset),int(float(row0["yposition"]*-1*scaling_factor + w_height/2 + y_offset)), int(pad.radius*2), int(pad.radius*2))
            #half hexagons
            elif self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 2 or self.df_pad_to_channel.loc[padnumber]['Channeltype'] == 3 and index > -1:
                pad = HalfHex(hex_length, str(padnumber), [0,0],'#d1d1d1', self.df_pad_to_channel.loc[row0['padnumber']]['Channeltype'], self.widget)
                pad.setGeometry(int(float(row0["xposition"]*-1*scaling_factor) + scroll_width/2 +x_offset),int(float(row0["yposition"]*-1*scaling_factor + w_height/2 + y_offset)), int(pad.radius*2), int(pad.radius*2))
            pads.append(pad)

        for index,row in self.df_backside_mbites_pos.iterrows():
            padnumber = int(row['padnumber'])
            #want these to be circular so pass channel_pos = 6
            pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, self.df_back_states.loc[padnumber]['state'], self.df_back_states.loc[padnumber]['grounded'],
                str(padnumber), 6, str(padnumber), [0,0], 13, self.widget)
            pad.setGeometry(int(float(row["xposition"])*-1*scaling_factor + scroll_width/2+ scaling_factor*0.25 + x_offset),int(float(row["yposition"]*-1*scaling_factor + w_height/2+ y_offset + scaling_factor*0.3)), int(pad.radius*2), int(pad.radius*2))
            self.buttons[str(padnumber)] = pad

        pad2 = GreyCircle(13, 0, 0, self.widget)
        pad2.setGeometry(int(scroll_width/2 +pad.radius*2 + x_offset),int(w_height/2+y_offset), int(pad.radius*2), int(pad.radius*2))
        diff = 4*((w_height/2+y_offset) - (df_pad_map.loc[0]["yposition"]*-1*scaling_factor + w_height/2 + y_offset) )/5
        pad3 = GreyCircle(13, 0, 0, self.widget)
        pad3.setGeometry(int(scroll_width/2 +pad.radius*2+x_offset),int(w_height/2+y_offset - diff), int(pad.radius*2), int(pad.radius*2))


#"results" page
class PullPage(QMainWindow):
    def __init__(self,modname,info_dict):
        super().__init__()
        self.pageid = "pullpage"
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
        self.modname = modname
        self.info_dict = info_dict

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        lab2 = QLabel("Technician CERN ID:", self)
        lab2.setGeometry(20,20, 150, 25)
        self.techname = QLineEdit(self)
        self.techname.setGeometry(20,45, 150, 25)
        lab3 = QLabel("Results from Pull Testing (optional):", self)
        lab3.setGeometry(20,90, 250, 25)
        lab4 = QLabel("Mean:", self)
        lab4.setGeometry(20,115, 150, 25)
        self.mean = QLineEdit(self)
        self.mean.setGeometry(20,140, 150, 25)
        lab5 = QLabel("Standard deviation:", self)
        lab5.setGeometry(20,165, 150, 25)
        self.std= QLineEdit(self)
        self.std.setGeometry(20,190, 150, 25)
        lab6 = QLabel("Comments:", self)
        lab6.setGeometry(20,215, 150, 25)
        self.comments= QTextEdit(self)
        self.comments.setGeometry(20,245, 300, 150)

        #load pull test data
        self.techname.setText(str(self.info_dict["pull_info"]["technician"]))
        self.mean.setText(str(self.info_dict["pull_info"]["avg_pull_strg_g"]))
        self.std.setText(str(self.info_dict["pull_info"]["std_pull_strg_g"]))
        self.comments.setText(str(self.info_dict["pull_info"]["comment"]))

        reset_button = ResetButton2(self.modname, self.techname, self.comments, self.mean, self.std, "Reset to last\nsaved version\n(irreversible)", 90, 50, self)
        reset_button.setGeometry(20,415, reset_button.width, reset_button.height)
        reset_button.show()

class EncapsPage(QMainWindow):
    def __init__(self, parent = None):
        super().__init__(parent)
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

        lab2 = QLabel("Technician CERN ID:", self)
        lab2.setGeometry(300,20, 150, 25)
        self.techname = QLineEdit(self)
        self.techname.setGeometry(300,45, 150, 25)
        lab6 = QLabel("Comments:", self)
        lab6.setGeometry(300,70, 150, 25)
        self.comments= QTextEdit(self)
        self.comments.setGeometry(300,100, 300, 150)

        self.label = QLabel("Module type:",self)
        self.label.setGeometry(20, 20, 150, 25)
        self.label.show()
        self.combobox = QComboBox(self)
        inst_code = conn.inst_code
        mod_list = mod_type_mac.module_type[inst_code]
        self.combobox.addItems(mod_list)
        self.combobox.setGeometry(15, 45, 150, 25)
        self.label = QLabel()
        self.label2 = QLabel("Module no:",self)
        self.label2.setGeometry(20, 70, 150, 25)
        self.modid = QLineEdit(self)
        self.modid.setGeometry(20, 100, 150, 25)
        self.scrolllabel = ScrollLabel(self)
        self.scrolllabel.setGeometry(20, 230, 250, 100)
        self.problemlabel = QLabel("This module isn't available.", self)
        self.problemlabel.setGeometry(20,340, 200, 25)
        self.problemlabel.hide()

        addbutton = GreyButton("Add", 75, 25, self)
        addbutton.setGeometry(20, 180, 75, 25)
        addbutton.clicked.connect(self.add)
        removebutton = GreyButton("Remove", 75, 25, self)
        removebutton.setGeometry(125, 180, 75, 25)
        removebutton.clicked.connect(self.remove)
        self.combobox2 = QComboBox(self)
        self.combobox2.addItems(["frontside", "backside"])
        self.combobox2.setGeometry(15, 140, 150, 25)

        self.modules = {}

    def add(self):
        self.problemlabel.hide()
        modname = self.combobox.currentText()+"-"+self.modid.text()
        read_query = f"""SELECT EXISTS(SELECT module_name
        FROM module_info
        WHERE module_name ='{modname}');"""
        check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        if check['exists']:
            self.modules[modname] = self.combobox2.currentText()
            string = ""
            for module in self.modules:
                string= string + module + ' ' + self.modules[module]  + "\n"
            self.scrolllabel.setText(string)
        else:
            self.problemlabel.show()

    def remove(self):
        modname = self.combobox.currentText()+"-"+self.modid.text()
        if modname in self.modules and self.modules[modname] == self.combobox2.currentText():
            del self.modules[modname]
        string = ""
        for module in self.modules:
            string = string + module +' ' + self.modules[module] + "\n"
        self.scrolllabel.setText(string)

#overarching window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #first, display place to input module name
        labelll = QLabel("<b>Encapsulation:</b>", self)
        labelll.setGeometry(int(w_width/2-75), 250, 150, 25)
        labell = QLabel("<b>Wirebonder:</b>", self)
        labell.setGeometry(int(w_width/2-75), 330, 150, 25)
        self.label = QLabel("Module type:",self)
        self.label.setGeometry(int(w_width/2-75), 350, 150, 25)
        self.combobox = QComboBox(self)
        inst_code = conn.inst_code
        mod_list = mod_type_mac.module_type[inst_code]
        self.combobox.addItems(mod_list)
        self.combobox.setGeometry(int(w_width/2-80), 375, 150, 25)
        self.label2 = QLabel("Module no:",self)
        self.label2.setGeometry(int(w_width/2-75), 400, 150, 25)
        self.modid = QLineEdit(self)
        self.modid.setGeometry(int(w_width/2-75), 425, 150, 25)

        self.load_button = GreyButton("Load front", 75, 25, self)
        self.load_button.setGeometry(int(w_width/2-75), 470, 75, 25)
        #when button clicked, try to load module information
        self.load_button.clicked.connect(lambda: self.load("frontpage"))
        self.load_button2 = GreyButton("Load back", 75, 25, self)
        self.load_button2.setGeometry(int(w_width/2+20), 470, 75, 25)
        self.load_button2.clicked.connect(lambda: self.load("backpage"))
        self.load_button3 = GreyButton("Load pull info", 75, 25, self)
        self.load_button3.setGeometry(int(w_width/2+20+75+20), 470, 75, 25)
        self.load_button3.clicked.connect(lambda: self.load("pullpage"))
        self.load_button4 = GreyButton("Encapsulation", 75, 25, self)
        self.load_button4.setGeometry(int(w_width/2-75), 280, 75, 25)
        self.load_button4.clicked.connect(lambda: self.load("encapspage"))

        self.df_pad_map = pd.DataFrame()
        self.df_backside_mbites_pos = pd.DataFrame()
        self.df_pad_to_channel = pd.DataFrame()
        self.logolabel = QLabel(self)
        logo = QPixmap('images/CMU_Logo_Stack_Red.png').scaled(75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logolabel.setPixmap(logo)
        self.logolabel.setGeometry(w_width-110, 30, 90, 75)
        self.namelabel = QLabel("<a href=\"https://github.com/nkalliney1/wirebonder_gui\">Created by <br>Nedjma Kalliney</a>",self)
        self.namelabel.setOpenExternalLinks(True)
        self.namelabel.setGeometry(w_width-110, 90, 110, 50)
        self.widget = QStackedWidget(self)
        self.widget.setGeometry(0, 25, w_width, w_height)
        self.label3 = QLabel(self)
        self.modname = ''
        self.scrolllabel = ScrollLabel(self)
        self.scrolllabel.setGeometry(int(w_width/2-75), 540, 300, 100)
        self.label5 = QLabel("Information not found,\nPlease enter valid module serial number",self)
        self.label5.setGeometry(int(w_width/2-75), 490, 300, 50)
        self.show_start()

    #showing home page
    def show_start(self):
        self.widget.hide()
        self.modid.setText('')
        self.modid.show()
        self.combobox.show()
        self.label2.show()
        self.label3.setText("Encaps and Wirebond")
        self.label3.setGeometry(int(w_width/2), 0, 150, 25)
        self.label.show()
        self.load_button.show()
        self.scrolllabel.show()
        self.logolabel.show()
        self.namelabel.show()
        self.label5.hide()
        string = 'To revisit (frontside only):\n'
        for module_name in find_to_revisit():
            string = string + (module_name + "\n")
        self.scrolllabel.setText(string)

    def load(self, page):
        #check if the module exists
        self.modname = self.combobox.currentText()+"-"+self.modid.text()
        read_query = f"""SELECT EXISTS(SELECT module_name
        FROM module_info
        WHERE module_name ='{self.modname}');"""
        check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        if check['exists'] or page == "encapspage":
            self.begin_program(page)
        else:
            self.label5.show()

    #create pages, button to switch between pages, button to save
    def begin_program(self,page):
        self.label5.hide()
        hexaboard_type = self.modname[5] + self.modname[7]
        global hex_length, y_offset, num_non_signal, x_offset
        if self.modname[5] == "L":
            hex_length = 38
        elif self.modname[5] == "H":
            hex_length = 25
            y_offset += 40
            x_offset+=add_x_offset

        #load position files
        if self.modname[7] == "5":
            num_non_signal = 10
        elif self.modname[7] == "L" or self.modname[7] == "R":
            num_non_signal = 8
        fname = f'./geometries/{hexaboard_type}_hex_positions.csv'
        with open(fname, 'r') as file:
            #read in all the pad positions
            self.df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['padnumber', 'xposition', 'yposition', 'type', 'optional'])
            self.df_pad_map = self.df_pad_map[["padnumber","xposition","yposition"]]

        fname = f'./geometries/{hexaboard_type}_backside_mbites_pos.csv'
        with open(fname, 'r') as file:
           self.df_backside_mbites_pos = pd.read_csv(file, skiprows = 1, names = ['padnumber','xposition','yposition'])

        #load pad to channel mappings
        fname = f'./geometries/{hexaboard_type}_pad_to_channel_mapping.csv'
        with open(fname, 'r') as file:
            #read in all the channels and what pad they're connected to (not used but possibly useful in the future)
            self.df_pad_to_channel = pd.read_csv(file, skiprows = 1, names = ['padnumber', 'ASIC','Channel','Channeltype','Channelpos'])
            self.df_pad_to_channel = self.df_pad_to_channel.set_index("padnumber")

        self.modid.hide()
        self.combobox.hide()
        self.label2.hide()
        self.scrolllabel.hide()
        self.label.hide()
        self.load_button.hide()
        self.logolabel.hide()
        self.namelabel.hide()

        if page == "encapspage":
            encapspage = EncapsPage(self)
            self.widget.addWidget(encapspage)
            self.widget.setCurrentWidget(encapspage)
            self.label3.setText("Encapsulation")
            self.label3.setGeometry(int(w_width/2), 0, 160, 25)
            self.label3.show()
        else:
            info_dict = read_from_db(self.modname, self.df_pad_map, self.df_backside_mbites_pos)
            if page == "frontpage":
                frontpage = FrontPage(self.modname, self.df_pad_map, self.df_backside_mbites_pos, self.df_pad_to_channel, info_dict)
                self.widget.addWidget(frontpage)
                self.widget.setCurrentWidget(frontpage)
            elif page == "pullpage":
                pullpage = PullPage(self.modname, info_dict)
                self.widget.addWidget(pullpage)
                self.widget.setCurrentWidget(pullpage)
            elif page == "backpage":
                backpage = BackPage(self.modname,self.df_pad_map, self.df_backside_mbites_pos, self.df_pad_to_channel,info_dict)
                self.widget.addWidget(backpage)
                self.widget.setCurrentWidget(backpage)
            self.label3.setText(self.modname)
            self.label3.setGeometry(int(w_width/2), 0, 160, 25)
            self.label3.show()

        self.widget.show()
        self.label = QLabel("Last Saved: Unsaved since opened", self)
        self.label.setGeometry(w_width-90-20-225, 0, 225, 25)
        self.label.show()
        save_button = SaveButton(self.widget, self.modname, self.label, 90, 25, "Save", self)
        save_button.setGeometry(w_width-save_button.width-10, 0, save_button.width, save_button.height)
        save_button.show()

        homebutton = HomePageButton("Home page", 75, 25, self)
        homebutton.setGeometry(0, 0, homebutton.width, homebutton.height)
        homebutton.clicked.connect(lambda: self.helper(self.widget))
        homebutton.show()

    def helper(self, widget):
        page = widget.currentWidget()
        if page.pageid == "frontpage":
            upload_front_wirebond(self.modname, page.techname.text(), page.comments.toPlainText(), page.wedgeid.text(), page.spool.text(), page.marked_done.isChecked(), page.buttons)
        elif page.pageid == "pullpage":
            upload_bond_pull_test(self.modname, page.mean.text(), page.std.text(), page.techname.text(), page.comments.toPlainText())
        elif page.pageid == "backpage":
            upload_back_wirebond(self.modname, page.techname.text(), page.comments.toPlainText(), page.wedgeid.text(), page.spool.text(), page.marked_done.isChecked(), page.buttons)
        elif page.pageid == "encapspage":
            upload_encaps(page.modules, page.techname.text(), page.comments.toPlainText())
        self.show_start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        painter.drawLine(QPoint(0,25),QPoint(w_width,25))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Calibri", text_font_size)
    font.setWeight(text_font_size)
    QApplication.setFont(font, "QLabel")
    mainWindow = MainWindow()
    mainWindow.setGeometry(0, 0, w_width, w_height)
    mainWindow.show()
    sys.exit(app.exec_())
