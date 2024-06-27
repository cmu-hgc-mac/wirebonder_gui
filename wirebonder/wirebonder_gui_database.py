import sys, csv
import numpy as np
import pandas as pd
from datetime import datetime
import os.path
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QLabel, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt, QRectF, QRect, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QRegion, QPainterPath, QPolygonF
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout
import asyncio

from postgres_tools import fetch_PostgreSQL, read_from_db, upload_front_wirebond, upload_back_wirebond, upload_bond_pull_test
from wirebonder_gui_buttons import Hex, HexWithButtons, WedgeButton, GreyButton, FlipButton, SetToNominal, ResetButton, InfoButton, SwitchPageButton, SaveButton, ResetButton2

#hexaboard/"requirements" page
class MainWindow(QMainWindow):
    def __init__(self, modid, df_pad_map, df_backside_mbites_pos, df_pad_to_channel, info_dict):
        super().__init__()

        self.setGeometry(0, 0, 1200, 1000)

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
        self.buttons = {}
        self.modid = modid
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
            lab = QLabel(f"{state}: {self.state_counter[state]}", self)
            lab.move(20, 0 + state * 20)
            self.state_counter_labels[state] = lab

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, self.modid.text(), "Set to nominal", self.buttons, 90, 25, self)
        nominal_button.setGeometry(1200-10-nominal_button.width,75, nominal_button.width, nominal_button.height)
        nominal_button.show()
        info_button = InfoButton(30,30, self)
        info_button.setGeometry(1200-10-info_button.width, 115, info_button.width, info_button.height)
        info_button.show()

        lab6 = QLabel("Technician CERN ID:", self)
        lab6.setGeometry(20,100, 150, 25)
        self.techname = QLineEdit(self)
        self.techname.setGeometry(20,125, 150, 25)
        self.techname.setText(self.info_dict["front_wirebond_info"]["technician"])
        lab4 = QLabel("Comments:", self)
        lab4.setGeometry(20,140,150,50)
        self.comments = QTextEdit(self)
        self.comments.setGeometry(20, 180, 150, 150)
        self.comments.setText(self.info_dict["front_wirebond_info"]["comment"])

        reset_button = ResetButton(self.modid.text(), "front", self.df_pad_map, self.techname, self.comments , "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50, self)
        reset_button.setGeometry(1200-10-reset_button.width,10, reset_button.width, reset_button.height)
        reset_button.show()

        pads = []

        #make all the cells
        for index,row0 in self.df_pad_map.iterrows():
            if index >198:
                continue
            #row of the dataframe that converts between pad and the channel number of the channel on that pad
            row1 = self.df_pad_to_channel.loc[index]
            #row of the dataframe that gives the pad ID, channel state, and whether or not it's grounded
            row2 = self.df_front_states.loc[index]
            if self.df_pad_to_channel.loc[index]['Channeltype'] == 0 and index > 0:
                #the following booleans check if there is a calibration channel on top of the pad; if so, relocate the label
                pad_after = (index < 198 and self.df_pad_map.loc[index+1]['xposition'] == row0["xposition"] and self.df_pad_map.loc[index+1]['yposition'] == row0["yposition"])
                pad_before = (index>1 and self.df_pad_map.loc[index-1]['xposition'] == row0["xposition"] and self.df_pad_map.loc[index-1]['yposition'] == row0["yposition"])
                if pad_after or pad_before:
                    if row1['Channelpos'] == 0 or row1['Channelpos'] == 1 or row1['Channelpos'] == 5:
                        #move label position if button would cover it
                        pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'], 30,
                            str(index), [0,18], str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                    else:
                        pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'],row2['grounded'], 30,
                            str(index), [0,-18], str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                    pad.lower()
                else: #if there is no calibration channel, the label can be in the middle of the pad
                    pad = HexWithButtons(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels,row2['state'],row2['grounded'], 30, str(index), [0,0],
                        str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                pad.setGeometry(int(float(row0["xposition"]*70) + 600 ),int(float(row0["yposition"]*-70 + 450)), int(pad.radius*2), int(pad.radius*2))
            elif self.df_pad_to_channel.loc[index]['Channeltype'] == 1 and index > 0: #calibration channel pads
                pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'],
                    str(row1['Channel']), 6, str(index), [0,0], 30/3, self.widget)
                pad.setGeometry(int(float(row0["xposition"]*70) + 600 + 30*2/3),int(float(row0["yposition"]*-70 + 450+30*2/3)), int(pad.radius*2), int(pad.radius*2))
                self.buttons[str(index)] = pad
                pad.raise_()
            else:
                #want these to be circular so pass channel_pos = 6
                pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'],
                    str(index), 6, str(index), [0,0], 13, self.widget)
                pad.setGeometry(int(float(row0["xposition"])*70 + 600 + 17),int(float(row0["yposition"]*-70 + 450+18)), int(pad.radius*2), int(pad.radius*2))
                self.buttons[str(index)] = pad
            pads.append(pad)

        #this brings pads in position 3 to the front to remove problematic overlap in clicking areas
        for pad in pads:
            if pad.channel_pos == 3:
                pad.activateWindow()
                pad.raise_()
            elif pad.channel_pos == 6:
                pad.activateWindow()
                pad.raise_()

        upload_front_wirebond(self.modid.text(), self.techname.text(), self.comments.toPlainText(), self.buttons)

