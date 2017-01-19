from collections import Iterable, OrderedDict
from PyQt5.QtWidgets import (QTreeWidgetItem, QMainWindow, QTreeWidget,
                             QWidget, QHBoxLayout, QVBoxLayout, QLineEdit,
                             QListWidget, QListWidgetItem, QTabWidget,
                             QCheckBox, QPushButton, QLabel, QFileDialog,
                             QMessageBox)
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
    def __init__(self, dispatcher, db=None):
        self.db = db
        self.dispatcher = dispatcher
        self._tabs = QTabWidget()
        self._widget = QWidget()
        self._tree = QTreeWidget()
        self._tree.setAlternatingRowColors(True)
        self._figures = {}
        self._overplot = {}
        self._header = None  # the current header, used by export functions

        export_csv_btn = QPushButton('CSV')
        export_csv_btn.clicked.connect(self._export_csv)
        export_xlsx_btn = QPushButton('Excel')
        export_xlsx_btn.clicked.connect(self._export_xlsx)
        self._export_btns = [export_csv_btn, export_xlsx_btn]
        # Disable buttons until first data set is loaded.
        [btn.setEnabled(False) for btn in self._export_btns]

        tree_container = QVBoxLayout()
        export_container = QHBoxLayout()
        export_container.addWidget(export_csv_btn)
        export_container.addWidget(export_xlsx_btn)
        layout = QHBoxLayout()
        tree_container.addWidget(QLabel("View Header (metadata):"))
        tree_container.addWidget(self._tree)
        tree_container.addWidget(QLabel("Export Events (data):"))
        tree_container.addLayout(export_container)
        layout.addLayout(tree_container)
        layout.addWidget(self._tabs)
        self._widget.setLayout(layout)

    @pyqtSlot()
    def _export_csv(self):
        if self._header is None:
            # no data loaded yet
            return
        fp, _ = QFileDialog.getSaveFileName(self._widget, 'Export CSV')
        self.db.get_table(self._header).to_csv(fp)

    @pyqtSlot()
    def _export_xlsx(self):
        if self._header is None:
            # no data loaded yet
            return
        try:
            import openpyxl
        except ImportError:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Feature Not Available")
            msg.setInformativeText("The Python package openpyxl must be "
                                   "installed to enable Excel export. Use "
                                   "CSV export instead.")
            msg.setWindowTitle("Error")
            msg.exec_()
        else:
            fp, _ = QFileDialog.getSaveFileName(self._widget, 'Export XLSX')
            self.db.get_table(self._header).to_xlsx(fp)

    def _figure(self, name):
        "matching plt.figure API"
        if name not in self._figures:
            self._figures[name] = self._add_figure(name)
        fig = self._figures[name]
        if not self._overplot[name].isChecked():
            fig.clf()
        return fig

    def __call__(self, header):
        [btn.setEnabled(True) for btn in self._export_btns]
        self._header = header
        self.dispatcher(header, self._figure)
        fill_widget(self._tree, header)

    def _add_figure(self, name):
        tab = QWidget()
        overplot = QCheckBox("Allow overplotting")
        overplot.setChecked(False)
        self._overplot[name] = overplot
        fig = Figure((5.0, 4.0), dpi=100)
        canvas = FigureCanvas(fig)
        canvas.setParent(tab)
        toolbar = NavigationToolbar(canvas, tab)

        layout = QVBoxLayout()
        layout.addWidget(overplot)
        layout.addWidget(canvas)
        layout.addWidget(toolbar)
        tab.setLayout(layout)
        self._tabs.addTab(tab, name)
        return fig


class HeaderViewerWindow(HeaderViewerWidget):
    """
    Parameters
    ----------
    dispatcher : callable
        expected signature: ``f(header, fig)``

    Example
    -------
    >>> def f(header, factory):
    ...     fig = factory(header['start']['plan_name'])
    ...     ax = fig.gca()
    ...     db.process(header,
    ...                LivePlot(header['start']['detectors'][0], ax=ax))
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
    def __init__(self, db, dispatcher, item_template):
        self.db = db
        self._hvw = HeaderViewerWidget(dispatcher, db)
        self.dispatcher = dispatcher
        self.item_template = item_template
        self._results = QListWidget()
        self._results.currentItemChanged.connect(
            self._on_results_selection_changed)
        self._search_bar = QLineEdit()
        self._search_bar.textChanged.connect(self._on_search_text_changed)
        self._widget = QWidget()
        
        layout = QVBoxLayout()
        sublayout = QHBoxLayout()
        layout.addWidget(self._search_bar)
        layout.addLayout(sublayout)
        sublayout.addWidget(self._results)
        sublayout.addWidget(self._hvw._widget)
        self._widget.setLayout(layout)

    @property
    def dispatcher(self):
        return self._dispatcher

    @dispatcher.setter
    def dispatcher(self, val):
        self._dispatcher = val
        self._hvw.dispatcher = val

    @pyqtSlot()
    def _on_search_text_changed(self):
        text = self._search_bar.text()
        try:
            query = eval("dict({})".format(text))
        except Exception:
            self._search_bar.setStyleSheet(BAD_TEXT_INPUT)
        else:
            self._search_bar.setStyleSheet(GOOD_TEXT_INPUT)
            self.search(**query)

    @pyqtSlot()
    def _on_results_selection_changed(self):
        row_index = self._results.currentRow()
        if row_index == -1:  # This means None. Do not update the viewer.
            return
        header = self._headers[row_index]
        self._hvw(header)

    def search(self, **query):
        self._results.clear()
        self._headers = self.db(**query)
        for h in self._headers:
            item = QListWidgetItem(self.item_template.format(**h))
            self._results.addItem(item)


class BrowserWindow(BrowserWidget):
    """
    Parameters
    ----------
    db : Broker
    dispatcher : callable
        expected signature: ``f(header, fig)``

    Example
    -------
    >>> def f(header, factory):
    ...     fig = factory(header['start']['plan_name'])
    ...     ax = fig.gca()
    ...     db.process(header,
    ...                LivePlot(header['start']['detectors'][0], ax=ax))
    ...
    >>> browser = BrokerWindow(db, f)  # spawns Qt window for searching/viewing
    """
    def __init__(self, db, dispatcher, item_template):
        super().__init__(db, dispatcher, item_template)
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
