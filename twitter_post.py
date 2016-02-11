#!/usr/bin/env python
"Loads all the files and DB information to create the text to markovify"

from secrets import *
import twitter
from markov import MarkovCombiner

API = twitter.Api(
        consumer_key=twit_cfg['c_key'],
        consumer_secret=twit_cfg['c_sec'],
        access_token_key=twit_cfg['t_key'],
        access_token_secret=twit_cfg['t_sec']
)

def main():
     model = MarkovCombiner()
     model.load_textfile('text_files/trunc_kjb.txt')
     model.load_twitch_channel(('professorbroman', 'kinggothalian'))
     API.PostUpdate(model.make_sentence(140))


if __name__ == "__main__":
    main()
