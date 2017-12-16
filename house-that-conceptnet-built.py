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

from weasyprint import HTML

from PIL import Image
concept_cache = {}
credits = {
        'nouns':[],
        'houses':[],
        'characters':[],
        'concepts':[],
        'raw_txt':'',
        'chapter_count':2,
        'chapter_titles':[],
        'character_icons':[]
    }

def contrib(sources):
    contributors = []
    for c in sources:
        contributors.append(c['contributor'].split("/")[-1])
    return contributors

def pal():
    palettes = [
        ["cf3e27","0d8a89","066598","ff9800","e68900"],
        ["25CAF7","BEF272","f9fa96","F89573","F44750"],
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
            elif ("bite" in w[0]):
                fixed += "bit "
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
                
                if (re.match(blob.tags[-1][1],"NN") and "VB" in pos and act[0].split(" ")[0] not in ['to','near'] ):
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

                        if (re.match(blob.tags[-1][1],"NN") and "VB" in pos and act not in db[s] and act[0].split(" ")[0] not in ['to','near'] ):
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
        photo_info = flickr.photos.getInfo(photo_id=photo['id'])
        #license = flickr.photos.getInfo(photo_id=photo['id'])['photo']['license']
        #owner = flickr.photos.getInfo(photo_id=photo['id'])['photo']['owner']['username']
        print photo_info
        if(len(photo_info['photo']['owner']['realname']) > 0):
            photog = photo_info['photo']['owner']['realname']
        else:
            photog = photo_info['photo']['owner']['username']
        
        credits['houses'].append((photo['id'],photo_info['photo']['license'],photog,photo_info['photo']['title']['_content'],photo_info['photo']['urls']['url'][0]['_content']))
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
                #print "get = " + get
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
                os.system("convert images/" + icon['id'] + ".png " + "-fuzz 90% -fill \"#" + color + "\" -opaque black " + color_fn)
    
    top = "%.1f" % random.uniform(-0.5,7.0)
    left = "%.1f" % random.uniform(-0.5,7.0)
    width = "%.1f" % random.uniform(0.2,2.8)
    rotation = "%.1fdeg" % random.uniform(-30,30)
    
    position = "top:" + top + "in;" + "left:" + left + "in;"
    
    return u'<img src=\"../' + color_fn + '\" class=\"' + keyword + '\" style=\"transform:rotate(' + rotation + ');position:absolute;width:' + width + 'in;' + position + '\" />'

def a(phrase):
    if (re.search(r" the [aeiou]",phrase)):
        new_phrase = phrase.replace(" the ", " an ").replace(" for an "," for ")
    else:
        new_phrase = phrase.replace(" the ", " a ").replace(" for a "," for ").replace(" a water"," water").replace(" a sun"," the sun")
        
    return new_phrase

def book_title ():
    global credits
    people = list(credits['characters'])
    people[-1] = "and " + people[-1]
    return "The " + quantify("house",amount=len(credits['chapter_titles'])) + " of " + ", ".join(people)
    
def prepare_chapter(content,startpage,chapter_number):
    
    global credits
    
    
    print content
    # put the list from stack() in reverse
    ordered = list(content[::-1])
    
    # this will hold the chapter text as it accumulates
    chapter = ''
    
    # this chooses a color palette for this chapter
    colors = pal()
       
    # pick a name for our main character
    jack = random.choice(pycorpora.get_file("humans","firstnames")['firstNames'])
    credits['characters'].append(jack)
    
    # get an image for this character
    jack_icon_first = get_icon(jack,random.choice(colors),random.choice(["man","girl","boy","woman","baby","child","grandmother","dude"]))
    
    jack_icon = re.sub(r"style=\".+?\"","",jack_icon_first)

    credits["character_icons"].append(jack_icon_first)
    
    # chapter object 
    chapter_object = content[0]

    
    # make a chapter title
    # this will make a title for the chapter
    chapter_title = str( jack + 
                        " and the " + 
                        str(chapter_object) + 
                        " that " + 
                        a(specify(pastify(content[1][0]))) )
    
    credits['chapter_titles'].append((chapter_title, startpage + 3))
    # loop through each concept in the stack
    for page in range(len(ordered)):
        
        print "Working on page " + str(page)
        
        
        # the page number
        page_number = str( startpage + ((page * 2) + 2) )
        
        # a color for this concept
        color = random.choice(colors)
        
        # I don't remember what this does but it's probably important later
        if (page == len(ordered) - 1):            
            the_concept = chapter_object
        else:
            the_concept = pastify(specify(ordered[page][0]))
            
            
        # isolate the current object
        the_thing = the_concept.split(" the ")[-1]
        
        # find an icon. This returns an <img> tag for the icon
        the_icon_first = get_icon(the_thing,color)
        the_icon = re.sub(r"style=\".+?\"","",the_icon_first)
        
        if (page == 0): # at the beginning of the chapter
            
            
            # make the blank page
            tpl("templates/template.html", "pages/" + str(startpage).zfill(5) + "l.html",[])
            
            # make the chapter title page 
            print "Making the title page "
            tpl("templates/chaptertitlepage.html",
                "pages/" + str(startpage + 1).zfill(5) + "r.html",
                [("chapter_number",str(chapter_number)),("chapter_title",chapter_title),("character_name",jack),("character_icon",str(jack_icon))])

            next_concept = ""
            # start the chapter string
            chapter = "that " + jack + " " + random.choice(["built.","built.","built.","built.","built.","built.","built.","built of brick.","divided into several rooms.","found in a neighborhood.","located on an estate."])
        else:
            # I don't know why this is going backwards?
            next_concept = "<span> that " + pastify(specify(ordered[page - 1][0])).split(" the ")[0] + " the </span>"
    
        page_content = [
            ("pn",str(int(page_number) - 6)),
            ("chapter_content",chapter),
            ("icon",the_icon),
            ("first_line","This is the <span class='page-object' style='color:#" + color + "'>" + the_thing + "</span>" + next_concept)      
        ]
        
        tpl("templates/template.html","pages/" + page_number.zfill(5) + "l.html",page_content)
        
        
        if (page == 0):           
            if (not os.path.isfile("images/house-" + str(chapter_number) + "-watercolor.jpg")):
                get_flickr_image("house",chapter_number)
                
            tpl("templates/rtemplate.html","pages/" + str(int(page_number) + 1).zfill(5) + "r.html",[("imagery",jack_icon_first + "<!-- imagery -->"),("pgbackground","<div class='pg' style='background-image: url(../images/house-" + str(chapter_number) + "-watercolor.jpg)'>")])
        elif (page >= 1):
            tpl ("pages/" + str(int(page_number) - 1).zfill(5) + "r.html",  "pages/" + str(int(page_number) + 1).zfill(5) + "r.html",[("imagery",the_icon_first + "<!-- imagery -->")])
        
        # prepend the next_concept variable to the chapter text before it loops again
        chapter = "<span class='page-object' style='color:#" + color + "'>" + the_thing + "</span>" + next_concept + chapter
        #raw_txt = str(chapter)
        raw_txt = re.sub('<[^<]+?>', '', chapter)
        credits['raw_txt'] += " This is the " + raw_txt
        
    return page_number
        
def assemble():
    # actually make the thing
    global credits
    credits = {
        'nouns':[],
        'houses':[],
        'characters':[],
        'concepts':[],
        'raw_txt':'',
        'chapter_count':7,
        'chapter_titles':[],
        'character_icons':[]
    }
    

    page_counter = 6
    # first, make the chapters
    animals = pycorpora.get_file("animals","common")['animals']
    
    
    for chapter_counter in range(credits['chapter_count']):
        result = 0
        while (result == 0):
            animal = random.randrange(0,len(animals))
            result = stack(animals[animal], 55)
            del animals[animal]
            
        
        a_chapter = prepare_chapter(result,int(page_counter) + 2,int(chapter_counter) + 1)
        page_counter = a_chapter
        
        # to make a chapter
        
        # pick an animal to stack
        
        # make sure it created a valid set
        
        # prepare_chapter should return a number, the next chapter should start two pages after, so 10 + 2 = 12, e.g.
        
        
    # prepare the frontmatter
    # 1r = frontcover
    # 2l = blank
    # 3r = title page
    # 4l = dedication
    # 5r = toc
    # 6l = blank
    # 7r = introduction
    # 8l = blank, chapter 1 page 0
    
    booktitle = book_title()
    print "This book is called " + booktitle
    
    tpl("templates/frontcover.html","pages/00001r.html",[("book_title",booktitle)])
    
    # blank page
    tpl("templates/template.html","pages/00002l.html",[("","")])
    
    # title page
    tpl("templates/titlepage.html","pages/00003r.html",[("book_title",booktitle)])
    
    # dedication page
    kid_icons = '<div id="kids">'
    for kid in ["Cecily","Daniel","Serena","Wendy"]:
        a_kid = re.sub(r"style=\".+?\"","",get_icon(kid,"333333"))
        kid_icons += a_kid
    kid_icons += "</div>"
    tpl("templates/dedication.html","pages/00004l.html",[("kids",kid_icons)])
    
    # toc -- this one has to be a bit more manual
    toc = ''
    for ch in range(len(credits['chapter_titles'])):
        toc_string = '<div class="toc-entry"><span>Chapter ' + str(ch + 1) + '</span><span>' + credits['chapter_titles'][ch][0] + '</span><span>' + str(credits['chapter_titles'][ch][1] - 8) + '</span></div>'                  
        toc += toc_string
        
    toc += '<div class="toc-entry"><span>&nbsp;</span><span>Credits</span><span>' + str(int(page_counter) - 3) + '</span></div>'
    tpl("templates/toc.html","pages/00005r.html",[("toc",toc)])
    
    # blank page
    tpl("templates/template.html","pages/00006l.html",[("","")])
     
    # introduction
    housecount = quantify("house",amount=len(credits['chapter_titles']))
    peoplecount = quantify("person",amount=len(credits['characters']))
    
    tpl("templates/preface.html","pages/00007r.html",[("house_count",housecount),("people_count",peoplecount),("character_names", ", ".join(list(credits['characters']))),("word_count",str(len(re.compile(r" +").split(credits['raw_txt']))))])
    
    # make a The End
    tpl("templates/last_page.html","pages/" + str(int(page_counter) + 2).zfill(5) + ".html",[("character_names", ", ".join(list(credits['characters'])))]) 
    
    tpl("templates/the_end.html","pages/" + str(int(page_counter) + 3).zfill(5) + ".html",[("character_icons"," ".join(list(credits['character_icons'])))])

    # make the credits
    make_credits(credits,str(int(page_counter) + 2))
    
    print "Generation complete"

def make_credits(credits,page_number):
    
    # actually first make a blank verso page
    tpl("templates/credits.html","pages/" + str(int(page_number) + 2).zfill(5) + ".html",[("","")])
    
    
    license = {
        '4': 'CC BY',
        '5': 'CC BY-SA',
        '9': 'CC 0',
        '10': 'Public Domain'
    }
    house_cred = ''
    # first the houses
    for h in credits["houses"]:
        house_cred += "<div class='housecred'>\"" + h[3] + "\" by Flickr User " + h[2] + " " + license[str(h[1])] 
        house_cred += "<br/><u>" + h[4] + "</u></div>"
        
    house_credit_content = [
        ("credits_header","<h2>Credits</h2>"),
        ("credits_content","<h3>Houses</h3>" + house_cred.encode('utf-8')),
        ("page_number",str(int(page_number) - 5))
    ]
    tpl("templates/credits.html","pages/" + str(int(page_number) + 3).zfill(5) + ".html",house_credit_content)
    
    
    # then the noun icons in pages with two 25-item columns
    # each is a tuple of an id and a attribution line
    nounlist = credits['nouns']
    chunked = [nounlist[i:i + 50] for i in xrange(0,len(nounlist),50)]
    
    for chunk in range(len(chunked)):
        chunk_counter = 1
        chunk_string = ''
        for noun in chunked[chunk]:
            noun_string = "<div class='noun-credit'><img src='../images/" + noun[0].encode('utf-8') + ".png' /><span> " + noun[1].encode('utf-8') + "</span></div>"
            chunk_string += noun_string
            
        this_header = "<h3>Icons</h3>"
        if (chunk >= 1):
            this_header = "<h3>Icons (continued)</h3>"
            
        tpl("templates/credits.html","pages/" + str(int(page_number) + chunk + 4).zfill(5) + ".html",[("credits_header",this_header),("credits_content",chunk_string),("page_number",str(int(page_number) + chunk - 2))])
        
    # finally all the concepts
    contributors = {}
    for c in credits['concepts']:
        for contributor in c:
            contributors[contributor] = ' '
            
    con_string = ", ".join(contributors.keys())
    
    tpl("templates/credits.html","pages/" + str(int(page_number) + chunk + 5).zfill(5) + ".html",[("page_number",str(int(page_number) - 1)),("credits_header","<h3>Concepts</h3>"),("credits_content","<p>" + con_string + "</p>")])
    
def chunk(thelist,size):
    nouncredits = {}
    for n in thenouns:
        nouncredits[n[0]] = n[1]
    for i in range(0, len(thelist),50):
        yield l[i:i + n] 

def make_pdf():
    print "Making PDF "
    pages = glob.glob("pages/*.html")
    
    print "Converting individal pages "
    
    for p in pages:
            
        pn = p.split("/")[-1].split(".")[0]
        nf = "pdfs/"+ pn.zfill(5) + ".pdf"
        
        HTML(p).write_pdf(nf)
    
    print "Combining them all "
    
    os.system("pdftk pdfs/*.pdf cat output output.pdf")
    
    print "I think it's done!"
    
assemble()
make_pdf()
#get_icon("water","red")