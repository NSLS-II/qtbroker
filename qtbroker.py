from collections import Iterable, OrderedDict
from PyQt5.QtWidgets import (QTreeWidgetItem, QMainWindow, QTreeWidget,
                             QWidget, QHBoxLayout, QVBoxLayout, QLineEdit)
from PyQt5.QtCore import pyqtSlot
from matplotlib.figure import Figure
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.backends import qt_compat


def fill_item(item, value):
    """
    Display a dictionary as a QtTreeWidget

    adapted from http://stackoverflow.com/a/21806048/1221924
    """
    item.setExpanded(True)
    if hasattr(value, 'items'):
        for key, val in sorted(value.items()):
            child = QTreeWidgetItem()
            # val is dict or a list -> recurse
            if (hasattr(val, 'items') or _listlike(val)):
                child.setText(0, _short_repr(key).strip("'"))
                item.addChild(child)
                fill_item(child, val)
                if key == 'descriptors':
                    child.setExpanded(False)
            # val is not iterable -> show key and val on one line
            else:
                text = "{}: {}".format(_short_repr(key).strip("'"),
                                       _short_repr(val))
                child.setText(0, text)
                item.addChild(child)

    elif type(value) is list:
        for val in value:
            if hasattr(val, 'items'):
                fill_item(item, val)
            elif _listlike(val):
                fill_item(item, val)
            else:
                child = QTreeWidgetItem()
                item.addChild(child)
                child.setExpanded(True)
                child.setText(0, _short_repr(val))
    else:
        child = QTreeWidgetItem()
        child.setText(0, _short_repr(value))
        item.addChild(child)


def _listlike(val):
    return isinstance(val, Iterable) and not isinstance(val, str)


def _short_repr(text):
    r = repr(text)
    if len(r) > 30:
        r = r[:27] + '...'
    return r


def fill_widget(widget, value):
    widget.clear()
    fill_item(widget.invisibleRootItem(), value)


def view_header(header):
    widget = QTreeWidget()
    widget.setAlternatingRowColors(True)
    fill_widget(widget, header)
    widget.show()
    return widget


class HeaderViewerWidget:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self._fig = Figure((5.0, 4.0), dpi=100)
        self._widget = QWidget()
        self._tree = QTreeWidget()
        self._tree.setAlternatingRowColors(True)

        canvas = FigureCanvas(self._fig)

        layout = QHBoxLayout()
        layout.addWidget(self._tree)
        layout.addWidget(canvas)
        self._widget.setLayout(layout)

    def __call__(self, header):
        self.dispatcher(header, self._fig)
        fill_widget(self._tree, header)


class HeaderViewerWindow(HeaderViewerWidget):
    """
    Parameters
    ----------
    dispatcher : callable
        expected signature: ``f(header, fig)``

    Example
    -------
    >>> def f(header, fig):
    ...     db.process(header,
    ...                LivePlot(header['start']['detectors'][0], fig=fig))
    ...
    >>> h = db[-1]
    >>> view = HeaderViewerWindow(f)
    >>> view(h)  # spawns Qt window for viewing h
    """
    def __init__(self, dispatcher):
        super().__init__(dispatcher)
        self._window = QMainWindow()
        self._window.setCentralWidget(self._widget)
        self._window.show()


class BrowserWidget:
    def __init__(self, db, dispatcher):
        self.db = db
        self._hvw = HeaderViewerWidget(dispatcher)
        self._search_bar = QLineEdit()
        self._search_bar.textChanged.connect(self._on_search_text_changed)
        self._widget = QWidget()
        
        layout = QVBoxLayout()
        layout.addWidget(self._search_bar)
        layout.addWidget(self._hvw._widget)
        self._widget.setLayout(layout)

    @pyqtSlot()
    def _on_search_text_changed(self):
        text = self._search_bar.text()
        try:
            query = eval("dict({})".format(text))
        except Exception:
            self._search_bar.setStyleSheet(BAD_TEXT_INPUT)
        else:
            self._search_bar.setStyleSheet(GOOD_TEXT_INPUT)
            self._headers = self.db(**query)
            print(len(self._headers))

class BrowserWindow(BrowserWidget):
    """
    Parameters
    ----------
    db : Broker
    dispatcher : callable
        expected signature: ``f(header, fig)``

    Example
    -------
    >>> def f(header, fig):
    ...     db.process(header,
    ...                LivePlot(header['start']['detectors'][0], fig=fig))
    ...
    >>> browser = BrokerWindow(db, f)  # spawns Qt window for searching/viewing
    """
    def __init__(self, db, dispatcher):
        super().__init__(db, dispatcher)
        self._window = QMainWindow()
        self._window.setCentralWidget(self._widget)
        self._window.show()


BAD_TEXT_INPUT = """
QLineEdit {
    background-color: rgb(255, 100, 100);
}
"""


GOOD_TEXT_INPUT = """
QLineEdit {
    background-color: rgb(255, 255, 255);
}
"""
