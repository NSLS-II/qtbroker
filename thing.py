from collections import Iterable, OrderedDict
from PyQt5.QtWidgets import (QTreeWidgetItem, QMainWindow, QTreeWidget,
                             QWidget, QHBoxLayout)

# import matplotlib
# matplotlib.use("Qt4Agg")
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


def view(header):
    window = QMainWindow()
    mw = QWidget()
    fig = Figure((5.0, 4.0), dpi=100)
    canvas = FigureCanvas(fig)
    ax = fig.gca()
    ax.plot([1,2,3])

    tree = QTreeWidget()
    tree.setAlternatingRowColors(True)
    fill_widget(tree, header)

    layout = QHBoxLayout()
    layout.addWidget(tree)
    layout.addWidget(canvas)
    mw.setLayout(layout)

    window.setCentralWidget(mw)

    window.show()
    return window
