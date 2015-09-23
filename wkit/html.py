import re

RE_PRAGMA = re.compile(b'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
RE_CHARSET = re.compile(b'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
RE_XML_DECL = re.compile(b'^<\?xml.*?encoding=["\']*(.+?)["\'>]')


def find_document_encoding(content):
    for rex in (RE_PRAGMA, RE_CHARSET, RE_XML_DECL):
        try:
            return rex.search(content).group(1).decode('latin')
        except AttributeError:
            pass
    return None
