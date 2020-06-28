from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure


class PlotWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.canvas = FigureCanvasQTAgg(Figure())
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.canvas)
        self.layout().addWidget(self.toolbar)
