# Write your code here :-)
import sys, csv
import pandas as pd
from wirebonder_gui_buttons import Hex

from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QLabel, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt, QRectF, QRect, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QRegion, QPainterPath, QPolygonF
from PyQt5.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QComboBox

class MainWindow2(QMainWindow):
    def __init__(self):
        super().__init__()
        fname = f'./geometries/HR_hex_positions.csv'
        with open(fname, 'r') as file:
            #read in all the pad positions
            df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['padnumber', 'xposition', 'yposition'])
            df_pad_map = df_pad_map.set_index("padnumber")
        print(df_pad_map)
        i = 0
        for index,row0 in df_pad_map.iterrows():
            pad = Hex(25, str(index), [0,0],'#d1d1d1', self)
            pad.setGeometry(int(float(row0["xposition"]*90) + 700),int(float(row0["yposition"]*-90) + 200), int(pad.radius)*2, int(pad.radius)*2)
            i += 1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow2 = MainWindow2()
    mainWindow2.setGeometry(0, 0, 1400, 1000)
    mainWindow2.show()
    sys.exit(app.exec_())


fname = f'./geometries/LR_hex_positions.txt'
with open(fname, 'r') as file:
    #read in all the channels and what pad they're connected to (not used but possibly useful in the future)
    df_pad_map = pd.read_csv(fname, skiprows= 1, sep = '\t', names = ['padnumber', 'xposition', 'yposition', 'type', 'optional'])
    df_pad_map = df_pad_map[["padnumber","xposition","yposition"]].set_index("padnumber")

df_pad_map.to_csv('./geometries/LR_hex_positions.csv')

'''
fname = f'./geometries/LR_pad_to_channel_mapping.csv'
with open(fname, 'r') as file:
    #read in all the channels and what pad they're connected to (not used but possibly useful in the future)
    df_pad_map = pd.read_csv(fname, skiprows= 1, names = ['PAD', 'ASIC', 'Channel', 'Channeltype'])
    df_pad_map = df_pad_map[['PAD', 'ASIC', 'Channel', 'Channeltype']].set_index("PAD")


sorted_df = df_pad_map.sort_values(by=['PAD'], ascending=True)
sorted_df.to_csv(f'./geometries/LR_pad_to_channel_mapping2.csv')
'''
