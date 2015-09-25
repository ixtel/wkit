import codecs


class JavaScriptMixin(object):
    #@can_load_page
    def evaluate(self, script):
        """Evaluates script in page frame.
        @param script: The script to evaluate.
        """
        result = self.page.mainFrame().evaluateJavaScript('%s' % script)
        return result

    def evaluate_js_file(self, path, encoding='utf-8'):
        """Evaluates javascript file at given path in current frame.
        Raises native IOException in case of invalid file.
        @param path: The path of the file.
        @param encoding: The file's encoding.
        """
        self.evaluate(codecs.open(path, encoding=encoding).read())
