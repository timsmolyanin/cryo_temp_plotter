from PySide6 import QtCore, QtWidgets, QtGui
import sys
from vis_UIMainWindow import vis_UIMainWindow, metric_UI_element
from random import uniform, randint
import pyqtgraph as pg
import time
import logging
import os
from paho.mqtt.client import Client as mqtt_client
from paho.mqtt.client import MQTTMessage
from pathlib import Path
from datetime import datetime, date
import numpy as np
import csv

class vis_app(vis_UIMainWindow):

    max_data_array_size = 1e8
    connection_status = 'Disconnected'
    outfile_status = 'default_output.csv'
    writing_status = 'enabled'


    def __init__(self, parent=None):
        self.get_dir()
        self.init_logger()
        self.topics_metrics_dict = self.read_config()
        self.metrics_names = list(self.topics_metrics_dict.keys())
        self.broker_port = 1883

        self.mqtt_interface = mqtt_comm_iface(self)
        self.file_editor = file_editor(self)

        super().__init__(parent, len(self.metrics_names), self)
        self.in_topics = []
        self.lines_dict = {}
        cur_metric_number = 0
        for cur_metric_name in self.topics_metrics_dict.keys():
            cur_metric_color = (randint(100,255), randint(100,255), randint(100,255))
            setattr(self, f'{cur_metric_name}_line', self.create_line(cur_metric_name, cur_metric_color))
            setattr(self, f'{cur_metric_name}_checkbox', self.create_checkbox(cur_metric_name, cur_metric_number))
            setattr(self, f'{cur_metric_name}_value', np.array([[],[]])) #[time][value]
            cur_metric_number +=1

        
        # self.mqtt_interface.start()
        
        #test:
        # self.test_timer = QtCore.QTimer()
        # self.test_timer.setInterval(500)
        # self.test_timer.timeout.connect(self.generate_test_values)
        # self.test_timer.start()
        
        self.update_timer = QtCore.QTimer()
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.update_lines)
        self.update_timer.start()
        self.cur_downsample_factor = 1
        self.cur_points_number = 0
        self.auto_downsampling_enabled = False
        self.cur_time_range = 10 # 0 means all data is displayed

        self.update_status()


    def get_dir(self):
        if getattr(sys, 'frozen', False):
            cur_path = os.path.dirname(sys.executable)
        elif __file__:
            cur_path = os.path.dirname(__file__)
        self.cur_path = str(cur_path.replace('\\', '/'))


    def read_config(self):
        import yaml
        try:
            config_path = Path(self.cur_path).joinpath('vis_app_config.yaml')
            with open(config_path, "r") as stream:
                cfg = yaml.safe_load(stream)
                topics_names = cfg['metrics']
                return topics_names
        except KeyError as err:
            raise KeyError(f'error while reading config: no mandatory field {err} found')
        except Exception as err:
            raise type(err)(f'error while reading config: {err}')


    def init_logger(self):
        self.error_logger = logging.getLogger('error_logger')
        self.error_logger.setLevel(logging.WARNING)
        self.error_logger_handler = logging.FileHandler(filename=f'{self.cur_path}/log.log', mode='a')
        self.error_logger_handler.setFormatter(logging.Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))
        self.error_logger.addHandler(self.error_logger_handler)


    def create_line(self, metric_name:str, metric_color):
        pen = pg.mkPen(color=metric_color)
        line = self.plot_widget.plot(
            [],
            [],
            name=metric_name,
            pen=pen,
            # symbol="",
            symbolSize=2,
            symbolBrush="b",
        )
        line.setVisible(True)
        return line
    

    def edit_line(self, metric_name, property, value = 0):
        cur_line = getattr(self, f'{metric_name}_line')
        match property:
            case 'Visibility':
                cur_line.setVisible(value)
            case _:
                return
    

    def create_checkbox(self, metric_name:str, cur_metric_number):
        cur_checkbox = metric_UI_element(metric_name, self.edit_line, parent=self.central_widget)
        self.main_layout.addWidget(cur_checkbox, cur_metric_number, 1, )
        return cur_checkbox


    def update_lines(self):
        try:
            cur_time = time.time()
            for cur_metric in self.metrics_names:
                self.update_line(cur_metric, cur_time)
            self.file_editor.add_data(self.metrics_names, cur_time)
            self.auto_downsampling(self.cur_points_number)
            self.update_status()
        except Exception as err:
            self.resolve_exception(err)


    def update_line(self, metric_name, cur_time):
        try:
            cur_line = getattr(self, f'{metric_name}_line')
            val_list =  getattr(self, f'{metric_name}_value')
            if self.cur_time_range == 0: # if no time range specified
                cur_line.setData(val_list[0].tolist() , val_list[1].tolist())
                return len(val_list[0])
            left_time_border = cur_time - (self.cur_time_range * 60)
            left_border_idx = 0
            for i in range (len(val_list[0])-1, 0, -1): # search for minimum timestamp to display
                if val_list[0][i]<left_time_border:
                    left_border_idx = i
                    break
            cut_val_list = val_list[:, left_border_idx:]
            cur_line.setData(cut_val_list[0].tolist() , cut_val_list[1].tolist())
        except Exception as err:
            self.resolve_exception(err)
        


    def add_new_value(self, metric_name_value):
        try:
            metric_name, cur_value = metric_name_value
            val_list = getattr(self, f'{metric_name}_value')
            if len(val_list[0,:]) > self.max_data_array_size:
                val_list = val_list[:, 1:]
            cur_time = time.time()
            cur_entry = np.array([[cur_time],[cur_value]])
            val_list = np.append(val_list, cur_entry, axis=1)
            setattr(self, f'{metric_name}_value', val_list)
            metr_checkbox = getattr(self, f'{metric_name}_checkbox')
            metr_checkbox.update_value(cur_value)
        except Exception as err:
            self.resolve_exception(err)
       

    def auto_downsampling(self, NOf_points):
        if self.auto_downsampling_enabled:
            if NOf_points/self.cur_downsample_factor>100:
                self.cur_downsample_factor*=10
                self.plot_widget.getPlotItem().setDownsampling(self.cur_downsample_factor, mode='mean')

    
    def change_time_range(self, new_time_range):
        try:
            self.cur_time_range = int(new_time_range)
        except Exception as err:
            self.resolve_exception(err, 1)


    def update_status(self, msg=None):
        try:
            if msg is not None:
                self.status_bar_label.setText(f'{msg}')
                return
            self.status_bar_label.setText(f'{self.connection_status}; Data writing {self.writing_status}; Output file: {self.outfile_status}')
        except Exception as err:
            self.resolve_exception(err, 1)


    def resolve_exception(self, err:Exception, severity=0):
        msg = f'{err.__class__.__name__}: {err}'
        if severity == 0:
            print(msg)
            self.error_logger.info(msg)
            return
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setText("Error")
        error_dialog.setInformativeText(msg)
        error_dialog.setWindowTitle("Error")
        error_dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        if severity == 1:
            self.error_logger.error(msg)
            error_dialog.exec()
        else:
            self.error_logger.critical(msg)
            error_dialog.exec()
            exit()

    #TEST ONLY:
    def generate_test_values(self):
        for cur_metric in self.metrics_names:
            cur_value = uniform(-1000, 1000)
            self.add_new_value(cur_metric, cur_value)
        

