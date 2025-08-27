import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import QPushButton, QLabel
from PyQt5.QtCore import Qt, QRectF, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygonF, QFont, QBrush
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PyQt5.QtGui import QRegion, QPainterPath
from qasync import QEventLoop, asyncSlot
import math, ast
from modules.postgres_tools import  (upload_front_wirebond, upload_back_wirebond, upload_encaps, 
                                     upload_bond_pull_test, read_front_db, read_back_db, read_pull_db)
from config.graphics_config import button_font_size
font = QFont("Calibri", button_font_size)

def rotate_point(x, y, angle_deg, getx = None, gety = None):
    x_rotated = x * math.cos(angle_deg) - y * math.sin(angle_deg)
    y_rotated = x * math.sin(angle_deg) + y * math.cos(angle_deg)
    if getx:
        return x_rotated
    if gety:
        return y_rotated
    return x_rotated, y_rotated

def rotate_channel_pos(pos_in, rotate_by_angle = 0):  ## counterclockwise to clockwise rotation of spokes
    return (pos_in+((360-math.degrees(rotate_by_angle))/60))%6 

#normal cell class (doesn't include calibration channels)
class Hex(QWidget):
    def __init__(self, radius, cell_id, label_pos, color, parent=None, rotate_by_angle = 0):
        super().__init__(parent)
        self.cell_id = cell_id
        self.label_pos = label_pos
        self.radius = radius
        self.color = color
        self.rotate_by_angle = rotate_by_angle

    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 - self.rotate_by_angle) + self.radius, 
                            self.radius * np.sin(x*np.pi/3 + np.pi/2 - self.rotate_by_angle) + self.radius) for x in range (0,6)]
        polygon = QPolygonF(vertices)
        pen = QPen(QColor(self.color))
        painter.setPen(pen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(polygon)

        # Draw label
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        label_rect = QRectF(self.label_pos[0], self.label_pos[1] , self.width()+2, self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)

#normal cell class (doesn't include calibration channels)
class HalfHex(QWidget):
    def __init__(self, radius, cell_id, label_pos, color, channeltype, parent=None, rotate_by_angle = 0):
        super().__init__(parent)
        self.cell_id = cell_id
        self.label_pos = label_pos
        self.radius = radius
        self.color = color
        self.channeltype = channeltype
        self.rotate_by_angle = rotate_by_angle
        self.rotate_by_angle_rad = math.radians(rotate_by_angle)

    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.channeltype == 2:
            # vertices = [QPointF(self.radius * np.cos(np.pi/2) + self.radius-3, self.radius * np.sin(np.pi/2) + self.radius),
            #     QPointF(self.radius * np.cos(np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(np.pi/3 + np.pi/2) + self.radius),
            #     QPointF(self.radius * np.cos(2*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(2*np.pi/3 + np.pi/2) + self.radius),
            #     QPointF(self.radius * np.cos(3*np.pi/3 + np.pi/2) + self.radius -3, self.radius * np.sin(3*np.pi/3 + np.pi/2) + self.radius)]
            vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius, 
                                self.radius * np.sin(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius) for x in range(0,4) ]
        elif self.channeltype == 3:
            # vertices = [QPointF(self.radius * np.cos(np.pi/2) + self.radius+3, self.radius * np.sin(np.pi/2) + self.radius),
            #     QPointF(self.radius * np.cos(3*np.pi/3 + np.pi/2) + self.radius+3, self.radius * np.sin(3*np.pi/3 + np.pi/2) + self.radius),
            #     QPointF(self.radius * np.cos(4*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(4*np.pi/3 + np.pi/2) + self.radius),
            #     QPointF(self.radius * np.cos(5*np.pi/3 + np.pi/2) + self.radius, self.radius * np.sin(5*np.pi/3 + np.pi/2) + self.radius)]
            vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius, 
                                self.radius * np.sin(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius) for x in range(3,7) ]
        polygon = QPolygonF(vertices)
        pen = QPen(QColor(Qt.black))
        painter.setPen(pen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(polygon)

        # Draw label
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        if self.channeltype == 2:
            x_offset = -12
        elif self.channeltype == 3:
            x_offset = 12
        label_rect = QRectF(self.label_pos[0]+x_offset, self.label_pos[1], self.width()+2, self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)


#normal cell class (doesn't include calibration channels) with channel buttons
class HexWithButtons(Hex):
    def __init__(self, buttons, state_counter, state_counter_labels, state_button_labels, 
                 state, grounded, radius, cell_id, label_pos, channel_id, channel_pos, color,  parent=None, rotate_by_angle = 0, ground_tracker_labels = None):
        super().__init__(radius, cell_id, label_pos, color,parent, rotate_by_angle)
        self.channel_id = channel_id
        self.rotate_by_angle = rotate_by_angle
        self.label_pos = list(rotate_point(label_pos[0],label_pos[1], rotate_by_angle))
        #channel positions start at 0 at the top of the hexagon and are numbered clockwise
        self.channel_pos = rotate_channel_pos(channel_pos, self.rotate_by_angle)
        #make button that is associated with this cell, store it in button dict
        self.button2 = WedgeButton(state_counter, state_counter_labels, state_button_labels, state, grounded, channel_id, self.channel_pos, ' ',
            [self.radius/3*np.cos(channel_pos*np.pi/3 + np.pi/2 -self.rotate_by_angle),self.radius/3*np.sin(channel_pos*np.pi/3 + np.pi/2 -self.rotate_by_angle)], self.radius/1.5, self, ground_tracker_labels = ground_tracker_labels , cell_id=cell_id)
        buttons[cell_id] = self.button2
        self.setMask(self.createMask())

    def createMask(self):
        """Creates a QRegion mask for the pad (rotated trapezoid)."""
        path = QPainterPath()
        vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius, 
                            self.radius * np.sin(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius) for x in range (0,6)] 
        path.moveTo(vertices[0])
        for vertex in vertices[1:]:
            path.lineTo(vertex)
        path.closeSubpath()
        return QRegion(path.toFillPolygon().toPolygon())

    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # rot_point = [list(rotate_point( (self.radius) * np.cos(x*np.pi/3 + np.pi/2),
        #                             (self.radius) * np.sin(x*np.pi/3 + np.pi/2 ),
        #                             -self.rotate_by_angle)) for x in range(0,6)]
        # vertices = [QPointF(rot_point[x][0]+self.radius, rot_point[x][1]+self.radius) for x in range(0,6)]
        
        vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius, 
                            self.radius * np.sin(x*np.pi/3 + np.pi/2 -self.rotate_by_angle) + self.radius) for x in range (0,6)]
        polygon = QPolygonF(vertices)
        pen = QPen(QColor(self.color))
        painter.setPen(pen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(polygon)

        # Draw label
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        label_rect = QRectF(self.label_pos[0], self.label_pos[1] , self.width()+2, self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)

        #based on position number of channel, calculate position of button within pad and find
        #angle from center of cell to vertex identified by channel_pos
        angle = 3*np.pi/2 + self.channel_pos*np.pi/3
        self.button2.setGeometry(int(self.radius - self.button2.radius + self.radius*np.cos(angle)),
            int(self.radius - self.button2.radius + self.radius*np.sin(angle)),int(self.button2.radius*2),int(self.button2.radius*2))
        self.button2.show()

#normal half cell class (doesn't include calibration channels) with channel buttons
class HalfHexWithButtons(Hex):
    def __init__(self, buttons, state_counter, state_counter_labels, state_button_labels, 
                 state, grounded, radius, cell_id, label_pos, channel_id, channel_pos, color, channeltype, parent=None, rotate_by_angle = 0, ground_tracker_labels = None):
        super().__init__(radius, cell_id, label_pos, color, parent,rotate_by_angle)
        self.channel_id = channel_id
        self.rotate_by_angle = rotate_by_angle
        #channel positions start at 0 at the top of the hexagon and are numbered clockwise
        self.channel_pos = rotate_channel_pos(channel_pos, rotate_by_angle)
        # self.label_pos = label_pos
        self.label_pos = list(rotate_point(label_pos[0],label_pos[1], rotate_by_angle))
        self.channeltype = channeltype
        #make button that is associated with this cell, store it in button dict
        self.button2 = WedgeButton(state_counter, state_counter_labels, state_button_labels, state, grounded, channel_id, self.channel_pos, ' ',
            [self.radius/3*np.cos(channel_pos*np.pi/3 + np.pi/2 - self.rotate_by_angle),
             self.radius/3*np.sin(channel_pos*np.pi/3 + np.pi/2 - self.rotate_by_angle)], self.radius/1.5, self, ground_tracker_labels = ground_tracker_labels, cell_id=cell_id)
        buttons[cell_id] = self.button2
        self.setMask(self.createMask())

    def createMask(self):
        """Creates a QRegion mask for the pad (rotated trapezoid)."""
        path = QPainterPath()
        if self.channeltype == 2:
            vertices = [QPointF(self.radius * np.cos(x * np.pi / 3 + np.pi / 2 - self.rotate_by_angle) + self.radius,
                                self.radius * np.sin(x * np.pi / 3 + np.pi / 2 - self.rotate_by_angle) + self.radius)
                        for x in range(0, 4)]
        elif self.channeltype == 3:  
            vertices = [QPointF(self.radius * np.cos(x * np.pi / 3 + np.pi / 2 - self.rotate_by_angle) + self.radius,
                                self.radius * np.sin(x * np.pi / 3 + np.pi / 2 - self.rotate_by_angle) + self.radius)
                        for x in range(3, 7)]

        path.moveTo(vertices[0])
        for vertex in vertices[1:]:
            path.lineTo(vertex)
        path.closeSubpath()
        return QRegion(path.toFillPolygon().toPolygon())
        
    #draw cell
    def paintEvent(self, event):
        #draw pad
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.channeltype == 2:
            vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 - self.rotate_by_angle) + self.radius, 
                                self.radius * np.sin(x*np.pi/3 + np.pi/2 - self.rotate_by_angle) + self.radius) for x in range(0,4)]
        elif self.channeltype == 3:
            vertices = [QPointF(self.radius * np.cos(x*np.pi/3 + np.pi/2 - self.rotate_by_angle) + self.radius, 
                                self.radius * np.sin(x*np.pi/3 + np.pi/2 - self.rotate_by_angle) + self.radius) for x in range(3,7)]
        polygon = QPolygonF(vertices)
        pen = QPen(QColor(Qt.black))
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
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        
        x_offset, y_offset = 0,0
        if self.channeltype == 2:
            x_offset = -self.button2.radius/2
        elif self.channeltype == 3:
            x_offset = self.button2.radius/2
        if self.channel_pos == 1 or self.channel_pos == 5:
            y_offset = self.button2.radius/2
        elif self.channel_pos == 2 or self.channel_pos == 4:
            y_offset = -self.button2.radius/2
        x_offset, y_offset = rotate_point(x_offset, y_offset, -self.rotate_by_angle)
        label_rect = QRectF(self.label_pos[0]+x_offset, self.label_pos[1] + y_offset, self.width()+2, self.height())  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.cell_id)

