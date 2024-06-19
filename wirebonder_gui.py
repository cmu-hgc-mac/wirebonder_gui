import sys, csv
import numpy as np
import pandas as pd
from datetime import datetime
import os.path
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QLabel, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt, QRectF, QRect, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QRegion, QPainterPath, QPolygonF
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout

#cell class
class Hex(QWidget):
    def __init__(self, buttons, state_counter, state_counter_labels, state_button_labels, state, grounded, radius, cell_id, label_pos, channel_id, channel_pos, color,  parent=None):
        super().__init__(parent)
        self.cell_id = cell_id
        self.label_pos = label_pos
        self.radius = radius
        self.state = state
        self.color = color
        self.channel_id = channel_id
        self.channel_pos = channel_pos
        #make button that is associated with this cell, store it in button dict
        self.button2 = WedgeButton(state_counter, state_counter_labels, state_button_labels, self.state, grounded, channel_id, self.channel_pos, ' ',
            [self.radius/3*np.cos(channel_pos*np.pi/3 + np.pi/2),self.radius/3*np.sin(channel_pos*np.pi/3 + np.pi/2)], self.radius/1.5, self)
        buttons[cell_id] = self.button2

    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(x*np.pi/3 + np.pi/2) + self.radius) for x in range (0,6)]
        polygon = QPolygonF(vertices)
        pen = QPen(QColor(self.color))
        painter.setPen(pen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(polygon)

        # Draw label
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        label_rect = QRectF(self.label_pos[0], self.label_pos[1] , self.width()+2, -0 +self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)

        #based on position number of channel, calculate position of button within pad and find
        #angle from center of cell to vertex identified by channel_pos
        angle = 3*np.pi/2 + self.channel_pos*np.pi/3
        self.button2.setGeometry(int(self.radius - self.button2.radius + self.radius*np.cos(angle)),
            int(self.radius - self.button2.radius + self.radius*np.sin(angle)),int(self.button2.radius*2),int(self.button2.radius*2))
        self.button2.show()

#these are the clickable buttons that represent channels
class WedgeButton(QPushButton):
    #whether or not front side buttons are active
    active = 0
    def __init__(self, state_counter, state_counter_labels, state_button_labels, state, grounded, channel_id, channel_pos, label, label_pos, radius, parent=None):
        super().__init__(parent)
        self.state_counter = state_counter
        self.state_counter_labels = state_counter_labels
        self.state_button_labels = state_button_labels
        self.channel_id = channel_id
        self.channel_pos = channel_pos
        self.label_pos = label_pos
        self.label = label
        self.state = int(state)
        self.radius = radius
        self.clicked.connect(self.changeState)
        self.grounded = grounded

    def mousePressEvent(self, QMouseEvent):
        #left click- change color/state
        if QMouseEvent.button() == Qt.LeftButton:
            self.changeState()
        #right click- change border/grounded state
        elif QMouseEvent.button() == Qt.RightButton:
            self.grounded = (self.grounded + 1)%3
            self.update()

    def changeState(self):
        #checks if button is active
        if (self.__class__.active == 1 and self.label[0] != 'b')  or (self.__class__.active == 0 and self.label[0] == 'b'):
            return
        old_state = self.state
        self.state = (self.state + 1) % 4
        self.state_counter[old_state] -= 1
        self.state_counter[self.state] += 1
        self.updateCounter()
        self.update()

    #update label
    def updateCounter(self):
        for state, count_label in self.state_counter_labels.items():
            count_label.setText(f"{state}: {self.state_counter[state]}")

    #draw the button
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())
        pen = QPen(Qt.black)
        painter.setPen(pen)
        #if button name starts with 'b' it is backside, and is active when showing backside
        if (self.__class__.active == 1 and self.label[0] != 'b')  or (self.__class__.active == 0 and self.label[0] == 'b'):
            painter.setBrush(QColor('#c2c2c2'))
            pen.setColor(QColor('#c2c2c2'))
        elif self.state == 0:
            painter.setBrush(QColor('#3498db'))
            pen.setColor(QColor('#3498db'))
        elif self.state == 1:
            painter.setBrush(Qt.yellow)
            pen.setColor(Qt.yellow)
        elif self.state == 3:
            painter.setBrush(Qt.red)
            pen.setColor(Qt.red)
        elif self.state == 2:
            painter.setBrush(QColor('#ffbc36'))
            pen.setColor(QColor('#ffbc36'))

        if self.grounded == 1:
            pen.setColor(Qt.black)
            pen.setStyle(Qt.DotLine)
            pen.setWidth(2)
        if self.grounded == 2:
            pen.setColor(Qt.black)
            pen.setWidth(2)
        painter.setPen(pen)

        start_angle = ((210-self.channel_pos*60)*16)%(360*16)
        span_angle  = 120*16
        if self.channel_pos != 6:
            painter.drawPie(0,0,int(2*self.radius),int(2*self.radius), start_angle, span_angle)
        else:
            #if pos = 6 then the button should be a full circle
            #it's either a mousebite or a calibration channel
            painter.drawEllipse(QPoint(int(self.radius),int(self.radius)),int(self.radius),int(self.radius))
            self.setStyleSheet("margin: 20;")


        # Draw label ONLY IF IT'S a calibration channel or mousebite (i.e. when the button is circular)
        if self.channel_pos == 6:
            font = painter.font()
            font.setPointSize(9)
            pen.setColor(Qt.black)
            painter.setPen(pen)
            painter.setFont(font)
            label_rect = QRectF(self.label_pos[0], self.label_pos[1] , self.width(), self.height())  # Adjust label position relative to button
            painter.drawText(label_rect, Qt.AlignCenter, str(self.label))


