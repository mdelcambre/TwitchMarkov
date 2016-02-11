#!/usr/bin/env python
"Loads all the files and DB information to create the text to markovify"

import markovify
import psycopg2
from secrets import *

DB_CONN = psycopg2.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password'],
        database=db_config['db']
)

def main():
    model = MarkovCombiner()
    model.load_textfile('text_files/trunc_kjb.txt')
    model.load_twitch_channel(('professorbroman', 'kinggothalian'))
    print(model.make_sentence(140))


class MarkovCombiner:

    def __init__(self, state=3):
        self.sources = []
        self.state = 3
        pass

    def add_text(self, text, pre_cleaned=False):
        if not pre_cleaned:
            clean = self._clean_text(text)
        else:
            clean = text
        self.sources.append(clean)
        self._update_model()

    def _update_model(self):
        self.model = markovify.Text(
                '. '.join(self.sources),
                state_size=self.state
            )

    def _clean_text(self, text):
        clean_text = ''
        for line in text.splitlines():
            clean = self._clean_line(line)
            if clean:
                clean_text += clean
        return clean_text

    def _clean_line(self, line):
        "Takes a line and cleans it up, filters some lines out"
        line = line.strip()
        # filter bad lines
        if 'http' in line:
            return False
        if line.startswith(('!', '@')):
            return False
        if len(line.split(' ')) < 3:
            return False
        #make sure it ends with punctuation
        if not line.endswith((".", "?", "!")):
            line += "."
        return line


    def load_twitch_channel(self, channel, stop=False):
        "Loads the comments from a specific channel with certain rules"
        text = ''
        # if we are passed a list, combine the  comments with recursion
        if hasattr(channel, '__iter__') and not stop:
            for sub in channel:
                # limit to one level deep with stop = True
                text += self.load_twitch_channel(sub, stop=True)
            self.add_text(text, pre_cleaned=True)
            return True
        # we must have a single channel, so lets do this
        cur = DB_CONN.cursor()
        cur.execute("""SELECT comment
            FROM comments AS c
            INNER JOIN log AS l ON l.comment_id = c.id
            INNER JOIN channels as ch ON l.channel_id = ch.id
            INNER JOIN users AS u ON l.user_id = u.id
            WHERE NOT u.name =  'twitchnotify'
            AND NOT u.name LIKE '%%bot'
            AND NOT u.name = ch.channel
            AND ch.channel = %s
            GROUP BY comment""", (channel, ))
        for row in cur:
            line = self._clean_line(row[0])
            if line:
                text += line + ' '
        # if we are in recursion, return
        if stop:
            return text
        # otherwise add the text
        self.add_text(text, pre_cleaned=True)

    def load_textfile(self, path):
        "Loads the bungie weekly update / this week at bungie"
        text = ''
        with open(path) as f:
            for line in f:
                clean = self._clean_line(line)
                if clean:
                    text += clean + ' '
        self.add_text(text, pre_cleaned=True)

    def make_sentence(self, count, **kwargs):
        # make a list of sets of sources.
        src_sets = [set(src.split()) for src in self.sources]
        # try to make a sentence 1000 times
        for tries in range(1000):
            sentence = self.model.make_short_sentence(
                    count,
                    **kwargs
                )
            # Get rid of senteces that have multiple senteces
            #They typical are bad
            if '.' in sentence:
                continue
            # create a list of bools that correspon to the srouces.
            # this keeps track of which sets the sentence have words soley from
            in_srcs = [False for src_set in src_sets]
            for word in sentence.split():
                # create a list of bools that tracks which sets a word is in.
                word_fnd = [word in src for src in src_sets]
                # if a word is only in one set, then add that to the in srcs.
                if sum(bool(a) for a in word_fnd) == 1:
                    in_srcs = [ a | b for a, b in zip(in_srcs, word_fnd)]
                    # if all srcs have a word only from that set, return
                    if all(in_srcs):
                        return sentence
        # we failed.
        return False

if __name__ == "__main__":
    main()