#hexaboard/"requirements" page
class MainWindow2(QMainWindow):
    def __init__(self, modid, df_pad_map, df_backside_mbites_pos, df_pad_to_channel, info_dict):
        super().__init__()

        self.setGeometry(0, 0, 1200, 1000)

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
        self.buttons = {}
        self.modid = modid
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
            lab = QLabel(f"{state}: {self.state_counter[state]}", self)
            lab.move(20, 0 + state * 20)
            self.state_counter_labels[state] = lab

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, self.modid.text(), "Set to nominal", self.buttons, 90, 25, self)
        nominal_button.setGeometry(1200-10-nominal_button.width,75, nominal_button.width, nominal_button.height)
        nominal_button.show()
        info_button = InfoButton(30,30, self)
        info_button.setGeometry(1200-10-info_button.width, 115, info_button.width, info_button.height)
        info_button.show()

        lab6 = QLabel("Technician CERN ID:", self)
        lab6.setGeometry(20,100, 150, 25)
        self.techname = QLineEdit(self)
        self.techname.setGeometry(20,125, 150, 25)
        self.techname.setText(self.info_dict["back_wirebond_info"]["technician"])
        lab4 = QLabel("Comments:", self)
        lab4.setGeometry(20,140,150,50)
        self.comments = QTextEdit(self)
        self.comments.setGeometry(20, 180, 150, 150)
        self.comments.setText(self.info_dict["back_wirebond_info"]["comment"])

        reset_button = ResetButton(self.modid.text(), "back", self.df_backside_mbites_pos, self.techname, self.comments , "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50, self)
        reset_button.setGeometry(1200-10-reset_button.width,10, reset_button.width, reset_button.height)
        reset_button.show()

        pads = []

        #make all the cells
        for index,row0 in self.df_pad_map.iterrows():
            if index >198:
                continue
            if self.df_pad_to_channel.loc[index]['Channeltype'] == 0 and index > 0:
                pad = Hex(30, str(index), [0,0],'#d1d1d1', self.widget)
                pad.setGeometry(int(float(row0["xposition"]*-70) + 600 ),int(float(row0["yposition"]*-70 + 450)), int(pad.radius*2), int(pad.radius*2))
            pads.append(pad)

        for index,row in self.df_backside_mbites_pos.iterrows():
            #want these to be circular so pass channel_pos = 6
            pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, self.df_back_states.loc[index]['state'], self.df_back_states.loc[index]['grounded'],
                str(index), 6, str(index), [0,0], 13, self.widget)
            pad.setGeometry(int(float(row["xposition"])*-70 + 600 + 17),int(float(row["yposition"]*-70 + 450+18)), int(pad.radius*2), int(pad.radius*2))
            self.buttons[str(index)] = pad

#"results" page
class MainWindow3(QMainWindow):
    def __init__(self,modid,info_dict):
        super().__init__()

        self.setWindowTitle("Tri-State Buttons")
        self.setGeometry(0, 0, 1200, 1000)

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
        self.modid = modid
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

        reset_button = ResetButton2(self.modid.text(), self.techname, self.comments, self.mean, self.std, "Reset to last\nsaved version\n(irreversible)", 90, 50, self)
        reset_button.setGeometry(20,415, reset_button.width, reset_button.height)
        reset_button.show()