#base class for generic grey buttons
class GreyButton(QPushButton):
    def __init__(self, button_text, width, height, parent = None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.button_text = button_text

    #draw button
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor('#c2c2c2'))
        painter.setBrush(QColor('#c2c2c2'))
        painter.setPen(pen)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        self.setStyleSheet("margin: 60;") #increases clickable area inside button

        #draw label
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        # label_rect = QRectF(5, 5 , self.width(), self.height())  # Adjust label position relative to button
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.button_text)

#button that flips from activating front and backside buttons
class FlipButton(GreyButton):
    def __init__(self, buttons, above_label, width, height, button_text, parent = None):
        super().__init__(button_text, width, height, parent)
        self.clicked.connect(self.changeState)
        self.side = 0
        self.above_label = above_label
        self.buttons = buttons

    def changeState(self):
        old_state = self.side
        self.side = (self.side+1)%2
        WedgeButton.active = self.side
        self.updateAboveLabel()
        self.update()
        for key in self.buttons:
            #update all other buttons to adjust color
            self.buttons[key].update()

    def updateAboveLabel(self):
        if self.side == 0:
            self.above_label.setText(f"Showing frontside")
        else:
            self.above_label.setText(f"Showing backside")

#button that sets all "needs to be grounded" states to "has been grounded" states
class GroundButton(GreyButton):
    def __init__(self, button_text, buttons, width, height, parent = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.clicked.connect(self.setGrounded)

    #if a button needs to be grounded, set it to has been grounded
    def setGrounded(self):
        for button_id in self.buttons:
            if self.buttons[button_id].grounded == 1:
                self.buttons[button_id].grounded = 2
            self.buttons[button_id].update()

#button that resets states to the most recent saved version,
#erasing any changes made since then
class ResetButton(GreyButton):
    def __init__(self, module_name, button_text, buttons, width, height, parent = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.module_name = module_name
        self.clicked.connect(self.reset)

    def reset(self):
        fname = f"/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.module_name}_states.csv"
        df_states = pd.DataFrame()
        with open(fname, 'r') as file:
            #read in all the button states
            df_states = pd.read_csv(fname, skiprows = 1, names = ['ID', 'state', 'grounded'])
            df_states = df_states.set_index("ID")
        for index in df_states.index:
            self.buttons[str(index)].state = df_states.loc[str(index)]['state']
            self.buttons[str(index)].grounded = df_states.loc[str(index)]['grounded']
            self.buttons[str(index)].update()

#button that resets states to default/nominal
class SetToNominal(GreyButton):
    def __init__(self, state_counter_labels, state_counter, module_name, button_text, buttons, width, height, parent = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.module_name = module_name
        self.clicked.connect(self.reset)
        self.state_counter_labels = state_counter_labels
        self.state_counter = state_counter

    def reset(self):
        for button_id in self.buttons:
            self.buttons[button_id].state = 0
            self.buttons[button_id].grounded = 0
            self.buttons[button_id].update()
        for state, count_label in self.state_counter_labels.items():
            if state == 0:
                count_label.setText(f"{state}: {len(self.buttons)}")
            else:
                count_label.setText(f"{state}: {0}")

#button that displays information
class InfoButton(QPushButton):
    def __init__(self, width, height, parent = None):
        super().__init__(parent)
        self.clicked.connect(self.show_info)
        self.width = width
        self.parent = parent
        self.height = height
        string =("Page 1 shows a module with each cell numbered, as well as the six frontside \nmousebites(ex. \"m1\") and the six backside mousebites"
            "(ex. \"b1\"). \n\nEach cell has a button corresponding to its channel; the calibration channels\n are just the button.\n\n Each channel may be given one of"
            " 4 color-based flags by clicking on the button \n(0: blue/nominal, 1:yellow/missing one wire bond, 2: orange/missing two bonds, \n3: red/missing three bonds)"
            " and one of 3 outline flags by right clicking on the button\n(0: no outline/does not need to be grounded, 1: dashed outline/needs to be grounded, \n2: solid outline/has been grounded).\n"
            "All color-based flags can be set to nominal using the \"Set to nominal button\" \nand all \"needs to be grounded\" states can be grounded"
            " using the \"Ground all\" button. \n\nBackside mousebites' states can not be changed while displaying the frontside;\nclick the \"Show other side\" button to make"
           " them accessible, and click it again to make\nfrontside active again.\n\nThe \"Reset to last saved version\" will restore the display to the last saved version"
           "\nwhich will ERASE ALL CHANGES MADE SINCE THEN.\n\nThe \"Show page 2\" button displays the other page. \n\nThe \"Save\" button saves the information from both pages"
           " eventually directly\nto the database, but right now to three files:\n {module_name}_encaps.txt, which holds technician name and comments from page 1;\n"
           "{module_name}_states.csv, which saves the ID and two states of each cell;\nand {module_name}_pull.txt, which holds all information from page 2.\n\n")
        self.box = QLabel(string, self.parent)
        self.closebutton = GreyButton("Close", 75, 25, self.parent)
        self.closebutton.hide()
        self.box.hide()

    def show_info(self):
        self.box.setGeometry(350,100, 550,500)
        self.box.setStyleSheet("background-color: rgb(240, 242, 242)")
        self.box.setMargin(5)
        self.closebutton.clicked.connect(self.closeinfo)
        self.closebutton.setGeometry(int((350+550/2)-75/2),565,75,25)
        self.closebutton.show()
        self.box.show()

    def closeinfo(self):
        self.box.hide()
        self.closebutton.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor('#c2c2c2'))
        painter.setBrush(QColor('#c2c2c2'))
        painter.setPen(pen)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        self.setStyleSheet("margin: 60;") #increases clickable area inside button

        #draw label
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        # label_rect = QRectF(5, 5 , self.width(), self.height())  # Adjust label position relative to button
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, "?")

#hexaboard/"requirements" page
class MainWindow(QMainWindow):
    def __init__(self, modid):
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

        #load states from file
        fname = f"/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.modid.text()}_states.csv"
        df_states = pd.DataFrame()
        with open(fname, 'r') as file:
            #read in all the button states
            df_states = pd.read_csv(fname, skiprows = 1, names = ['ID', 'state', 'grounded'])
            df_states = df_states.set_index("ID")

        #set state counter
        self.state_counter = {0: len(df_states[df_states['state'] == 0]), 1: len(df_states[df_states['state'] == 1]), 2: len(df_states[df_states['state'] == 2]), 3: len(df_states[df_states['state'] == 3])}
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

        lab2 = QLabel(self)
        lab2.setText(f"Showing frontside")
        lab2.setGeometry(20,80,150,25)
        side_flip = FlipButton(self.buttons, lab2, 90, 25,  "Show other side", self)
        side_flip.setGeometry(1200-10-side_flip.width,10, side_flip.width, side_flip.height)
        ground_button = GroundButton("Ground all", self.buttons, 90, 25, self)
        ground_button.setGeometry(1200-10-ground_button.width,50, ground_button.width, ground_button.height)
        ground_button.show()
        reset_button = ResetButton(self.modid.text(), "Reset to last\nsaved version\n(irreversible)", self.buttons, 90, 50, self)
        reset_button.setGeometry(1200-10-reset_button.width,90, reset_button.width, reset_button.height)
        reset_button.show()
        nominal_button = SetToNominal(self.state_counter_labels, self.state_counter, self.modid.text(), "Set to nominal", self.buttons, 90, 25, self)
        nominal_button.setGeometry(1200-10-nominal_button.width,155, nominal_button.width, nominal_button.height)
        nominal_button.show()
        info_button = InfoButton(30,30, self)
        info_button.setGeometry(1200-10-info_button.width, 195, info_button.width, info_button.height)
        info_button.show()

        lab6 = QLabel("Technician Name:", self)
        lab6.setGeometry(20,120, 150, 25)
        self.techname = QLineEdit(self)
        self.techname.setGeometry(20,145, 150, 25)
        lab4 = QLabel("Comments:", self)
        lab4.setGeometry(20,160,150,50)
        self.comments = QTextEdit(self)
        self.comments.setGeometry(20, 200, 150, 150)

        #load encapsulation notes
        fname = f'/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.modid.text()}_encaps.txt'
        encaps_data = []
        with open(fname, 'r') as f:
            encaps_data = f.read().split("\n")
        self.techname.setText(encaps_data[1])
        self.comments.setText(encaps_data[2])

        #load pad positions
        fname = '/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/hex_positions.csv'
        df_pad_map = pd.DataFrame()
        with open(fname, 'r') as file:
            #read in all the pad positions
            df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['padnumber', 'xposition', 'yposition', 'type', 'optional'])
            df_pad_map = df_pad_map[["padnumber","xposition","yposition"]].set_index("padnumber")

        #load pad to channel mappings (these are not currently used in the code)
        fname = '/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/ld_pad_to_channel_mapping.csv'
        df_pad_to_channel = pd.DataFrame()
        with open(fname, 'r') as file:
            #read in all the channels and what pad they're connected to (not used but possibly useful in the future)
            df_pad_to_channel = pd.read_csv(file).set_index("PAD")

        pads = []

        #make all the cells
        for index,row0 in df_pad_map.iterrows():
            if index < 0 or index >198: #these are pads that don't correspond to pads on the board
                continue
            if df_pad_to_channel.loc[index]['Channeltype'] == 0:
                #row of the dataframe that converts between pad and the channel number of the channel on that pad
                row1 = df_pad_to_channel.loc[index]
                #row of the dataframe that gives the pad ID, channel state, and whether or not it's grounded
                row2 = df_states.loc[str(index)]
                #the following booleans check if there is a calibration channel on top of the pad; if so, relocate the label
                pad_after = (index < 198 and df_pad_map.loc[index+1]['xposition'] == row0["xposition"] and df_pad_map.loc[index+1]['yposition'] == row0["yposition"])
                pad_before = (index>1 and df_pad_map.loc[index-1]['xposition'] == row0["xposition"] and df_pad_map.loc[index-1]['yposition'] == row0["yposition"])
                if pad_after or pad_before:
                    if row1['Channelpos'] == 0 or row1['Channelpos'] == 1 or row1['Channelpos'] == 5:
                        #move label position if button would cover it
                        pad = Hex( self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'], 30,
                            str(index), [0,18], str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                    else:
                        pad = Hex(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'],row2['grounded'], 30,
                            str(index), [0,-18], str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                    pad.lower()
                else: #if there is no calibration channel, the label can be in the middle of the pad
                    pad = Hex(self.buttons, self.state_counter, self.state_counter_labels, self.state_button_labels,row2['state'],row2['grounded'], 30, str(index), [0,0],
                        str(row1['Channel']), int(row1['Channelpos']), '#d1dbe8', self.widget)
                pad.setGeometry(int(float(row0["xposition"]*70) + 600 ),int(float(row0["yposition"]*-70 + 450)), int(pad.radius*2), int(pad.radius*2))
            else: #calibration channel pads
                pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, row2['state'], row2['grounded'],
                    str(row1['Channel']), 6, str(index), [0,0], 30/3, self.widget)
                pad.setGeometry(int(float(row0["xposition"]*70) + 600 + 30*2/3),int(float(row0["yposition"]*-70 + 450+30*2/3)), int(pad.radius*2), int(pad.radius*2))
                self.buttons[str(index)] = pad
                pad.raise_()
            pads.append(pad)

        #this brings pads in position 3 to the front to remove problematic overlap in clicking areas
        for pad in pads:
            if pad.channel_pos == 3:
                pad.activateWindow()
                pad.raise_()
            elif pad.channel_pos == 6:
                pad.activateWindow()
                pad.raise_()

        #add front and back mousebites
        #id is of the form "mx", where x is an arbitrary indexer for front bites and "bx" for backside
        fname = '/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/mousebite_graphics_pos.csv'
        df_mousebites_pos = pd.DataFrame()
        with open(fname, 'r') as file:
            df_mousebites_pos = pd.read_csv(file).set_index("ID")

        #make mousebites
        for index, row in df_mousebites_pos.iterrows():
            #want these to be circular so pass channel_pos = 6
            pad = WedgeButton(self.state_counter, self.state_counter_labels, self.state_button_labels, df_states.loc[str(index)]['state'], df_states.loc[str(index)]['grounded'], str(index), 6, str(index), [0,0], 13, self.widget)
            pad.setGeometry(int(float(row["xposition"])*70 + 600 + 17),int(float(row["yposition"]*-70 + 450+18)), int(pad.radius*2), int(pad.radius*2))
            self.buttons[str(index)] = pad

#"results" page
class MainWindow2(QMainWindow):
    def __init__(self,modid):
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

        for i in range(60):  ##### This allows scrolling. Weirdly..
            label = QLabel(f"")
            self.vbox.addWidget(label)

        lab2 = QLabel("Technician Name:", self)
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
        fname = f'/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.modid.text()}_pull.txt'
        pull_data = []
        with open(fname, 'r') as f:
            pull_data = f.read().split("\n")
        self.techname.setText(pull_data[1])
        self.mean.setText(pull_data[2])
        self.std.setText(pull_data[3])
        self.comments.setText(pull_data[4])

#button that switches to provided window
class SwitchPageButton(QPushButton):
    def __init__(self, stacked, text, window, width, height, parent = None):
        super().__init__(parent)
        self.stacked=stacked
        self.clicked.connect(self.switch)
        self.window = window
        self.width = width
        self.height = height
        self.text = text

    def switch(self):
        self.stacked.setCurrentWidget(self.window)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        self.setStyleSheet("margin: 60;") #increases clickable area inside button

        #draw label
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        # label_rect = QRectF(5, 5 , self.width(), self.height())  # Adjust label position relative to button
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.text)
        self.setStyleSheet("background-color: transparent")