#these are the clickable buttons that represent channels
class WedgeButton(QPushButton):
    def __init__(self, state_counter, state_counter_labels, state_button_labels, state,
                 grounded, channel_id, channel_pos, label, label_pos, radius, parent=None, rotate_by_angle = 0, ground_tracker_labels = None, cell_id = None):
        super().__init__(parent)
        self.state_counter = state_counter
        self.state_counter_labels = state_counter_labels
        self.state_button_labels = state_button_labels
        self.ground_tracker_labels = ground_tracker_labels
        self.channel_id = channel_id
        self.channel_pos = channel_pos
        self.label_pos = label_pos
        self.label = label
        self.state = int(state)
        self.radius = radius
        self.grounded = grounded
        self.clicked.connect(self.changeState)
        self.rotate_by_angle = rotate_by_angle
        self.cell_id = cell_id
        self.setMask(self.createMask())

    def createMask(self):
        """Creates a QRegion mask for the button in the shape of a wedge."""
        path = QPainterPath()
        center = QPointF(self.radius, self.radius)
        if self.channel_pos != 6:
            start_angle = 210 - self.channel_pos * 60
            end_angle = start_angle + 120
            start_radian, end_radian = np.deg2rad(start_angle), np.deg2rad(end_angle)
            path.moveTo(center)
            for angle in np.linspace(start_radian, end_radian, num=100):  # Smooth arc
                x = self.radius + self.radius * np.cos(angle)
                y = self.radius - self.radius * np.sin(angle)  # Negative because Qt uses inverted Y-axis
                path.lineTo(QPointF(x, y))
            path.lineTo(center)  # Close the wedge
        else:
            start_radian, end_radian = np.deg2rad(0), np.deg2rad(360)
            path.moveTo(center)
            for angle in np.linspace(start_radian, end_radian, num=100):  # Smooth arc
                x = self.radius + self.radius * np.cos(angle)
                y = self.radius - self.radius * np.sin(angle)  # Negative because Qt uses inverted Y-axis
                path.lineTo(QPointF(x, y))
            path.lineTo(center)  # Close the wedge
        
        path.moveTo(center)
        for angle in np.linspace(start_radian, end_radian, num=100):  # Smooth arc
            x = self.radius + self.radius * np.cos(angle)
            y = self.radius - self.radius * np.sin(angle)  # Negative because Qt uses inverted Y-axis
            path.lineTo(QPointF(x, y))
        path.lineTo(center)  # Close the wedge
        return QRegion(path.toFillPolygon().toPolygon())

    def mousePressEvent(self, QMouseEvent):
        #left click- change color/state
        if QMouseEvent.button() == Qt.LeftButton:
            self.changeState()
        #right click- change border/grounded state
        elif QMouseEvent.button() == Qt.RightButton:
            if self.ground_tracker_labels and self.cell_id:
                tobegroundedset  = set(ast.literal_eval( (self.ground_tracker_labels[ 'tobegroundedlist'].text()).split(":")[1].strip()))
                groundedset      = set(ast.literal_eval( (self.ground_tracker_labels[     'groundedlist'].text()).split(":")[1].strip()))
                old_ground_state, cell_id_ground = self.grounded, self.cell_id
                
            ### Toggles between signal, tobeground, ground and keeps track in counter
            self.grounded = (self.grounded + 1)%3  ### This is action when the button is right-clicked
            if self.ground_tracker_labels and self.cell_id:
                new_ground_state = self.grounded
                if old_ground_state == 1 and new_ground_state == 2:
                    tobegroundedset.remove(int(cell_id_ground))
                    groundedset.add(int(cell_id_ground))
                elif old_ground_state == 2 and new_ground_state == 0:
                    groundedset.remove(int(cell_id_ground))
                elif old_ground_state == 0 and new_ground_state == 1:
                    tobegroundedset.add(int(cell_id_ground))
                self.ground_tracker_labels[ 'tobegroundedlist'].setText(f"ToBeGrounded: {list(tobegroundedset)}") 
                self.ground_tracker_labels[     'groundedlist'].setText(f"Grounded: {list(groundedset)}") 
            self.update()

    def changeState(self):
        #checks if button is active
        old_state = self.state
        self.state = (self.state + 1) % 4 ### This is action when the button is left-clicked
        self.state_counter[old_state] -= 1
        self.state_counter[self.state] += 1
        if self.ground_tracker_labels and self.cell_id:  ### remove from unbond list or add to unbond list based on the state
            attemptrebondset = set(ast.literal_eval( (self.ground_tracker_labels['attemptrebondlist'].text()).split(":")[1].strip()))
            new_state, cell_id_unbond = self.state, self.cell_id
            if old_state == 3 and new_state != 3:
                attemptrebondset.remove(int(cell_id_unbond))
            elif old_state != 3 and new_state == 3:
                attemptrebondset.add(int(cell_id_unbond))
            self.ground_tracker_labels["attemptrebondlist"].setText(f"ToBeBonded: {list(attemptrebondset)}")
        self.updateCounter()
        self.update()

    #update label
    def updateCounter(self):
        for state, count_label in self.state_counter_labels.items():
            count_label.setText(f"{state} missing bonds: {self.state_counter[state]}")

    #draw the button
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        if self.state == 0:
            baseColor = '#87d4fa'
        elif self.state == 1:
            baseColor = Qt.yellow
        elif self.state == 3:
            baseColor = '#fa5846'
        elif self.state == 2:
            baseColor = '#ffbc36'

        painter.setBrush(QColor(baseColor))
        pen.setColor(QColor(baseColor))
        pen.setWidth(4)

        if self.grounded == 1:
            painter.setBrush(QBrush(Qt.black, Qt.CrossPattern)) 

        if self.grounded == 2:
            painter.setBrush(Qt.black)

        painter.setPen(pen)

        start_angle = int(np.round(((210-self.channel_pos*60)*16)%(360*16)))
        span_angle  = 120*16
        if self.channel_pos != 6:
            painter.drawPie(0,0,int(2*self.radius),int(2*self.radius), start_angle, span_angle)
        else:
            #if pos = 6 then the button should be a full circle
            #it's either a mousebite or a calibration channel
            painter.drawEllipse(QPoint(int(self.radius),int(self.radius)),int(self.radius),int(self.radius))

        # Draw label ONLY IF IT'S a calibration channel or mousebite (i.e. when the button is circular)
        if self.channel_pos == 6:
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
    def __init__(self, button_text, width, height, parent = None, rotate_by_angle = 0):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.button_text = button_text
        self.rotate_by_angle = rotate_by_angle
        self.original_color = QColor('#c2c2c2')  # Default color
        self.clicked_color = self.original_color.darker(120)  
        self.hover_color = self.original_color.lighter(120)  
        self.current_color = self.original_color 

    #draw button
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self.current_color)
        painter.setBrush(self.current_color)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        self.setStyleSheet("margin: 90px; padding: 0px;") #increases clickable area inside button

        #draw label
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        # label_rect = QRectF(5, 5 , self.width(), self.height())  # Adjust label position relative to button
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.button_text)

    def enterEvent(self, event):
        self.current_color = self.hover_color  
        self.update() 

    def leaveEvent(self, event):
        if not self.underMouse(): 
            self.current_color = self.original_color  
            self.update()  

