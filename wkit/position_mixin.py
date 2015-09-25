import logging
from PyQt4.QtCore import QPoint

logger = logging.getLogger('wkit.position_mixin')


class PositionMixin(object):
    def qpoint_to_tuple(self, qpoint):
        return qpoint.x(), qpoint.y()

    def find_position(self, css):
        try:
            return self.find_all_positions(css)[0]
        except IndexError:
            logger.warning("Can't locate element " + (css or xpath))
            return None

    def find_all_positions(self, css=None, xpath=None):
        """Get the position of elements whose match selector
        @return: position of QPoint
        """
        if css:
            result = []
            for ele in self.page.mainFrame().findAllElements(css):
                if not ele.isNull():
                    result.append(ele.geometry().center())
            return result
        else:
            positions = self.evaluate(u"""
            function GetAbsoluteLocationEx(element)
            {
                if ( arguments.length != 1 || element == null )
                {
                    return null;
                }
                var elmt = element;
                var offsetTop = elmt.offsetTop;
                var offsetLeft = elmt.offsetLeft;
                var offsetWidth = elmt.offsetWidth;
                var offsetHeight = elmt.offsetHeight;
                while( elmt = elmt.offsetParent )
                {
                      // add this judge
                    if ( elmt.style.position == 'absolute' || elmt.style.position == 'relative'
                        || ( elmt.style.overflow != 'visible' && elmt.style.overflow != '' ) )
                    {
                        break;
                    }
                    offsetTop += elmt.offsetTop;
                    offsetLeft += elmt.offsetLeft;
                }
                return { absoluteTop: offsetTop, absoluteLeft: offsetLeft,
                    offsetWidth: offsetWidth, offsetHeight: offsetHeight };
            }
            result=[];
            for (var r = document.evaluate('%s', document, null, 5, null), n; n = r.iterateNext();) {
            pos=GetAbsoluteLocationEx(n)
            result.push([pos.absoluteLeft+pos.offsetWidth/2.0,pos.absoluteTop+pos.offsetHeight/2.0]);
            }
            result
            """ % query.replace("\'", "\\'"))

            return [QPoint(*tuple(x)) for x in positions]
