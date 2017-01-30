from collections import Iterable, OrderedDict
import os
from datetime import datetime
import matplotlib
from matplotlib.backends.qt_compat import QtWidgets, QtCore
from matplotlib.figure import Figure


CLIPBOARD = QtWidgets.QApplication.clipboard()


class Placeholder:
    def __init__(self):
        self.widget = QtWidgets.QWidget()


def fill_item(item, value):
    """
    Display a dictionary as a QtWidgets.QtTreeWidget

    adapted from http://stackoverflow.com/a/21806048/1221924
    """
    item.setExpanded(True)
    if hasattr(value, 'items'):
        for key, val in sorted(value.items()):
            child = QtWidgets.QTreeWidgetItem()
            # val is dict or a list -> recurse
            if hasattr(val, 'items') or _listlike(val):
                child.setText(0, _short_repr(key).strip("'"))
                item.addChild(child)
                fill_item(child, val)
                if key == 'descriptors':
                    child.setExpanded(False)
            # val is not iterable -> show key and val on one line
            else:
                # Show human-readable datetime alongside raw timestamp.
                # 1484948553.567529 > '[2017-01-20 16:42:33] 1484948553.567529'
                if (key == 'time') and isinstance(val, float):
                    FMT = '%Y-%m-%d %H:%M:%S'
                    ts = datetime.fromtimestamp(val).strftime(FMT)
                    text = "time: [{}] {}".format(ts, val)
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
                child = QtWidgets.QTreeWidgetItem()
                item.addChild(child)
                child.setExpanded(True)
                child.setText(0, _short_repr(val))
    else:
        child = QtWidgets.QTreeWidgetItem()
        child.setText(0, _short_repr(value))
        item.addChild(child)


def _listlike(val):
    return isinstance(val, Iterable) and not isinstance(val, str)


def _short_repr(text):
    r = repr(text)
    if len(r) > 82:
        r = r[:27] + '...'
    return r


def fill_widget(widget, value):
    widget.clear()
    fill_item(widget.invisibleRootItem(), value)


class TableExportWidget:
    """
    A Widget with buttons for exporting run data to tabular formats.

    Parameters
    ----------
    header : Header
    db : Broker
        This argument will be removed once Headers hold a ref to their Brokers.
    """
    def __init__(self, header, db):
        self.widget = QtWidgets.QWidget()
        self._header = header
        self._db = db
        export_csv_btn = QtWidgets.QPushButton('CSV')
        export_csv_btn.clicked.connect(self._export_csv)
        export_xlsx_btn = QtWidgets.QPushButton('Excel')
        export_xlsx_btn.clicked.connect(self._export_xlsx)
        copy_uid_btn  = QtWidgets.QPushButton('Copy UID to Clipbaord')
        copy_uid_btn.clicked.connect(
            lambda: self._copy_uid(self._header['start']['uid']))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(export_csv_btn)
        layout.addWidget(export_xlsx_btn)
        layout.addWidget(copy_uid_btn)
        self.widget.setLayout(layout)

    @QtCore.pyqtSlot()
    def _copy_uid(self, uid):
        CLIPBOARD.setText(uid)

    @QtCore.pyqtSlot()
    def _export_csv(self):
        fp, _ = QtWidgets.QFileDialog.getSaveFileName(self.widget,
                                                      'Export CSV')
        if not fp:
            return
        # Create a separate CSV for each event stream, named like
        # 'mydata-primary.xlsx', 'mydata-baseline.xlsx', ....
        base, ext = os.path.splitext(fp)
        tables = {d['name']: self._db.get_table(self._header,
                                                stream_name=d['name'])
                  for d in self._header.descriptors}
        for name, df in tables.items():
            df.to_csv('{}-{}{}'.format(base, name, ext))

    @QtCore.pyqtSlot()
    def _export_xlsx(self):
        try:
            import openpyxl
        except ImportError:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Feature Not Available")
            msg.setInformativeText("The Python package openpyxl must be "
                                   "installed to enable Excel export. Use "
                                   "CSV export instead.")
            msg.setWindowTitle("Error")
            msg.exec_()
        else:
            from pandas import ExcelWriter
            fp, _ = QtWidgets.QFileDialog.getSaveFileName(self.widget,
                                                          'Export XLSX')
            if not fp:
                return
            # Write each event stream to a different spreadsheet in one
            # Excel document.
            writer = ExcelWriter(fp)
            tables = {d['name']: self._db.get_table(self._header,
                                                    stream_name=d['name'])
                      for d in self._header.descriptors}
            for name, df in tables.items():
                df.to_excel(writmer, name)
            writer.save()