#button that saves all states and ground states to csv file
class SaveButton(QPushButton):
    def __init__(self, window1, window2, module_name, label, width, height, button_text, parent = None):
        super().__init__(parent)
        self.clicked.connect(self.save)
        self.window1 = window1
        self.window2 = window2
        self.module_name = module_name
        self.label = label
        self.width = width
        self.height = height
        self.button_text  = button_text

    def save(self):
        self.save_csv()
        self.save_encaps()
        self.save_pull()
        self.updateAboveLabel()
        self.update()

    #save states to csv file
    def save_csv(self):
        filename = self.module_name + "_states.csv"
        with open(filename, 'w') as f:
            f.write("ID,state, grounded\n")
            for button in self.window1.buttons:
                s = button + ',' + str(self.window1.buttons[button].state) + ',' + str(self.window1.buttons[button].grounded)+"\n"
                f.write(s)

    #ssave encapsulation comments and technician name
    def save_encaps(self):
        filename = self.module_name + "_encaps.txt"
        with open(filename, 'w') as f:
            f.write(self.module_name + "\n" + self.window1.techname.text() + "\n" + self.window1.comments.toPlainText())

    #save technician name and pull test information
    def save_pull(self):
        filename = self.module_name + "_pull.txt"
        with open(filename, 'w') as f:
            f.write(self.module_name + "\n" + self.window2.techname.text() + "\n" +
                self.window2.mean.text()+ "\n" + self.window2.std.text() + "\n" + self.window2.comments.toPlainText())

    #update label on when last save was
    def updateAboveLabel(self):
        now = datetime.now()
        dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
        self.label.setText("Last Saved: " + dt_string)

    #draw button
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        self.setStyleSheet("margin: 60;") #increases clickable area inside button

        #draw label
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        # label_rect = QRectF(5, 5 , self.width(), self.height())  # Adjust label position relative to button
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.button_text)
        self.setStyleSheet("background-color: transparent")

