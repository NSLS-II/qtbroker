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


def view(db, dispatcher):
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
    >>> view(db, f)
    """
    fig = Figure((5.0, 4.0), dpi=100)
    canvas = FigureCanvas(fig)

    header = db[-1]
    dispatcher(header, fig)

    tree = QTreeWidget()
    tree.setAlternatingRowColors(True)
    fill_widget(tree, header)

    search_bar = QLineEdit()

    layout = QHBoxLayout()
    layout.addWidget(tree)
    layout.addWidget(canvas)

    layout2 = QVBoxLayout()
    layout2.addWidget(search_bar)
    layout2.addLayout(layout)

    mw = QWidget()
    mw.setLayout(layout2)
    window = QMainWindow()
    window.setCentralWidget(mw)

    window.show()
    return window
