# -*- coding: utf-8 -*-
import requests

import random
import re
import os

from textblob import TextBlob 
from textblob.tokenizers import SentenceTokenizer

from pattern.en import conjugate, lemma, lexeme
from pattern.en import tenses, PAST, PL, parse, pluralize, singularize

import pdfkit

concept_cache = {}

def simpler(word):
    return re.sub(r"^an? |^the |^your ","",word,flags=re.IGNORECASE)

def pastify(phrase):
    fixed = ''   
    found = 0
    blob = TextBlob("I would like to " + phrase)
    for w in blob.tags[4:]:
        if ("VB" in w[1] and found is 0):    
            if ("heat" in w[0]):
                fixed += "heated up "
            elif ("leave" in w[0]):
                fixed += "left "
            elif ("lose" in w[0]):
                fixed += "lost "
            else:
                fixed += conjugate(w[0],tense=PAST) + " "
            found = 1
        else:
            fixed += w[0] + " "
            
    return fixed

def specify(phrase):
    #print "\n"+phrase
    phrase = re.sub(r" an? | their | your | its | her | his "," the ",phrase)
    do = ''
    if (" the " not in phrase):
        # check for the direct object
        chunks = TextBlob("this is the thing that " + phrase)
        #print chunks
        for word in chunks.tags:
            
            if ("NN" in word[1]):
                
                # print "found the object"
                
                do = word[0]
                # print do
                #break        
        return phrase.replace(do,"the " + do,1)
        phrase = re.sub(do,"the " + do,phrase)
    return phrase

def get_some(word,rel,direction,number):
    global concept_cache
    
    if (word in concept_cache.keys()):
        # print "getting concept from cache..."
        return concept_cache[word]
    else:
        # eg 
        url = 'http://api.conceptnet.io/query?node=/c/en/' + word + '&rel=/r/' + rel + '&limit='+number
        #objects = requests.get('http://api.conceptnet.io/query?node=/c/en/' + word + '&rel=/r/' + rel + '&limit='+number).json()
        objects = requests.get(url).json()

        #print "getting: " + url
        things = []
        for thing in objects['edges']:
            directions = simpler(thing[direction]['label']).lower()
            #print directions
            #end = simpler(thing['end']['label']).lower()

            if (simpler(word) not in directions):
                things.append(directions)
        
        concept_cache[word] = things
        
    return things

def stack(seed,depth):
    db = []
    completed = []
    
    for d in range(depth):
        
        print "Depth is now " + str(d) + " and the db is at " + str(len(db))
        
        if (d is 0):
            actions = get_some(seed,"CapableOf","end","1000")
            
            # get some actions
            for act in actions:
                blob = TextBlob(seed + " can " + act)
      
                # make sure that there's a verb besides "is"
                pos = []
                for w in blob.tags:
                    if (not re.match("be",lemma(w[0]))):
                        pos.append(w[1]) 
                
                if (re.match(blob.tags[-1][1],"NN") and "VB" in pos):
                    # print "Adding " + act
                    db.append([act])
            #print db
        else:
        
            threadsnap = len(db)
            
            #print "DB length is " + str(threadsnap)
            #print db
            for s in range(threadsnap):
                #row = db[s]
                thread = db[s][d - 1]
                #print "Working on " + str(thread)
                
                seed = thread.split(" ")[-1]
 
                new_tails = []
      
                if (len(seed) > 0 and seed not in 'house'):
                    actions = get_some(seed,"CapableOf","end","1000")
                    for act in actions:
                        blob = TextBlob(seed + " can " + act)
                        pos = []
                        for w in blob.tags:
                            if (not re.match("be",lemma(w[0]))):
                                pos.append(w[1])

                        if (re.match(blob.tags[-1][1],"NN") and "VB" in pos and act not in db[s]):
                            # add it
                            #print "A new tail action: " + act
                            new_tails.append(act)
                        
                if (len(new_tails) > 0):  
                    row = list(db[s])     
                        
                    for n in range(len(new_tails)):
                        if (n > 0):
                            # the new phrase is new_tails[n]
                            
                            new_row = list(row)
                            new_row.append(new_tails[n])
                            db.append(new_row)
                        else:
                            db[s].append(new_tails[0])                 
                else:
                    if (len(db[s]) <= d):
                        db[s].append("")
                    else:
                        db[s][d] = ""
                        
        # right here, do some clean up. 
        
        print "Before cleanup, db is at " + str(len(db))
        
        cull = []
        
        for c in range(len(db)):
            
            # save any that end in houses
            if ("house" in db[c][-1].split(" ")[-1]):
                completed.append(db[c])
                cull.append(c)
            
            # trim out any that have died
            if (len(db[c][-1].split(" ")[-1]) is 0):
                cull.append(c)
            
           
        db = [v for i, v in enumerate(db) if i not in cull]
        
        trim = []
        for r in range(len(db) - 50):
            totrim = random.randrange(0,len(db))        
            while (totrim in trim):
                totrim = random.randrange(0,len(db))
            trim.append(totrim)
            
        db = [v for i, v in enumerate(db) if i not in trim]
        
        print "After cleanup, db is at " + str(len(db))
            
    return completed

def prepare():
    ordered = list(result[-1][::-1])
    chapter = ''
    ordered.append("the tiger")
    colors = ["#cf3e27","#0d8a89","#066598","#ff9800","#e68900"]
    for page in range(len(ordered)):
        
        template = open('template.html')
        lines = template.readlines()
        template.close()
        
        page_number = str(page + 1)
        
        the_concept = pastify(specify(ordered[page]))
        
        # isolate the current object
        the_thing = the_concept.split(" the ")[-1]
        
        
  
        if (page == 0):
            next_concept = ""
            chapter = "that Jack built."
        else:
            color = random.choice(colors)
            next_concept = "<span style=\"color:" + color + "\"> that " + pastify(specify(ordered[page - 1])) + "</span>"
        
        #print "\n\nThis is the " + the_thing + next_concept
        #print chapter
        
        gen = open( "pages/" + page_number + ".html", 'w' )
        for l in lines:
            li = l.replace("{{{pn}}}",page_number).replace("{{{chapter_content}}}",chapter).replace("{{{first_line}}}","This is the <span class='page-object'>" + the_thing + "</span>" + next_concept)
            gen.write(li)
            
        gen.close()
        
        chapter = next_concept + chapter
        
def get_icons(keyword):
    
    # first check the cache
    if (os.path.isfile("icons/" + keyword + ".json")):
        #print "Loading from file"
        # proceed to load it from file
        
        icon_file = open("icons/" + keyword + ".json").read()
        icons = json.loads(icon_file)
        #icon_file.close()
        
    else:
        #print "Getting from API"
        # set up nounproject auth
        auth = OAuth1("da866a7951e24154b918294bd9223304", "072eca50d5dc47d3a98375e6ef54a434")

        # the api endpoint
        endpoint = "http://api.thenounproject.com/icons/{}".format(keyword)

        response = requests.get(endpoint, auth=auth)
        
        icons = response.json()
        
        with open("icons/" + keyword + ".json","w") as outfile:
            json.dump(data, outfile)
        
    return icons        
        