#button that resets states to the most recent saved version,
#erasing any changes made since then
#for back wirebonding page
class ResetButton(GreyButton):
    def __init__(self, module_name, side, df_pos, techname, comments, button_text, buttons, width, height, parent = None, pool = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.module_name = module_name
        self.df_pos = df_pos
        self.techname = techname
        self.comments = comments
        self.side = side
        self.clicked.connect(self.reset)
        self.pool = pool

    @asyncSlot()
    async def reset(self):
        df_states_dict = await read_back_db(self.pool, self.module_name, self.df_pos)
        try:
            df_states = df_states_dict["df_back_states"]
            self.techname.setText(df_states_dict["back_wirebond_info"]["technician"])
            self.comments.setText(df_states_dict["back_wirebond_info"]["comment"])
        except Exception as e: print(e)

        for index in df_states.index:
            self.buttons[str(int(index))].state = df_states.loc[int(index)]['state']
            self.buttons[str(int(index))].grounded = df_states.loc[int(index)]['grounded']
            self.buttons[str(int(index))].update()


#button that resets states to the most recent saved version,
#erasing any changes made since then
#for front page
class ResetButton2(GreyButton):
    def __init__(self, module_name, side, df_pos, techname, comments, button_text, buttons, width, height, pull_techname,
                 pull_comments, std, mean, parent = None, pool = None, ground_tracker_labels = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.module_name = module_name
        self.df_pos = df_pos
        self.techname = techname
        self.comments = comments
        self.side = side
        self.module_name = module_name
        self.mean = mean
        self.pull_techname = pull_techname
        self.pull_comments = pull_comments
        self.std = std
        self.clicked.connect(self.reset)
        self.pool = pool
        self.ground_tracker_labels = ground_tracker_labels
        self.ground_tracker_labels_init = ground_tracker_labels

    @asyncSlot()
    async def reset(self):
        df_states_dict = await read_front_db(self.pool, self.module_name, self.df_pos) ##["df_front_states"]
        try:
            df_states = df_states_dict["df_front_states"]
            self.techname.setText(df_states_dict["front_wirebond_info"]["technician"])
            self.comments.setText(df_states_dict["front_wirebond_info"]["comment"])
        except Exception as e: print(e)

        for index in df_states.index:
            self.buttons[str(int(index))].state = df_states.loc[int(index)]['state']
            self.buttons[str(int(index))].grounded = df_states.loc[int(index)]['grounded']
            self.buttons[str(int(index))].update()

        pull_info_dict = await read_pull_db(self.pool, self.module_name)
        info = pull_info_dict["pull_info"]
        self.pull_techname.setText(info["technician"])
        self.pull_comments.setText(info["comment"])
        self.std.setText(str(info["std_pull_strg_g"]))
        self.mean.setText(str(info["avg_pull_strg_g"]))
        if self.ground_tracker_labels:
            tobegroundedlist = df_states.index[df_states['grounded'] == 1].tolist()
            tobegroundedlist = str([int(i) for i in tobegroundedlist])
            groundedlist = df_states.index[df_states['grounded'] == 2].tolist()
            groundedlist = str([int(i) for i in groundedlist])
            attemptrebondlist = list(np.intersect1d(df_states.index[df_states['grounded'] == 0].tolist(), df_states.index[df_states['state'] == 3].tolist()))
            attemptrebondlist = str([int(i) for i in attemptrebondlist])
            self.ground_tracker_labels["tobegroundedlist"].setText(f"ToBeGrounded: {tobegroundedlist}")
            self.ground_tracker_labels["groundedlist"].setText(f"Grounded: {groundedlist}")
            self.ground_tracker_labels["attemptrebondlist"].setText(f"ToBeBonded: {attemptrebondlist}")

#button that resets states to default/nominal
class SetToNominal(GreyButton):
    def __init__(self, state_counter_labels, state_counter, module_name, button_text, buttons, width, height, parent = None, ground_tracker_labels = None):
        super().__init__(button_text, width, height, parent)
        self.buttons = buttons
        self.module_name = module_name
        self.clicked.connect(self.reset)
        self.state_counter_labels = state_counter_labels
        self.state_counter = state_counter
        self.ground_tracker_labels = ground_tracker_labels

    def reset(self):
        for button_id in self.buttons:
            self.buttons[button_id].state = 0
            self.buttons[button_id].grounded = 0
            self.buttons[button_id].update()
        for state, count_label in self.state_counter_labels.items():
            if state == 0:
                count_label.setText(f"{state} missing bonds: {len(self.buttons)}")
            else:
                count_label.setText(f"{state} missing bonds: {0}")
        if self.ground_tracker_labels:
            self.ground_tracker_labels["tobegroundedlist"].setText(f"ToBeGrounded: {[]}")
            self.ground_tracker_labels["groundedlist"].setText(f"Grounded: {[]}")
            self.ground_tracker_labels["attemptrebondlist"].setText(f"ToBeBonded: {[]}")

#button that switches to provided window
class HomePageButton(QPushButton):
    def __init__(self, text, width, height, parent = None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.text = text
        self.original_color = QColor('#80d0e0')  # Default color
        self.clicked_color = self.original_color.darker(120)  
        self.hover_color = self.original_color.lighter(120)  
        self.current_color = self.original_color 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setBrush(self.current_color)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        # self.setStyleSheet("margin: 60;") #increases clickable area inside button
        self.setStyleSheet("margin: 60px; padding: 0px;")
        #draw label
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.text)
        self.setStyleSheet("background-color: transparent")

    def enterEvent(self, event):
        self.current_color = self.hover_color  
        self.update() 

    def leaveEvent(self, event):
        if not self.underMouse(): 
            self.current_color = self.original_color  
            self.update()  


#button that saves all states and ground states to csv file
class SaveButton(QPushButton):
    def __init__(self, widget, module_name, label, width, height, button_text, parent = None):
        super().__init__(parent)
        self.widget = widget
        self.module_name = module_name
        self.label = label
        self.width = width
        self.height = height
        self.button_text  = button_text
        self.original_color = QColor('#80e085')  # Default color
        self.clicked_color = self.original_color.darker(120)  
        self.hover_color = self.original_color.lighter(120)  
        self.current_color = self.original_color 

    #update label on when last save was
    def updateAboveLabel(self, message = None):
        now = datetime.now()
        if not message:
            dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
            self.label.setText("Last Saved: " + dt_string)
        else:
            message = f". {message}"
            self.label.setText(f"{self.label.text().replace(message,'')}{message}")

    #draw button
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.black)
        painter.setBrush(self.current_color)
        painter.setPen(pen)
        vertices = [QPoint(0,0), QPoint(self.width,0), QPoint(self.width,self.height), QPoint(0,self.height)]
        polygon = QPolygonF(vertices)
        painter.drawPolygon(polygon)
        self.setStyleSheet("margin: 60px; padding: 0px;")
        #draw label
        painter.setFont(font)
        pen = QPen(Qt.black)
        painter.setPen(pen)
        label_rect = QRectF(0,0, self.width, self.height)  # Adjust label position relative to button
        painter.drawText(label_rect, Qt.AlignCenter, self.button_text)

    def enterEvent(self, event):
        self.current_color = self.hover_color  
        self.update() 

    def leaveEvent(self, event):
        if not self.underMouse(): 
            self.current_color = self.original_color  
            self.update()  


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