#overarching window
class MainWindow4(QMainWindow):
    def __init__(self):
        super().__init__()
        #first, display place to input module name
        self.label = QLabel("Module:",self)
        self.label.setGeometry(600-75, 350, 150, 25)
        self.modid = QLineEdit(self)
        self.modid.setGeometry(600-75, 375, 150, 25)
        self.load_button = GreyButton("Load module", 75, 25, self)
        self.load_button.setGeometry(525, 415, 75, 25)
        #when button clicked, try to load module information
        self.load_button.clicked.connect(self.load)

        fname = './hex_positions.csv'
        self.df_pad_map = pd.DataFrame()
        with open(fname, 'r') as file:
            #read in all the pad positions
            self.df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['padnumber', 'xposition', 'yposition', 'type', 'optional'])
            self.df_pad_map = self.df_pad_map[["padnumber","xposition","yposition"]].set_index("padnumber")

        fname = './backside_mbites_pos.csv'
        self.df_backside_mbites_pos = pd.DataFrame()
        with open(fname, 'r') as file:
           self.df_backside_mbites_pos = pd.read_csv(file).set_index("ID")

        #load pad to channel mappings (these are not currently used in the code)
        fname = './ld_pad_to_channel_mapping.csv'
        self.df_pad_to_channel = pd.DataFrame()
        with open(fname, 'r') as file:
            #read in all the channels and what pad they're connected to (not used but possibly useful in the future)
            self.df_pad_to_channel = pd.read_csv(file).set_index("PAD")

    def load(self):
        read_query = f"""SELECT EXISTS(SELECT module_name
        FROM module_info
        WHERE module_name ='{self.modid.text()}');"""
        check = [dict(record) for record in asyncio.run(fetch_PostgreSQL(read_query))][0]
        if check['exists']:
            self.begin_program()
        else:
            label2 = QLabel("Files not found,\nPlease enter valid module serial number",self)
            label2.setGeometry(525, 440, 300, 50)
            label2.show()

    #create page 1 and 2, button to switch between pages, button to save
    def begin_program(self):
        self.modid.hide()
        self.label.hide()
        self.load_button.hide()
        info_dict = read_from_db(self.modid.text(), self.df_pad_map, self.df_backside_mbites_pos)
        widget = QStackedWidget(self)
        mainWindow = MainWindow(self.modid, self.df_pad_map, self.df_backside_mbites_pos, self.df_pad_to_channel, info_dict)
        widget.addWidget(mainWindow)
        mainWindow3 = MainWindow3(self.modid, info_dict)
        widget.addWidget(mainWindow3)
        mainWindow2 = MainWindow2(self.modid,self.df_pad_map, self.df_backside_mbites_pos, self.df_pad_to_channel,info_dict)
        widget.addWidget(mainWindow2)
        widget.setCurrentWidget(mainWindow)
        #sets window size (edit to make full screen)
        widget.setGeometry(0, 25, 1200, 1000)
        widget.show()
        switch_button1 = SwitchPageButton(widget, "Show frontside", mainWindow, 75, 25,self)
        switch_button1.setGeometry(0, 0, switch_button1.width, switch_button1.height)
        switch_button1.show()
        switch_button2 = SwitchPageButton(widget, "Show backside", mainWindow2, 75, 25,self)
        switch_button2.setGeometry(75, 0, switch_button2.width, switch_button2.height)
        switch_button2.show()
        switch_button2 = SwitchPageButton(widget, "Show pull test", mainWindow3, 75, 25,self)
        switch_button2.setGeometry(150, 0, switch_button2.width, switch_button2.height)
        switch_button2.show()
        label = QLabel("Last Saved: Unsaved since opened", self)
        label.setGeometry(1200-90-10-225, 0, 225, 25)
        label.show()
        save_button = SaveButton(mainWindow, mainWindow2, mainWindow3, self.modid.text(), label, 90, 25, "Save", self)
        save_button.setGeometry(1200-save_button.width-10, 0, save_button.width, save_button.height)
        save_button.show()
        label2 = QLabel(self.modid.text(), self)
        label2.setGeometry(600, 0, 150, 25)
        label2.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        painter.drawLine(QPoint(0,25),QPoint(1200,25))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow3 = MainWindow4()
    mainWindow3.setGeometry(0, 0, 1200, 1000)
    mainWindow3.show()
    sys.exit(app.exec_())

#make save button more obvious (color, size, placement)
#contact jessica + alethea (ucsb)
#320-ML-F2CX-CM-0001

'''
'list_grounded_cells': dummy_list_int,  : All cells with grounded = 1
'list_unbonded_cells': dummy_list_int,  : All cells with state = 3
'cell_no': dummy_list_int,  : Cell # / index
'bond_count_for_cell': dummy_list_int,  : State
'bond_type': dummy_list_str : N = nominal / G = ground
'''
