import sys, csv
import numpy as np
import pandas as pd
from datetime import datetime
import os.path
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QLabel, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt, QRectF, QRect, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QRegion, QPainterPath, QPolygonF
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout

from postgres_tools import fetch_PostgreSQL, read_from_db, upload_front_wirebond, upload_back_wirebond, upload_bond_pull_test, read_front_db, read_back_db, read_pull_db

#normal cell class (doesn't include calibration channels)
class Hex(QWidget):
    def __init__(self, radius, cell_id, label_pos, color, parent=None):
        super().__init__(parent)
        self.cell_id = cell_id
        self.label_pos = label_pos
        self.radius = radius
        self.color = color

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

#normal cell class (doesn't include calibration channels)
class HalfHex(QWidget):
    def __init__(self, radius, cell_id, label_pos, color, channeltype,parent=None):
        super().__init__(parent)
        self.cell_id = cell_id
        self.label_pos = label_pos
        self.radius = radius
        self.color = color
        self.channeltype = channeltype

    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.channeltype == 2:
            vertices = [QPointF(self.radius * np.cos(np.pi/2) + self.radius-3, self.radius * np.sin(np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(2*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(2*np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(3*np.pi/3 + np.pi/2) + self.radius -3, self.radius * np.sin(3*np.pi/3 + np.pi/2) + self.radius)]
        elif self.channeltype == 3:
            vertices = [QPointF(self.radius * np.cos(np.pi/2) + self.radius+3, self.radius * np.sin(np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(3*np.pi/3 + np.pi/2) + self.radius+3, self.radius * np.sin(3*np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(4*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(4*np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(5*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(5*np.pi/3 + np.pi/2) + self.radius)]
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
        if self.channeltype == 2:
            x_offset = -12
        elif self.channeltype == 3:
            x_offset = 12
        label_rect = QRectF(self.label_pos[0]+x_offset, self.label_pos[1], self.width()+2, -0 +self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)


#normal cell class (doesn't include calibration channels) with channel buttons
class HexWithButtons(Hex):
    def __init__(self, buttons, state_counter, state_counter_labels, state_button_labels, state, grounded, radius, cell_id, label_pos, channel_id, channel_pos, color,  parent=None):
        super().__init__(radius, cell_id, label_pos, color,parent)
        self.channel_id = channel_id
        #channel positions start at 0 at the top of the hexagon and are numbered clockwise
        self.channel_pos = channel_pos
        #make button that is associated with this cell, store it in button dict
        self.button2 = WedgeButton(state_counter, state_counter_labels, state_button_labels, state, grounded, channel_id, self.channel_pos, ' ',
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

#normal half cell class (doesn't include calibration channels) with channel buttons
class HalfHexWithButtons(Hex):
    def __init__(self, buttons, state_counter, state_counter_labels, state_button_labels, state, grounded, radius, cell_id, label_pos, channel_id, channel_pos, color, channeltype, parent=None):
        super().__init__(radius, cell_id, label_pos, color,parent)
        self.channel_id = channel_id
        #channel positions start at 0 at the top of the hexagon and are numbered clockwise
        self.channel_pos = channel_pos
        self.channeltype = channeltype
        #make button that is associated with this cell, store it in button dict
        self.button2 = WedgeButton(state_counter, state_counter_labels, state_button_labels, state, grounded, channel_id, self.channel_pos, ' ',
            [self.radius/3*np.cos(channel_pos*np.pi/3 + np.pi/2),self.radius/3*np.sin(channel_pos*np.pi/3 + np.pi/2)], self.radius/1.5, self)
        buttons[cell_id] = self.button2

    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.channeltype == 2:
            vertices = [QPointF(self.radius * np.cos(np.pi/2) + self.radius-3, self.radius * np.sin(np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(2*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(2*np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(3*np.pi/3 + np.pi/2) + self.radius -3, self.radius * np.sin(3*np.pi/3 + np.pi/2) + self.radius)]
        elif self.channeltype == 3:
            vertices = [QPointF(self.radius * np.cos(np.pi/2) + self.radius+3, self.radius * np.sin(np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(3*np.pi/3 + np.pi/2) + self.radius+3, self.radius * np.sin(3*np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(4*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(4*np.pi/3 + np.pi/2) + self.radius),
                QPointF(self.radius * np.cos(5*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(5*np.pi/3 + np.pi/2) + self.radius)]
        polygon = QPolygonF(vertices)
        pen = QPen(QColor(self.color))
        painter.setPen(pen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(polygon)

        #based on position number of channel, calculate position of button within pad and find
        #angle from center of cell to vertex identified by channel_pos
        angle = 3*np.pi/2 + self.channel_pos*np.pi/3
        self.button2.setGeometry(int(self.radius - self.button2.radius + self.radius*np.cos(angle)),
            int(self.radius - self.button2.radius + self.radius*np.sin(angle)),int(self.button2.radius*2),int(self.button2.radius*2))
        self.button2.show()

        # Draw label
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        if self.channeltype == 2:
            x_offset = -12
        elif self.channeltype == 3:
            x_offset = 12
        if self.channel_pos == 1 or self.channel_pos == 5:
            y_offset = 9
        elif self.channel_pos == 2 or self.channel_pos == 4:
            y_offset = -9
        label_rect = QRectF(self.label_pos[0]+x_offset, self.label_pos[1] + y_offset, self.width()+2, -0 +self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)

#these are the clickable buttons that represent channels
class WedgeButton(QPushButton):
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
        self.grounded = grounded
        self.clicked.connect(self.changeState)

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
        if self.state == 0:
            painter.setBrush(QColor('#87d4fa'))
            pen.setColor(QColor('#87d4fa'))
        elif self.state == 1:
            painter.setBrush(Qt.yellow)
            pen.setColor(Qt.yellow)
        elif self.state == 3:
            painter.setBrush(QColor('#fa5846'))
            pen.setColor(QColor('#fa5846'))
        elif self.state == 2:
            painter.setBrush(QColor('#ffbc36'))
            pen.setColor(QColor('#ffbc36'))

        if self.grounded == 1:
            pen.setColor(Qt.black)
            pen.setWidth(2)
        if self.grounded == 2:
            painter.setBrush(Qt.black)
            pen.setColor(Qt.black)

        painter.setPen(pen)

        start_angle = ((210-self.channel_pos*60)*16)%(360*16)
        span_angle  = 120*16
        if self.channel_pos != 6:
            painter.drawPie(0,0,int(2*self.radius),int(2*self.radius), start_angle, span_angle)
        else:
            #if pos = 6 then the button should be a full circle
            #it's either a mousebite or a calibration channel
            painter.drawEllipse(QPoint(int(self.radius),int(self.radius)),int(self.radius),int(self.radius))

        # Draw label ONLY IF IT'S a calibration channel or mousebite (i.e. when the button is circular)
        if self.channel_pos == 6:
            font = painter.font()
            font.setPointSize(9)
            pen.setColor(Qt.black)
            painter.setPen(pen)
            painter.setFont(font)
            label_rect = QRectF(self.label_pos[0], self.label_pos[1] , self.width(), self.height())  # Adjust label position relative to button
            painter.drawText(label_rect, Qt.AlignCenter, str(self.label))


class GreyCircle(QWidget):
    def __init__(self, radius, x, y, parent=None):
        super().__init__(parent)
        self.radius = radius
        self.x = x
        self.y = y

    #draw the circle
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setBrush(QColor('#7a7979'))
        pen.setColor(QColor('#7a7979'))
        painter.setPen(pen)
        painter.drawEllipse(QPoint(self.x+self.radius,self.y+self.radius),int(self.radius),int(self.radius))


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

#button that resets states to the most recent saved version,
#erasing any changes made since then
#for both front + back wirebonding pages
class ResetButton(GreyButton):
    def __init__(self, module_name, side, df_pos, techname, comments, button_text, buttons, width, height, parent = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.module_name = module_name
        self.df_pos = df_pos
        self.techname = techname
        self.comments = comments
        self.side = side
        self.clicked.connect(self.reset)

    def reset(self):
        if self.side == "front":
            df_states = read_front_db(self.module_name, self.df_pos)["df_front_states"]
            self.techname.setText(read_front_db(self.module_name, self.df_pos)["front_wirebond_info"]["technician"])
            self.comments.setText(read_front_db(self.module_name, self.df_pos)["front_wirebond_info"]["comment"])

        elif self.side == "back":
            df_states = read_back_db(self.module_name, self.df_pos)["df_back_states"]
            self.techname.setText(read_back_db(self.module_name, self.df_pos)["back_wirebond_info"]["technician"])
            self.comments.setText(read_back_db(self.module_name, self.df_pos)["back_wirebond_info"]["comment"])

        for index in df_states.index:
            self.buttons[str(int(index))].state = df_states.loc[int(index)]['state']
            self.buttons[str(int(index))].grounded = df_states.loc[int(index)]['grounded']
            self.buttons[str(int(index))].update()


#button that resets states to the most recent saved version,
#erasing any changes made since then
#for pull testing page
class ResetButton2(GreyButton):
    def __init__(self, module_name, techname, comments, avg, sd, button_text, width, height, parent = None):
        super().__init__(button_text, width, height, parent)
        self.module_name = module_name
        self.avg = avg
        self.techname = techname
        self.comments = comments
        self.sd = sd
        self.clicked.connect(self.reset)

    def reset(self):
        info = read_pull_db(self.module_name)["pull_info"]
        self.techname.setText(info["technician"])
        self.comments.setText(info["comment"])
        self.sd.setText(str(info["std_pull_strg_g"]))
        self.avg.setText(str(info["avg_pull_strg_g"]))

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
        string = ("The frontside page shows the frontside of the module with each cell numbered, as well as the notches (negative numbers) and guardrail bonds"
                "while the backside page shows the backside of the module, showing the backside notches. Each cell has a button corresponding to its channel, while the calibration channel button is the entire cell."
                "Each button may be left clicked, which will cycle it between four flags, representing the succcess of its three wirebonds: 0: blue/nominal, 1:yellow/missing one wire bond, 2: orange/missing two bonds, "
                "3: red/missing three bonds. Each button may be right clicked, which will give it one of three ground flags: 0: no outline/does not need to be grounded, 1: dashed outline/needs to be grounded, "
                "2: solid outline/has been grounded. All color based flags may be set to blue with the \"Set to Nominal\" button, and all \"needs to be grounded\" states may be set to \"has"
                "been grounded\" using the \"Ground all\" button. \n\nThe \"Reset to last saved version\" resets the code to the most recent version in the database, which will lose all changes made since then."
                "The pull testing page has text boxes for optional pull testing information.")
        self.box = QLabel(string, self.parent)
        self.box.setWordWrap(True)
        self.closebutton = GreyButton("Close", 75, 25, self.parent)
        self.closebutton.hide()
        self.box.hide()

    def show_info(self):
        self.box.setGeometry(350,100, 550, 325)
        self.box.setStyleSheet("background-color: rgb(240, 242, 242)")
        self.box.setMargin(5)
        self.closebutton.clicked.connect(self.closeinfo)
        self.closebutton.setGeometry(int((350+550/2)-75/2),390,75,25)
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

#button that switches to provided window
class SwitchPageButton(QPushButton):
    def __init__(self, stacked_widget, text, window, width, height, parent = None):
        super().__init__(parent)
        self.stacked_widget = stacked_widget
        self.clicked.connect(self.switch)
        self.window = window
        self.width = width
        self.height = height
        self.text = text

    #sets the stacked widget to display the window provided
    def switch(self):
        self.stacked_widget.setCurrentWidget(self.window)

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
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.text)
        self.setStyleSheet("background-color: transparent")

#button that switches to provided window
class HomePageButton(QPushButton):
    def __init__(self, text, width, height, parent = None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.text = text

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
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.text)
        self.setStyleSheet("background-color: transparent")


#button that saves all states and ground states to csv file
class SaveButton(QPushButton):
    def __init__(self, frontpage, backpage, pullpage, module_name, label, width, height, button_text, parent = None):
        super().__init__(parent)
        self.clicked.connect(self.save)
        self.frontpage = frontpage
        self.backpage = backpage
        self.pullpage = pullpage
        self.module_name = module_name
        self.label = label
        self.width = width
        self.height = height
        self.button_text  = button_text

    def save(self):
        upload_front_wirebond(self.module_name, self.frontpage.techname.text(), self.frontpage.comments.toPlainText(), self.frontpage.wedgeid.text(), self.frontpage.spool.text(), self.frontpage.buttons)
        upload_bond_pull_test(self.module_name, self.pullpage.mean.text(), self.pullpage.std.text(), self.pullpage.techname.text(), self.pullpage.comments.toPlainText())
        upload_back_wirebond(self.module_name, self.backpage.techname.text(), self.backpage.comments.toPlainText(), self.backpage.wedgeid.text(), self.backpage.spool.text(),self.backpage.buttons)
        self.updateAboveLabel()
        self.update()

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
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.button_text)
        self.setStyleSheet("background-color: transparent")

# class for scrollable label
class ScrollLabel(QScrollArea):
    def __init__(self, parent = None):
        QScrollArea.__init__(self, parent)
        self.setWidgetResizable(True)
        content = QWidget(self)
        self.setWidget(content)
        lay = QVBoxLayout(content)
        self.label = QLabel(content)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setWordWrap(True)
        lay.addWidget(self.label)

    def setText(self, text):
        self.label.setText(text)