class file_editor():
    def __init__(self, mw) -> None:
        self.mw = mw
        self.file_save_flag = True
        head_row = ['time']
        head_row.extend(self.mw.metrics_names)
        self.out_file_name = 'default_output.csv'
        with open(self.out_file_name, 'a+') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=head_row, lineterminator='\n')
            writer.writeheader()


    def set_file_save_flag(self, value = True):
        self.file_save_flag = value
        if value:
            self.mw.writing_status = 'enabled'
        else:
            self.mw.writing_status = 'disabled'


    def open_file(self, file_path=None):
        if file_path is None:
            f_dialog = QtWidgets.QFileDialog(parent=self.mw)
            file_path = f_dialog.getSaveFileName(self.mw, f'Choose output file file...', f'{self.mw.cur_path}', f'csv (*.csv)')[0]
        if len(file_path)<1:
            return
        self.out_file_name = file_path
        head_row = ['time']
        head_row.extend(self.mw.metrics_names)
        with open(self.out_file_name, 'w+') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=head_row, lineterminator='\n')
            writer.writeheader()
        self.mw.outfile_status = file_path


    def add_data(self, metrics_list, cur_time):
        if not self.file_save_flag:
            return
        cur_row = {'time':f'{datetime.fromtimestamp(cur_time)}'}
        for cur_metric_name in metrics_list:
            try:
                cur_value = getattr(self.mw, f'{cur_metric_name}_value')[1][-1]
                cur_row.update({cur_metric_name:f'{cur_value:0.3f}'})
            except IndexError:
                continue
        if self.out_file_name is not None:
            with open(self.out_file_name, 'a+') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=list(cur_row.keys()), lineterminator='\n')
                writer.writerow(cur_row)



