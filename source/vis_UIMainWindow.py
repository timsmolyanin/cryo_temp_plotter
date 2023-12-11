from typing import Optional
import PySide6.QtCore
import PySide6.QtWidgets
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

# import styles
# from custom_objects import *
# from pid_settings import PidSettings

# from status_form import StatusForm

class vis_UIMainWindow(QtWidgets.QMainWindow):

    def_font = QtGui.QFont("Arial", 13, weight=700)
    int_validator = QtGui.QIntValidator()
    

    def __init__(self, parent=None, metrics_number = 1, child=None):
        self.int_validator.setRange(1, 10000)
        self.child = child
        super().__init__(parent)


        self.setWindowTitle('Cryo data visualizer')

        self.central_widget = QtWidgets.QWidget()
        self.main_layout = QtWidgets.QGridLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)
        self.connect_window = None


        connect_action = QtGui.QAction('Connect', self)
        connect_action.triggered.connect(lambda: self.call_connect_window(None))
        disconnect_action = QtGui.QAction('Disconnect', self)
        disconnect_action.triggered.connect(lambda: exit())
        write_file_action = QtGui.QAction('Write data to file', self)
        write_file_action.setCheckable(True)
        write_file_action.setChecked(True)
        write_file_action.triggered.connect(lambda: child.file_editor.set_file_save_flag(write_file_action.isChecked()))
        select_file_action = QtGui.QAction('Select file to write', self)
        select_file_action.triggered.connect(lambda: child.file_editor.open_file())

        #main menu create
        self.main_menu = self.menuBar()
        self.write_menu = self.main_menu.addMenu(f'&File')
        self.write_menu.addAction(write_file_action)
        self.write_menu.addAction(select_file_action)
        self.connect_menu = self.main_menu.addMenu(f'&Connection')
        self.connect_menu.addAction(connect_action)
        self.connect_menu.addAction(disconnect_action)
        
        #plot widget:
        alignment_flag = QtCore.Qt.AlignmentFlag()
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem(orientation='bottom')})
        self.main_layout.addWidget(self.plot_widget, 0, 0, metrics_number+1, 1, alignment_flag)

        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        time_axis = pg.DateAxisItem()
        self.plot_widget.getPlotItem().setAxisItems({'bottom':time_axis})
        self.plot_widget.getPlotItem().setDownsampling(1, auto=False, mode='mean')
        self.graph_legend = self.plot_widget.addLegend()

        #time range widget:
        self.time_range_widget = QtWidgets.QWidget()
        self.time_range_layout = QtWidgets.QGridLayout(self.time_range_widget)

        self.range_label = QtWidgets.QLabel()
        self.range_label.setText('Show:')
        self.time_range_layout.addWidget(self.range_label, 0, 0)

        self.time_range_radio1 = QtWidgets.QRadioButton()
        self.time_range_radio1.setText('Whole data')
        self.time_range_radio1.toggled.connect(lambda: child.change_time_range(0))
        self.time_range_layout.addWidget(self.time_range_radio1, 1, 0, 1, 3, QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignLeft))

        self.time_range_input = QtWidgets.QLineEdit()
        self.time_range_input.setText('10')
        self.time_range_input.setFixedWidth(60)
        self.time_range_input.setValidator(self.int_validator)
        self.time_range_layout.addWidget(self.time_range_input, 2, 1, QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignLeft))

        self.time_range_radio2 = QtWidgets.QRadioButton()
        self.time_range_radio2.setText('Last')
        self.time_range_radio2.setChecked(True)
        self.time_range_radio2.toggled.connect(lambda: child.change_time_range(self.time_range_input.text()))
        self.time_range_layout.addWidget(self.time_range_radio2, 2, 0)

        self.range_label = QtWidgets.QLabel()
        self.range_label.setText('minutes')
        self.time_range_layout.addWidget(self.range_label, 2, 2, QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignLeft))


        self.main_layout.addWidget(self.time_range_widget, metrics_number, 1, QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignTop))

        self.status_bar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar_label = QtWidgets.QLabel()
        self.status_bar.addWidget(self.status_bar_label)

        
        # self.lvl_lbl.setFont(def_font)
        # self.t_01_curve = self.plot_widget.plot(name=f'T_01')

        # self.t_01_curve.setPen("#FF8000", width=3)

        # self.main_layout.addWidget(self.plot_widget, 0, 0, 1, 1)

        # def_font = QtGui.QFont()
        # def_font.setFamily("Tahoma")
        # def_font.setPointSize(12)
        # def_font.setWeight(50)

        # self.t_lbl = QtWidgets.QLabel()
        # # self.t_lbl.setFont(def_font)
        # self.main_layout.addWidget(self.t_lbl, 0, 1, 1, 1)

    def call_connect_window(self, event):
        # print('window')
        if self.connect_window is None:
            self.connect_window = ConnectionWindow(self.child, position=self.pos())
        else:
            self.connect_window.activateWindow()
            self.connect_window.raise_()

        
