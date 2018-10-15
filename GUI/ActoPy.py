#! /usr/bin/env python
# Copyright © 2018 Clément Bourguignon, The Storch Lab, McGill
# Distributed under terms of the MIT license.

from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import sys
import time
import struct
from datetime import datetime, timedelta
import serial
import threading


class serial_read_GUI(QtGui.QMainWindow):
    # send_chans = QtCore.pyqtSignal('QVariantList')
    # send_state = QtCore.pyqtSignal('QVariantList')

    def __init__(self):
        super().__init__()

        self.on_toggle = False
        self.n_pirs = 12
        self.active_chans = []
        self.state = False

        self.initUI()

    @QtCore.pyqtSlot()
    def initUI(self):
        # uic.loadUi('SerialReadUI.ui', self)
        self.setWindowTitle('Arduino Serial Reader')

        centralwidget = QtGui.QWidget()

        self.layout = QtGui.QGridLayout()

        self.layout.addWidget(QtGui.QLabel('Parameters'), 0, 1)
        self.layout.addWidget(QtGui.QLabel(''), 2, 1)

        self.layout.addWidget(QtGui.QLabel('Port'), 1, 1)
        self.port = QtGui.QLineEdit('COM7', self)
        self.layout.addWidget(self.port, 1, 2)

        self.layout.addWidget(QtGui.QLabel('Baudrate:'), 1, 3)
        self.baud = QtGui.QLineEdit('115200', self)
        self.layout.addWidget(self.baud, 1, 4)

        self.layout.addWidget(QtGui.QLabel('Sampling rate:'), 1, 5)
        self.winsize = QtGui.QLineEdit('60', self)
        self.layout.addWidget(self.winsize, 1, 6)

        self.name = []
        self.active = []
        self.activity_count = []
        self.showbtn = []
        self.choosefile = []

        for i in range(0, self.n_pirs):
            self.active.append(QtGui.QCheckBox(self))
            self.layout.addWidget(self.active[i], i+3, 0)
            self.active[i].stateChanged.connect(self.set_active_chans)

            self.choosefile.append(QtGui.QPushButton('%d' % (i+1), self))
            self.layout.addWidget(self.choosefile[i], i+3, 1)
            self.choosefile[i].clicked.connect(self.SelectFile)

            self.name.append(QtGui.QLineEdit('', self))
            self.layout.addWidget(self.name[i], i+3, 2)
            self.name[i].editingFinished.connect(self.set_active_chans)

            self.activity_count.append(QtGui.QLabel('', self))
            self.layout.addWidget(self.activity_count[i], i+3, 3)

            self.showbtn.append(QtGui.QPushButton('show %d' % (i+1), self))
            self.layout.addWidget(self.showbtn[i], i+3, 4)
            self.showbtn[i].clicked.connect(self.drawActogram)

        self.serialbtn = QtGui.QPushButton('Open Serial Connection')
        self.serialbtn.clicked.connect(self.StartSerial)
        self.layout.addWidget(self.serialbtn, 4, 6)

        self.startbtn = QtGui.QPushButton('Start')
        self.startbtn.clicked.connect(self.StartRecord)
        self.layout.addWidget(self.startbtn, 6, 6)

        self.stopbtn = QtGui.QPushButton('Stop')
        self.stopbtn.clicked.connect(self.StopRecord)
        self.layout.addWidget(self.stopbtn, 7, 6)

        centralwidget.setLayout(self.layout)
        self.setCentralWidget(centralwidget)

    @QtCore.pyqtSlot()
    def SelectFile(self):
        sender = int(self.sender().text())-1
        filename = QtGui.QFileDialog.getSaveFileName()
        self.name[sender].setText(filename[0])

    @QtCore.pyqtSlot()
    def StartSerial(self):
        try:
            # Initialize connection to serial port
            self.ser = serial.Serial(self.port.text(), self.baud.text())
            print('Connected')

            # Deactivate the button to avoid messing with IO
            self.serialbtn.setEnabled(False)

        except serial.SerialException as e:
            print('Error connecting to serial port: {0}'.format(e) + '\n')

    @QtCore.pyqtSlot()
    def StartRecord(self):
        lock = threading.Lock()
        with lock:
            self.state = True
        print('recording started')

        # We want the reading/recording loop to happen in another thread so
        # the GUI is not frozen and can be moved, plot things, etc.
        # Initialize and start worker thread
        t = threading.Thread(target=self.Record, args=())
        t.deamon = True
        t.start()

        # Deactivate button so we know it worked and we don't risk that a
        # new thread is created (though an exception should occur before)
        self.startbtn.setEnabled(False)

    @QtCore.pyqtSlot()
    def StopRecord(self):
        lock = threading.Lock()
        with lock:
            self.state = False
        print('recording stopped')

        self.startbtn.setEnabled(True)

    @QtCore.pyqtSlot()
    def set_active_chans(self):
        """Set channels whenever one is selected or its name change."""
        lock = threading.Lock()
        with lock:
            self.active_chans = [(i, self.name[i].text()) for (i, j)
                                 in enumerate(self.active) if j.isChecked()]

    @QtCore.pyqtSlot()
    def Record(self):
        """
        Start main worker thread.

        Reads data from serial, stores it, and encodes it to file after each
        winsize period.
        Code runs in an infinite loop that can be toggled on and off with
        self.state.
        """
        winsize = timedelta(seconds=int(self.winsize.text()))
        try:
            # set end of first loop
            end_loop = datetime.now() + winsize

            # Initialize values list
            summing_array = [0 for x in range(0, self.n_pirs)]
            n_reads = 0  # used to calculate average

            # Wait for junk to exit serial
            t1 = time.time()
            while time.time() < t1 + 1.5:
                self.ser.readline()

            # Read ser and write files as long as state is True
            while self.state:
                # Read and format serial input
                in_serial = self.ser.readline()
                if in_serial == b'':
                    return
                cleaned_serial = [int(x, 2) for x
                                    in in_serial.strip().split(b'\t')]
                n_reads += 1

                # Monitor + add status to summing_array
                statusmonitor = []
                for i in self.active_chans:
                    summing_array[i[0]] = summing_array[i[0]] \
                                            + cleaned_serial[i[0]]
                    statusmonitor.append('%d: %d'
                                            % (i[0]+1, cleaned_serial[i[0]]))
                    self.activity_count[i[0]].setText(
                                                '%s' % (summing_array[i[0]]))

                # Monitor output in console
                print('\t'.join(statusmonitor))

                # Check if time to write to file, if so write data to files
                current_time = datetime.now()
                if current_time >= end_loop:
                    bin_start = int(time.mktime(current_time.timetuple()))
                    for n in self.active_chans:
                        with open(n[1], 'ab') as f:
                            float_avg = summing_array[n[0]]/n_reads
                            out_string = struct.pack('=If',
                                                        bin_start, float_avg)
                            f.write(out_string)

                    # Reinitialize values
                    summing_array = [0 for x in range(0, self.n_pirs)]
                    n_reads = 0

                    # Set end of next loop
                    end_loop = current_time + winsize
            
            # Terminate the thread if loop is toggled off
            return

        except Exception as e:
            print('Error: {0}'.format(e) + '\n')
            return

    @QtCore.pyqtSlot()
    def drawActogram(self):
        try:
            sender = ''.join([x for x in self.sender().text()
                              if x.isnumeric()])
            print('plotting ' + sender)
            sender = int(sender)-1

            time_ = []
            status = []

            with open(self.name[sender].text(), 'rb') as f:
                for buff in iter(lambda: f.read(8), b''):
                    anteroom_tuple = struct.unpack('=If', buff)
                    time_.append(anteroom_tuple[0])
                    status.append(anteroom_tuple[1])

            time_ = np.asarray(time_)/(24*3600) + 719163 - 5/24
            status = np.asarray(status)

            days = np.floor(time_)
            x = time_ - days
            y = status + (days[-1] - days)

            self.win = pg.GraphicsWindow()
            pg.setConfigOptions(antialias=True)
            self.p1 = self.win.addPlot()

            for i in range(int(days[0]), int(days[-1]) + 1):
                self.p1.plot(x[days == i], y[days == i], pen='r')
                self.p1.plot(x[days == i-1]+1,           # double-plot
                             y[days == i-1]+1, pen='r')
            self.p1.plot(x[days == int(days[-1])]+1,           # double-plot
                         y[days == int(days[-1])]+1, pen='r')  # last day
            self.p1.showGrid(x=True, y=True)
        except FileNotFoundError:
            print('No file')


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    GUI = serial_read_GUI()
    GUI.show()
    sys.exit(app.exec_())


"""
TODO:
    [ ] Add restore state function for power outages or unexpected restarts
    [ ] Label axes
"""