#overarching window
class MainWindow3(QMainWindow):
    def __init__(self):
        super().__init__()
        #first, display place to input module name
        self.label = QLabel("Module:",self)
        self.label.setGeometry(600-75, 350, 150, 25)
        self.modid = QLineEdit(self)
        self.modid.setGeometry(600-75, 375, 150, 25)
        self.load_button = GreyButton("Load module", 75, 25, self)
        self.load_button.setGeometry(525, 415, 75, 25)
        #wwhen button clicked, try to load module information
        self.load_button.clicked.connect(self.load)

    def load(self):
        path1 = f'/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.modid.text()}_pull.txt'
        path2 = f'/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.modid.text()}_encaps.txt'
        path3 = f'/Users/nedjmakalliney/Desktop/Programs/HGC_DB/wirebonder/{self.modid.text()}_states.csv'
        if os.path.isfile(path1) and os.path.isfile(path2) and os.path.isfile(path3):
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
        widget = QStackedWidget(self)
        mainWindow = MainWindow(self.modid)
        widget.addWidget(mainWindow)
        mainWindow2 = MainWindow2(self.modid)
        widget.addWidget(mainWindow2)
        widget.setCurrentWidget(mainWindow)
        #sets window size (edit to make full screen)
        widget.setGeometry(0, 25, 1200, 1000)
        widget.show()
        switch_button1 = SwitchPageButton(widget, "Show page 1", mainWindow, 75, 25,self)
        switch_button1.setGeometry(0, 0, switch_button1.width, switch_button1.height)
        switch_button1.show()
        switch_button2 = SwitchPageButton(widget, "Show page 2", mainWindow2, 75, 25,self)
        switch_button2.setGeometry(75, 0, switch_button2.width, switch_button2.height)
        switch_button2.show()
        label = QLabel("Last Saved: Unsaved since opened", self)
        label.setGeometry(1200-90-10-225, 0, 225, 25)
        label.show()
        save_button = SaveButton(mainWindow, mainWindow2, self.modid.text(), label, 90, 25, "Save", self)
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
    mainWindow3 = MainWindow3()
    mainWindow3.setGeometry(0, 0, 1200, 1000)
    mainWindow3.show()
    sys.exit(app.exec_())
