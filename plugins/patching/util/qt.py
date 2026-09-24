#
# this global is used to indicate whether Qt bindings for python are present
# and whether the plugin should expect to be using UI features
#

QT_AVAILABLE = False
QT_BINDING = None

#
# IDA 9.2+ runs on Qt6 and ships PySide6 (its PyQt5 package is only a
# deprecated shim). older IDA versions run on Qt5 with PyQt5. prefer PySide6
# and fall back to PyQt5 so the plugin works with either.
#

try:
    import PySide6.QtGui as QtGui
    import PySide6.QtCore as QtCore
    import PySide6.QtWidgets as QtWidgets
    import shiboken6
    QT_BINDING = 'PySide6'

except ImportError:
    try:
        import PyQt5.QtGui as QtGui
        import PyQt5.QtCore as QtCore
        import PyQt5.QtWidgets as QtWidgets
        from PyQt5 import sip
        QT_BINDING = 'PyQt5'
    except ImportError:
        pass

# importing Qt went okay, let's see if we're in an IDA Qt context
if QT_BINDING:
    try:
        import ida_kernwin
        QT_AVAILABLE = ida_kernwin.is_idaq()
    except ImportError:
        pass

#--------------------------------------------------------------------------
# Qt Pointer Wrapping
#--------------------------------------------------------------------------

def wrapinstance(address, qt_type):
    """
    Wrap a raw C++ Qt object pointer as the given Qt python type.
    """
    if QT_BINDING == 'PySide6':
        return shiboken6.wrapInstance(int(address), qt_type)
    return sip.wrapinstance(int(address), qt_type)

def twidget_to_qwidget(twidget):
    """
    Wrap an IDA TWidget* (SWIG object or PyCapsule) as a QWidget.

    IDA can hand a PyCapsule (rather than a SWIG TWidget*) to OnCreate(),
    and IDA's own conversion helpers prefer whichever binding they were built
    against, so we unpack the pointer ourselves and wrap it with the binding
    this plugin actually imported.
    """
    import ctypes

    if type(twidget).__name__ == 'SwigPyObject':
        address = int(twidget)
    else:
        get_pointer = ctypes.pythonapi.PyCapsule_GetPointer
        get_pointer.restype = ctypes.c_void_p
        get_pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
        address = get_pointer(twidget, b'$valid$')

    if not address:
        raise RuntimeError("IDA returned an invalid TWidget pointer")

    return wrapinstance(address, QtWidgets.QWidget)

#--------------------------------------------------------------------------
# Qt Misc Helpers
#--------------------------------------------------------------------------

def get_main_window():
    """
    Return the Qt Main Window.
    """
    app = QtWidgets.QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMainWindow):
            return widget
    return None

def center_widget(widget):
    """
    Center the given widget to the Qt Main Window.
    """
    main_window = get_main_window()
    if not main_window:
        return False

    #
    # compute a new position for the floating widget such that it will center
    # over the Qt application's main window
    #

    rect_main = main_window.geometry()
    rect_widget = widget.rect()

    centered_position = rect_main.center() - rect_widget.center()
    widget.move(centered_position)

    return True
