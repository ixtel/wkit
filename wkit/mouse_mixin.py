from PyQt4.QtTest import QTest
from PyQt4.QtCore import QPoint
from PyQt4.Qt import Qt

from wkit.logger import log_errors


class MouseMixin(object):
    #@can_load_page
    #@have_a_break
    def click(self, css):
        qpoint = self.find_position(css)
        if qpoint is not None:
            return self.qpoint_to_tuple(self._click_position(qpoint))

    #@have_a_break
    def move_to(self, css):
        qpoint = self.find_position(css)
        if qpoint is not None:
            self._move_to_position(qpoint)
            return qpoint_to_tuple(qpoint)

    def move_at(self, x, y):
        return self._move_to_position(QPoint(x, y))

    # ***************
    # Private methods
    # ***************

    #@can_load_page
    def _click_position(self, qpoint):
        self._move_page_center_to(qpoint)
        self.view.repaint()
        pos = qpoint - self.page.mainFrame().scrollPosition()

        self._move_to_position(pos)
        QTest.mouseClick(self.view, Qt.LeftButton, pos=pos)
        self.sleep(1) # Why?
        return pos


    def _move_to_position(self, qpoint):
        QTest.mouseMove(self.view, pos=qpoint)
        return qpoint

    def _move_page_center_to(self, qpoint):
        size = self.page.viewportSize()
        self.page.mainFrame().setScrollPosition(
            qpoint - QPoint(size.width(), size.height()) / 2)