class HeaderViewerWidget:
    def __init__(self, fig_dispatch, text_dispatch):
        self.fig_dispatch = fig_dispatch
        self.text_dispatch = text_dispatch
        self._tabs = QtWidgets.QTabWidget()
        self.widget = QtWidgets.QWidget()
        self._text_summary = QtWidgets.QLabel()
        self._tree = QtWidgets.QTreeWidget()
        self._tree.setAlternatingRowColors(True)
        self._figures = OrderedDict()
        self._overplot = {}

        tree_container = QtWidgets.QVBoxLayout()
        layout = QtWidgets.QHBoxLayout()
        tree_container.addWidget(self._text_summary)
        tree_container.addWidget(QtWidgets.QLabel("View Header (metadata):"))
        tree_container.addWidget(self._tree)
        tree_container.addWidget(QtWidgets.QLabel("Export Events (data):"))
        self.export_widget = Placeholder()  # placeholder
        tree_container.addWidget(self.export_widget.widget)
        layout.addLayout(tree_container)
        layout.addWidget(self._tabs)
        self.widget.setLayout(layout)
        self.tree_container = tree_container

        backend = matplotlib.get_backend()
        if backend == 'Qt5Agg':
            from matplotlib.backends.backend_qt5agg import (
                FigureCanvasQTAgg as FigureCanvas,
                NavigationToolbar2QT as NavigationToolbar)
        elif backend == 'Qt4Agg':
            from matplotlib.backends.backend_qt4agg import (
                FigureCanvasQTAgg as FigureCanvas,
                NavigationToolbar2QT as NavigationToolbar)
        else:
            raise Exception("matplotlib backend is {!r} but it expected to be"
                            "one of ('Qt4Agg', 'Qt5Agg')".format(backend))
        # Stash them on the instance to avoid needing to re-import.
        self.FigureCanvas = FigureCanvas
        self.NavigationToolbar = NavigationToolbar

    def _figure(self, name):
        "matching plt.figure API"
        # Find a figure with the desired name; if none, create one.
        if name not in self._figures:
            self._figures[name] = self._add_figure(name)
        fig = self._figures[name]
        # If overplotting is not allowed, clear the figure.
        if not self._overplot[name].isChecked():
            fig.clf()
        # Bring the appropriate tab into focus.
        self._tabs.setCurrentIndex(list(self._figures).index(name))
        return fig

    def __call__(self, header, db=None):
        """
        header : Header
        db : Broker
            This will be removed once Headers hold a ref to their Brokers.
        """
        self.fig_dispatch(header, self._figure)
        text = self.text_dispatch(header)
        self._text_summary.setText(text)
        fill_widget(self._tree, header)

        # Remove and destroy the old export widget. Create and add a new one.
        self.tree_container.removeWidget(self.export_widget.widget)
        self.export_widget.widget.deleteLater()
        if db is not None:
            self.export_widget = TableExportWidget(header, db)
            self.tree_container.addWidget(self.export_widget.widget)
        else:
            self.export_widget = Placholder()

    def _add_figure(self, name):
        tab = QtWidgets.QWidget()
        overplot = QtWidgets.QCheckBox("Allow overplotting")
        overplot.setChecked(False)
        self._overplot[name] = overplot
        fig = Figure((5.0, 4.0), dpi=100)
        canvas = self.FigureCanvas(fig)
        canvas.setMinimumWidth(640)
        canvas.setParent(tab)
        toolbar = self.NavigationToolbar(canvas, tab)
        tab_label = QtWidgets.QLabel(name)
        tab_label.setMaximumHeight(20)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(overplot)
        layout.addWidget(tab_label)
        layout.addWidget(canvas)
        layout.addWidget(toolbar)
        tab.setLayout(layout)
        self._tabs.addTab(tab, '{:.8}'.format(name))
        return fig


