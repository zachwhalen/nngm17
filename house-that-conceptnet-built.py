# -*- coding: utf-8 -*-
import requests

import random
import re
import os
import json
import glob
import urllib
from requests_oauthlib import OAuth1
import flickrapi
import pycorpora
from textblob import TextBlob 
from textblob.tokenizers import SentenceTokenizer

from pattern.en import conjugate, lemma, lexeme
from pattern.en import tenses, PAST, PL, parse, pluralize, singularize, quantify

import pdfkit

from PIL import Image
concept_cache = {}
credits = {
        'nouns':[],
        'houses':[],
        'characters':[],
        'concepts':[],
        'raw_txt':'',
        'chapter_count':2,
        'chapter_titles':[]
    }

def contrib(sources):
    contributors = []
    for c in sources:
        contributors.append(c['contributor'].split("/")[-1])
    return contributors

def pal():
    palettes = [
        ["cf3e27","0d8a89","066598","ff9800","e68900"],
        ["25CAF7","BEF272","F8FA68","F89573","F44750"],
        ["EA9155","EFB53A","C54400","B0946F","5D443F"],
        ["820434","C84622","F6871E","F3B778","2D132E"],
        ["1E2C45","A1531B","D9B32B","A11B1B","250433"]
    ]
    
    return random.choice(palettes)

def cred():
    cred = {}
    f = open("credentials")
    lines = f.readlines()
    for l in lines:
        l = l.rstrip()
        cred[l.split(" = ")[0]] = l.split(" = ")[1] 
    return cred

def tpl(template_file,outfile,data):
    # data should be a list of tuples
    
    if os.path.isfile(outfile):
        os.unlink(outfile)
    f = open(template_file)
    lines = f.readlines()
    f.close()
    
    for l in lines: 
        for token in data: 
#             print "token0 is " + token[0]
#             print "token1 is " + token[1]
            l = l.replace("<!-- " + token[0] + " -->",token[1])
        g = open(outfile,"a")

        g.write(l)
        f.close()
   
    return True

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
            elif ("lie" in w[0]):
                fixed += "lay "
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
                contributors = contrib(thing['sources'])
                things.append((directions,contributors)) # make this a tuple
        
        concept_cache[word] = things
        
    return things

def stack(seed,depth):
    db = []
    completed = []
    og = seed
    
    for d in range(depth):
        
        print "Depth is now " + str(d) + " and the db is at " + str(len(db))
        
        if (d is 0):
            actions = get_some(seed,"CapableOf","end","1000")
            
            # get some actions
            for act in actions:
                blob = TextBlob(seed + " can " + act[0]) # adjust for tuple here
      
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
                
                seed = thread[0].split(" ")[-1]
 
                new_tails = []
      
                if (len(seed) > 0 and seed not in 'house'):
                    actions = get_some(seed,"CapableOf","end","1000")
                    for act in actions:
                        blob = TextBlob(seed + " can " + act[0]) # adjust for tuple here
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
            if (len(db[c][-1]) > 0):
                # save any that end in houses
                if ("house" in db[c][-1][0].split(" ")[-1]):
                    completed.append(db[c])
                    cull.append(c)
            else:
                cull.append(c)

#             # trim out any that have died
#             if (len(db[c][-1][0].split(" ")[-1]) is 0):
#                 cull.append(c)
            
           
        db = [v for i, v in enumerate(db) if i not in cull]
        
        trim = []
        for r in range(len(db) - 50):
            totrim = random.randrange(0,len(db))        
            while (totrim in trim):
                totrim = random.randrange(0,len(db))
            trim.append(totrim)
            
        db = [v for i, v in enumerate(db) if i not in trim]
        
        print "After cleanup, db is at " + str(len(db))
    
    # pick one of the longest complete chains, prepend the seed, and return 
    if (len(db) > 0 and len(completed) > 0):
        content = completed[-1]

        # add to the credits here with information from tuple
        for c in content:
            credits['concepts'].append(c[1])
        content.insert(0,str(og))
        return content
    else:
        return 0

def get_icons(noun,fallback):
    save_as = ""
    keyword = re.sub(r" $","",noun)
    # first check the cache
    if (os.path.isfile("icons/" + keyword.replace(" ","+") + ".json")):
        print "Loading from file"
        # proceed to load it from file
        
        icon_file = open("icons/" + keyword.replace(" ","+") + ".json").read()
        icons = json.loads(icon_file)
        #icon_file.close()
        save_as = keyword
    
    elif (os.path.isfile("icons/" + keyword.split(" ")[-1] + ".json")):
        icon_file = open("icons/" + keyword.split(" ")[-1] + ".json").read()
        icons = json.loads(icon_file)
        save_as = keyword.split(" ")[-1]
    else:
        print "Getting from API"
        # set up nounproject auth
        credentials = cred()
        auth = OAuth1(credentials['noun_key'],credentials['noun_secret'])
 
        # the api endpoint
        endpoint = "http://api.thenounproject.com/icons/" + urllib.quote(keyword)
        
       
        response = requests.get(endpoint, auth=auth)
        print response.status_code
        if ("404" not in str(response.status_code)):
            icons = response.json()
            save_as = keyword
        elif (len(keyword.split(" ")) > 1):
            # try again
            # should put a file check in here
            endpoint = "http://api.thenounproject.com/icons/" + urllib.quote(keyword.split(" ")[-1])
            response = requests.get(endpoint, auth=auth)
            
            if ("404" not in str(response.status_code)):
                icons = response.json()
                save_as = keyword.split(" ")[-1]
            else:
                icons = json.loads("icons/object.json")
                save_as = "object"
                
        else:
#             icons = json.loads("icons/thing.json")
#             save_as = "thing"
            icons = get_icons(fallback,fallback)
            save_as = fallback
            
        with open("icons/" + save_as.replace(" ","+") + ".json","w") as outfile:
            json.dump(icons, outfile)
            
    return icons
     

def get_flickr_image(keyword,chapter_number):
    
    new_fn = 'images/' + keyword + '-' + str(chapter_number) + '-watercolor.jpg'
    if (not os.path.isfile(new_fn)):
    
        credentials = cred()
        api_key = credentials['flickr_key']
        api_secret = credentials['flickr_secret']

        flickr = flickrapi.FlickrAPI(api_key, api_secret,format="parsed-json")
        photos = flickr.photos.search(text=keyword,license='4,5,9,10',sort="relevance",per_page='300')
        photo = random.choice(photos['photos']['photo'])
        license = flickr.photos.getInfo(photo_id=photo['id'])['photo']['license']
        owner = flickr.photos.getInfo(photo_id=photo['id'])['photo']['owner']['username']
        credits['houses'].append((photo['id'],license,owner))
        fullsize = flickr.photos.getSizes(photo_id=photo['id'])['sizes']['size'][-1]['source']
        fn = fullsize.split("/")[-1]
        iid = fn.split(".")[0]
        #new_fn = fn.split(".")[0] + "-watercolor.jpg"

        os.system("wget -P images " + fullsize)
        # convert images/larger-flickr.jpg -resize "800x800^" -gravity center -crop 800x800+0+0 +repage -brightness-contrast 50x0 images/smaller-flickr.jpg

        os.system("convert images/" + fn + " -resize \"800x800^\" -gravity center -crop 800x800+0+0 +repage -brightness-contrast 50x0 images/" + fn)
        os.system("./watercolor -s 25 -e 5 -m 50 -c 0 images/" + fn + " " + new_fn)
    return new_fn

def get_icon(keyword,color,fallback="thing"):
    global credits
    icons = get_icons(keyword,fallback)
    #print icons
    
    icon_url = 0
    while(not icon_url):
        icon = random.choice(icons['icons'])
        
        if ("attribution_preview_url" in icon):
            print "has png"
            icon_url = icon['attribution_preview_url']
            
            credits['nouns'].append((icon['id'],icon['attribution']))
            
            # do I already have this one?
            if (not os.path.isfile("images/" + icon['id'] + ".png")):
                # save it
                get = os.system("wget -P images/ -O images/" + icon['id'] + ".png " + icon_url)

                # crop it
                img = Image.open("images/" + icon['id'] + ".png")
                t = img.crop((0,0,700,600))
                t.save("images/" + icon['id'] + ".png")
            
            # do I have the right color?
            color_fn = "images/" + icon['id'] + "-" + color + ".png"
            print "The colorized file name should be " + color_fn
            if (not os.path.isfile(color_fn)):
                # convert 8668.png -fuzz 100% -fill "#e68900" -opaque black test.png
                print "coloring the icon "
                os.system("convert images/" + icon['id'] + ".png " + "-fuzz 100% -fill \"#" + color + "\" -opaque black " + color_fn)
    
    top = "%.1f" % random.uniform(-0.5,7.0)
    left = "%.1f" % random.uniform(-0.5,7.0)
    width = "%.1f" % random.uniform(0.2,2.8)
    rotation = "%.1fdeg" % random.uniform(-30,30)
    
    position = "top:" + top + "in;" + "left:" + left + "in;"
    
    return u'<img src=\"../' + color_fn + '\" class=\"' + keyword + '\" style=\"transform:rotate(' + rotation + ');position:absolute;width:' + width + 'in;' + position + '\" />'

def a(phrase):
    if (re.search(r" the [aeiou]",phrase)):
        new_phrase = phrase.replace(" the ", " an ")
    else:
        new_phrase = phrase.replace(" the ", " a ")
    return new_phrase

def book_title ():
    global credits
    people = list(credits['characters'])
    people[-1] = "and " + people[-1]
    return "The " + quantify("house",amount=len(credits['chapter_titles'])) + " of " + ", ".join(people)
