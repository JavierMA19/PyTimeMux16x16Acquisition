#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 12:29:47 2019

@author: aguimera
"""


from __future__ import print_function
from PyQt5 import Qt
from qtpy.QtWidgets import (QHeaderView, QCheckBox, QSpinBox, QLineEdit,
                            QDoubleSpinBox, QTextEdit, QComboBox,
                            QTableWidget, QAction, QMessageBox, QFileDialog,
                            QInputDialog)

from qtpy import QtWidgets, uic
import numpy as np
import time
import os
import sys
from pyqtgraph.parametertree import Parameter, ParameterTree

import PyqtTools.FileModule as FileMod
import PyqtTools.PlotModule as PltMod

from PyqtTools.PlotModule import Plotter as TimePlt
from PyqtTools.PlotModule import PlotterParameters as TimePltPars
from PyqtTools.PlotModule import PSDPlotter as PSDPlt
from PyqtTools.PlotModule import PSDParameters as PSDPltPars


import PyTM16Core.TM16acqThread as AcqMod


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        self.threadAcq = None
        self.threadSave = None
        self.threadPlotter = None
        self.threadPSDPlotter = None
        self.threadPlotterRaw = None

        layout = Qt.QVBoxLayout(self)

        self.btnAcq = Qt.QPushButton("Start Acq!")
        layout.addWidget(self.btnAcq)

        self.ResetGraph = Qt.QPushButton("Reset Graphics")
        layout.addWidget(self.ResetGraph)

        self.SamplingPar = AcqMod.SampSetParam(name='SampSettingConf')
        self.Parameters = Parameter.create(name='App Parameters',
                                           type='group',
                                           children=(self.SamplingPar,))

        self.SamplingPar.NewConf.connect(self.on_NewConf)
        self.SamplingPar.Fs.sigValueChanged.connect(self.on_FsChanged)
        self.SamplingPar.FsxCh.sigValueChanged.connect(self.on_FsxChChanged)

        # self.PlotParams = PltMod.PlotterParameters(name='Plot options')
        # self.Parameters.addChild(self.PlotParams)
        self.PlotParams = TimePltPars(name='TimePlt',
                              title='Time Plot Options')

        self.PlotParams.NewConf.connect(self.on_NewPlotConf)
        self.Parameters.addChild(self.PlotParams)

        self.RawPlotParams = TimePltPars(name='RawPlot')
        self.Parameters.addChild(self.RawPlotParams)

        # self.PSDParams = PltMod.PSDParameters(name='PSD Options')
        # self.PSDParams.NewConf.connect(self.on_NewPSDConf)
        # self.Parameters.addChild(self.PSDParams)
        self.PsdPlotParams = PSDPltPars(name='PSDPlt',
                                        title='PSD Plot Options')
        self.Parameters.addChild(self.PsdPlotParams)

        self.PsdPlotParams.NewConf.connect(self.on_NewPSDConf)

        # self.Parameters.sigTreeStateChanged.connect(self.on_pars_changed)

        self.treepar = ParameterTree()
        self.treepar.setParameters(self.Parameters, showTop=False)
        self.treepar.setWindowTitle('pyqtgraph example: Parameter Tree')

        layout.addWidget(self.treepar)

        self.setGeometry(650, 20, 400, 800)
        self.setWindowTitle('MainWindow')

        self.btnAcq.clicked.connect(self.on_btnStart)
        self.ResetGraph.clicked.connect(self.on_ResetGraph)

        self.FileParameters = FileMod.SaveFileParameters(QTparent=self,
                                                         name='Record File')
        self.Parameters.addChild(self.FileParameters)

        self.ConfigParameters = FileMod.SaveSateParameters(QTparent=self,
                                                           name='Configuration File')
        self.Parameters.addChild(self.ConfigParameters)
        self.on_FsChanged()
        self.on_FsxChChanged()
        self.on_NewConf()

    def on_FsChanged(self):
        self.RawPlotParams.param('Fs').setValue(self.SamplingPar.Fs.value())

    def on_FsxChChanged(self):
        print('FSXCH', self.SamplingPar.FsxCh.value())
        self.PlotParams.param('Fs').setValue(self.SamplingPar.FsxCh.value())
        self.PsdPlotParams.param('Fs').setValue(self.SamplingPar.FsxCh.value())

    def on_pars_changed(self, param, changes):
        print("tree changes:")
        for param, change, data in changes:
            path = self.Parameters.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()
        print('  parameter: %s' % childName)
        print('  change:    %s' % change)
        print('  data:      %s' % str(data))
        print('  ----------')

        if childName == 'SampSettingConf.Sampling Settings.Vgs':
            if self.threadAcq:
                Vds = self.threadAcq.DaqInterface.Vds
                self.threadAcq.DaqInterface.SetBias(Vgs=data, Vds=Vds)

        if childName == 'SampSettingConf.Sampling Settings.Vds':
            if self.threadAcq:
                Vgs = self.threadAcq.DaqInterface.Vgs
                self.threadAcq.DaqInterface.SetBias(Vgs=Vgs, Vds=data)

        # if childName == 'Plot options.RefreshTime':
        #     if self.threadPlotter is not None:
        #         self.threadPlotter.SetRefreshTime(data)

        # if childName == 'Plot options.ViewTime':
        #     if self.threadPlotter is not None:
        #         self.threadPlotter.SetViewTime(data)

        # if childName == 'Raw Plot.ViewTime':
        #     if self.threadPlotterRaw is not None:
        #         self.threadPlotterRaw.SetViewTime(data)

        # if childName == 'Raw Plot.RefreshTime':
        #     if self.threadPlotterRaw is not None:
        #         self.threadPlotterRaw.SetRefreshTime(data)

    def on_NewPSDConf(self):
        if self.threadPSDPlotter is not None:
            nFFT = self.PsdPlotParams.param('nFFT').value()
            nAvg = self.PsdPlotParams.param('nAvg').value()
            self.threadPSDPlotter.InitBuffer(nFFT=nFFT, nAvg=nAvg)

    def on_NewConf(self):
        self.PlotParams.SetChannels(self.SamplingPar.GetChannelsNames())
        self.RawPlotParams.SetChannels(self.SamplingPar.GetRowNames())
        self.PsdPlotParams.ChannelConf = self.PlotParams.ChannelConf
        nChannels = self.PlotParams.param('nChannels').value()
        self.PsdPlotParams.param('nChannels').setValue(nChannels)

    def on_NewPlotConf(self):
        if self.threadPlotter is not None:
            ViewTime = self.PlotParams.param('ViewTime').value()
            self.threadPlotter.SetViewTime(ViewTime)        
            RefreshTime = self.PlotParams.param('RefreshTime').value()
            self.threadPlotter.SetRefreshTime(RefreshTime)        

    def on_ResetGraph(self):
        if self.threadAcq is None:
            return

        # Plot and PSD threads are stopped
        if self.threadPlotter is not None:
            self.threadPlotter.stop()
            self.threadPlotter = None

        if self.threadPSDPlotter is not None:
            self.threadPSDPlotter.stop()
            self.threadPSDPlotter = None

        if self.threadPlotterRaw is not None:
            self.threadPlotterRaw.stop()
            self.threadPlotterRaw = None

        if self.PlotParams.param('PlotEnable').value():
            Pltkw = self.PlotParams.GetParams()
            self.threadPlotter = TimePlt(**Pltkw)
            self.threadPlotter.start()

        if self.PsdPlotParams.param('PlotEnable').value():
            PSDKwargs = self.PsdPlotParams.GetParams()
            self.threadPSDPlotter = PSDPlt(**PSDKwargs)
            self.threadPSDPlotter.start()

        if self.RawPlotParams.param('PlotEnable').value():
            RwPltkw = self.RawPlotParams.GetParams()
            self.threadPlotterRaw = TimePlt(**RwPltkw)
            self.threadPlotterRaw.start()

    def on_btnStart(self):
        if self.threadAcq is None:
            GenKwargs = self.SamplingPar.GetSampKwargs()
            GenChanKwargs = self.SamplingPar.GetChannelsConfigKwargs()
            AvgIndex = self.SamplingPar.SampSet.param('nAvg').value()
            self.threadAcq = AcqMod.DataAcquisitionThread(ChannelsConfigKW=GenChanKwargs,
                                                          SampKw=GenKwargs,
                                                          AvgIndex=AvgIndex,
                                                          )

            self.threadAcq.NewMuxData.connect(self.on_NewSample)
            self.threadAcq.start()

            PlotterKwargs = self.PlotParams.GetParams()

            FileName = self.FileParameters.FilePath()
            print('Filename', FileName)
            if FileName == '':
                print('No file')
            else:
                if os.path.isfile(FileName):
                    print('Remove File')
                    os.remove(FileName)
                MaxSize = self.FileParameters.param('MaxSize').value()
                self.threadSave = FileMod.DataSavingThread(FileName=FileName,
                                                           nChannels=PlotterKwargs['nChannels'],
                                                           MaxSize=MaxSize)
                self.threadSave.start()

            self.on_ResetGraph()

            self.btnAcq.setText("Stop Gen")
            self.OldTime = time.time()
            self.Tss = []
        else:
            self.threadAcq.DaqInterface.Stop()
            self.threadAcq = None

            if self.threadSave is not None:
                self.threadSave.terminate()
                self.threadSave = None
            if self.PlotParams.param('PlotEnable').value():
                self.threadPlotter.terminate()
                self.threadPlotter = None
            if self.threadPSDPlotter is not None:
                self.threadPSDPlotter.stop()
                self.threadPSDPlotter = None
            if self.threadPlotterRaw is not None:
                self.threadPlotterRaw.stop()
                self.threadPlotterRaw = None

            self.btnAcq.setText("Start Gen")

    def on_NewSample(self):
        ''' Visualization of streaming data-WorkThread. '''
        Ts = time.time() - self.OldTime
        self.Tss.append(Ts)
        self.OldTime = time.time()

        if self.threadSave is not None:
            self.threadSave.AddData(self.threadAcq.OutData.transpose())

        if self.threadPlotter is not None:
            self.threadPlotter.AddData(self.threadAcq.OutData.transpose())

        if self.threadPSDPlotter is not None:
            self.threadPSDPlotter.AddData(self.threadAcq.OutData.transpose())

        if self.threadPlotterRaw is not None:
            self.threadPlotterRaw.AddData(self.threadAcq.aiData.transpose())

def main():
    import argparse
    import pkg_resources

    # Add version option
    __version__ = pkg_resources.require("PyqtTools")[0].version
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(
                            version=__version__))
    parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