class metric_UI_element(QtWidgets.QWidget):
    def __init__(self, metric_name:str, event_cb, parent = None,) -> None:
        super().__init__(parent)

        self.setFixedHeight(40)
        left_alignment = QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignLeft))
        self.grid_layout = QtWidgets.QGridLayout(self)
        self.cur_checkbox = QtWidgets.QCheckBox(parent=self)
        self.cur_checkbox.setText(metric_name)
        self.cur_checkbox.setChecked(True)
        self.cur_checkbox.stateChanged.connect(lambda: event_cb(metric_name, 'Visibility', self.cur_checkbox.isChecked()))
        self.grid_layout.addWidget(self.cur_checkbox, 0, 0, left_alignment)

        self.cur_value_display = QtWidgets.QLineEdit()
        self.cur_value_display.setText('')
        self.cur_value_display.setFixedWidth(60)
        self.cur_value_display.setReadOnly(True)
        self.grid_layout.addWidget(self.cur_value_display, 0, 1, QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignLeft))


    def update_value(self, value):
        self.cur_value_display.setText(f'{value:0.3f}')


class ConnectionWindow(QtWidgets.QWidget):
    mw = None

    def __init__(self, mw, position):
        super().__init__()
        self.mw = mw
        self.setGeometry(QtCore.QRect(position.x(), position.y(), 200, 130))
        self.setWindowTitle('Cryo controller connection')
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.make_elements()
        self.show()

    def make_elements(self):
        left_alignment = QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignmentFlag(QtCore.Qt.AlignLeft))
        self.grid_layout = QtWidgets.QGridLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.label.setFixedHeight(30)
        self.label.setText(f'IP Address:')
        self.grid_layout.addWidget(self.label, 0, 0, left_alignment)

        self.ip_input = QtWidgets.QLineEdit()
        self.ip_input.setText('192.168.0.1')
        self.ip_input.setFixedWidth(100)
        self.grid_layout.addWidget(self.ip_input, 0, 1, left_alignment)

        self.connect_button = QtWidgets.QPushButton(self)
        self.connect_button.setText('Connect')
        self.grid_layout.addWidget(self.connect_button, 1, 0, left_alignment)
        self.connect_button.clicked.connect(lambda: self.mw.mqtt_interface.start(self.ip_input.text()))

        self.ping_button = QtWidgets.QPushButton(self)
        self.ping_button.setText('Ping')
        self.grid_layout.addWidget(self.ping_button, 1, 1, left_alignment)
        self.ping_button.clicked.connect(lambda: self.ping_answer_label.setText(self.mw.mqtt_interface.ping_device(self.ip_input.text())))

        self.ping_answer_label = QtWidgets.QLabel(self)
        self.ping_answer_label.setFixedHeight(30)
        self.ping_answer_label.setText(f'')
        self.grid_layout.addWidget(self.ping_answer_label, 2, 0, left_alignment)

