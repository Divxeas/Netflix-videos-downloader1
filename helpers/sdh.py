import codecs
import os
import re
import sys

import pysrt


class sdh_remover:
    def __init__(self,):
        self.__replace__ = "empty_line"
        self.content = []

    def cleanLine(self, line, regex):
        line = re.sub("</i>", "", line)
        line = re.sub("<i>", "", line)
        if re.search(r"\[(.*)?\n(.*)?\]", line):
            line = re.sub(
                re.search(r"\[(.*)?\n(.*)?\]", line).group(), self.__replace__, line
            )

        if re.search(r"\((.*)?\n(.*)?\)", line):
            line = re.sub(
                re.search(r"\((.*)?\n(.*)?\)", line).group(), self.__replace__, line
            )

        try:
            # is it inside a markup tag?
            match = regex.match(line).group(1)
            tag = re.compile("(<[A-z]+[^>]*>)").match(match).group(1)
            line = re.sub(match, tag + self.__replace__, line)
        except:
            try:
                line = re.sub(regex, self.__replace__, line)
            except:
                pass
        return line

    def _save(self, Output):

        file = codecs.open(Output, "w", encoding="utf-8")

        for idx, text in enumerate(self.content, start=1):
            file.write(
                "{}\n{} --> {}\n{}\n\n".format(
                    str(idx), text["start"], text["end"], text["text"].strip(),
                )
            )

        file.close()

    def clean(self):
        if not self.content == []:
            temp = self.content
            self.content = []

            for text in temp:
                if text["text"].strip() == self.__replace__:
                    continue
                text.update({"text": re.sub(self.__replace__, "", text["text"])})

                if not text["text"].strip() == "":
                    self.content.append(text)

        return

    def noHI(self, Input=None, Output=None, content=None):

        srt = pysrt.open(Input, encoding="utf-8")
        for idx, line in enumerate(srt, start=1):
            number = str(idx)
            start = line.start
            end = line.end
            text = line.text

            text = self.cleanLine(text, re.compile(r"(\[(.+)?\]|\[(.+)?|^(.+)?\])"))
            text = self.cleanLine(text, re.compile(r"(\((.+)?\)|\((.+)?|^(.+)?\))"))
            text = self.cleanLine(text, re.compile(r"(\[(.+)?\]|\[(.+)?|^(.+)?\])"))
            text = self.cleanLine(
                text,
                re.compile(r"([♩♪♫♭♮♯]+(.+)?[♩♪♫♭♮♯]+|[♩♪♫♭♮♯]+(.+)?|^(.+)?[♩♪♫♭♮♯]+)"),
            )
            text = self.cleanLine(text, re.compile(r"(<font[^>]*>)|(<\/font>)"))

            self.content.append(
                {"number": number, "start": start, "end": end, "text": text,}
            )

        self.clean()
        self._save(Output)
