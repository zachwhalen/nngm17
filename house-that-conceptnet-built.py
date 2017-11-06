# -*- coding: utf-8 -*-
import requests
import random
import re
from textblob import TextBlob 

from pattern.en import conjugate, lemma, lexeme
from pattern.en import tenses, PAST, PL, parse, pluralize, singularize

def us(word):
    word = re.sub(r"^[aA]n? ","",word)
    return word.replace(' ','_')

def get_some(word,rel,number):
    objects = requests.get('http://api.conceptnet.io/query?node=/c/en/' + word + '&rel=/r/' + rel + '&limit='+number).json()
    return objects

def get_a(word,rel):
    stuff = get_some(word,rel,'50')
    choice = random.choice(stuff['edges'])
    start = singularize(re.sub(r"^[aA]n? |[tT]he ","",choice['start']['label'],flags=re.IGNORECASE))
    end = singularize(re.sub(r"^[aA]n? |[tT]he ","",choice['end']['label'],flags=re.IGNORECASE))   
    if (start.find(word.lower()) == 0):
        return end
    else:
        return start

def past_tense(phrase):
    blob = TextBlob("thing that can " + phrase)
    past_phrase = ''
    
    for word in (blob.tags[3:]):
        new_word = word[0]
        if (re.match(r"VBP?Z?",word[1])):
            new_word = conjugate(word[0],tense=PAST)
        past_phrase += new_word + " "    
    return past_phrase
    
# get some house stuff
stuff = get_some('bed','AtLocation','15')

# pick one thing
thing = random.choice(stuff['edges'])['start']['label']

# what did Jack do to the house?
built = get_a('house','ReceivesAction')

# what did the thing do?
lay = past_tense( get_a(us(thing),'CapableOf') )

print thing + " that " + lay + " in the house that Jack " + built