class mqtt_comm_iface(QtCore.QObject):

    read_signal = QtCore.Signal(object)

    def __init__(self, mw:vis_app) -> None:
        super().__init__()
        # self.error_logger = mw.error_logger
        self.mw = mw
        # self.cb_func = self.mw.update_line
        self.broker_ip = '192.168.0.104'
        self.broker_port = 1883
        self.read_signal.connect(self.mw.add_new_value)
        self.resolve_exception = mw.resolve_exception
        self.in_topics = list(self.mw.topics_metrics_dict.values())


    def connect_mqtt(self, broker_ip, broker_port = 1883):        
        self.client = mqtt_client(client_id=f'vis_app-1')
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.client.connect(broker_ip, broker_port)


    def subscribe(self):
        try:
            print(self.in_topics)
            for cur_topic in self.in_topics:
                self.client.subscribe((cur_topic,0)) 
            self.client.on_message = self.on_message
        except Exception as e:
            print('subscribe')
            self.resolve_exception(e, 1)


    def on_connect(self, client, userdata, flags, rc):
        try:
            if rc == 0:
                self.is_connected = True
                self.mw.connection_status = f'connected to {self.broker_ip}:{self.broker_port}'
            else:
                raise ConnectionError(f'Could not connect to controller, return code {rc}')
        except Exception as err:
            print('on_connect')
            self.resolve_exception(err, 1)


    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        self.resolve_exception(ConnectionError('Lost connection to controller, attempting to reconnect'), 1)

    
    def on_message(self, client : mqtt_client, userdata, msg : MQTTMessage):
        try:
            
            metric_name = msg.topic.split("/")[-1]
            value = float(msg.payload.decode())
            self.read_signal.emit((metric_name, value))
        except Exception as err:
            print('on_message')
            self.resolve_exception(type(err)(f'value read error: {err}'), 0)


    def start(self, broker_ip:str = '192.168.0.104', broker_port:int = 1883):
        try:
            if not self.ip_format_check(broker_ip):
                raise ValueError('Incorrect IP address format, expected X.X.X.X')
            self.connect_mqtt(broker_ip=broker_ip, broker_port=broker_port)
            self.subscribe()
            self.client.loop_start() # starts a separate thread (created by paho library)
        except (TimeoutError, ValueError) as err:
            self.resolve_exception(err, 1)
        except Exception as err:
            print('start')
            self.resolve_exception(err, 2)


    def ping_device(self, host:str):
        try:
            import platform, subprocess
            if not self.ip_format_check(host):
                raise ValueError('Incorrect IP address format')
            param = '-n' if platform.system().lower()=='windows' else '-c'
            command = ['ping', param, '1', host]
            if subprocess.call(command) == 0:
                return f'Host is available'
            else:
                return f'Host is unavailable'
        except Exception as err:
            self.resolve_exception(err, 1)
        
    
    def ip_format_check(self, host:str):
        from ipaddress import ip_address
        try:
            ip_address(host)
            return True
        except ValueError:
            return False


if __name__ == '__main__':

    QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
    app = QtWidgets.QApplication(sys.argv)

    # app.setWindowIcon(QtGui.QIcon(':/icons/icon.ico'))

    form = vis_app()
    form.show()
    sys.exit(app.exec())