class HeaderViewerWindow(HeaderViewerWidget):
    """
    Parameters
    ----------
    fig_dispatch : callable
        expected signature: ``f(header, fig_factory)``
    text_dispatch : callable
        expected signature: ``f(header) -> str``

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
    >>> view(h)  # spawns QtWidgets.Qt window for viewing h
    """
    def __init__(self, fig_dispatch, text_dispatch):
        super().__init__(fig_dispatch, text_dispatch)
        self._window = QtWidgets.QMainWindow()
        self._window.setCentralWidget(self.widget)
        self._window.show()


class BrowserWidget:
    def __init__(self, db, fig_dispatch, text_dispatch, short_template):
        self.db = db
        self._hvw = HeaderViewerWidget(fig_dispatch, text_dispatch)
        self.fig_dispatch = fig_dispatch
        self.text_dispatch = text_dispatch
        self.short_template = short_template
        self._results = QtWidgets.QListWidget()
        self._results.currentItemChanged.connect(
            self._on_results_selection_changed)
        self._search_bar = QtWidgets.QLineEdit()
        self._search_bar.textChanged.connect(self._on_search_text_changed)
        self.widget = QtWidgets.QWidget()
        
        layout = QtWidgets.QVBoxLayout()
        sublayout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._search_bar)
        layout.addLayout(sublayout)
        sublayout.addWidget(self._results)
        sublayout.addWidget(self._hvw.widget)
        self.widget.setLayout(layout)

    @QtCore.pyqtSlot()
    def _on_search_text_changed(self):
        text = self._search_bar.text()
        try:
            query = eval("dict({})".format(text))
        except Exception:
            self._search_bar.setStyleSheet(BAD_TEXT_INPUT)
        else:
            self._search_bar.setStyleSheet(GOOD_TEXT_INPUT)
            self.search(**query)

    @QtCore.pyqtSlot()
    def _on_results_selection_changed(self):
        row_index = self._results.currentRow()
        if row_index == -1:  # This means None. Do not update the viewer.
            return
        self._hvw(self._headers[row_index], self.db)

    def search(self, **query):
        self._results.clear()
        self._headers = self.db(**query)
        for h in self._headers:
            item = QtWidgets.QListWidgetItem(self.short_template.format(**h))
            self._results.addItem(item)


class BrowserWindow(BrowserWidget):
    """
    Parameters
    ----------
    db : Broker
    fig_dispatch : callable
        expected signature: ``f(header, fig_factory)``
    text_dispatch : callable
        expected signature: ``f(header) -> str``
    short_template : str
        format string which will be passed ``**header``

    Example
    -------
    >>> def f(header, factory):
    ...     fig = factory(header['start']['plan_name'])
    ...     ax = fig.gca()
    ...     db.process(header,
    ...                LivePlot(header['start']['detectors'][0], ax=ax))
    ...
    >>> t = lambda header: header['plan_name']
    >>> s = '{start[plan_name]}'
    >>> browser = BrokerWindow(db, f, t, s)
    """
    def __init__(self, db, fig_dispatch, text_dispatch, short_template):
        super().__init__(db, fig_dispatch, text_dispatch, short_template)
        self._window = QtWidgets.QMainWindow()
        self._window.setCentralWidget(self.widget)
        self._window.show()


BAD_TEXT_INPUT = """
QtWidgets.QLineEdit {
    background-color: rgb(255, 100, 100);
}
"""


GOOD_TEXT_INPUT = """
QtWidgets.QLineEdit {
    background-color: rgb(255, 255, 255);
}
"""
