#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os, time
import re
import codecs

import pywikibot
from pywikibot import pagegenerators
from pprint import pprint

import logging

def existingClaimFromYear(item, year, mon, day):
    try:
        claims = item.claims['P1082']
        time_str = pywikibot.WbTime(year=year, month=mon, day=day).toTimestr()
        for claim in claims:
            if ('P585' in claim.qualifiers):
                for qualifier_value in claim.qualifiers['P585']:
                    if (qualifier_value.getTarget().toTimestr() == time_str):
                        return claim
    except KeyError:
        pass
    return None
    

def addPopData(site, atvk_id, name, pop):
    
    source_url = 'http://data.csb.gov.lv/pxweb/en/Sociala/Sociala__ikgad__iedz__iedzskaits'
    #population record date
    pop_day = 1
    pop_mon = 1
    pop_year = 2017
    #data access date
    access_day = 11
    access_mon = 9
    access_year = 2017
    
    sparql = "SELECT ?item WHERE { ?item wdt:P1115 '%s' . } LIMIT 1" % (atvk_id, )
    wd_pages = pagegenerators.WikidataSPARQLPageGenerator(sparql, site=wikidata)
    wd_pages = list(wd_pages)
    ##pprint( wd_pages )
    repo = site ##data repo
    
    for wd_page in wd_pages:

        if wd_page.exists():
            dictionary = wd_page.get()
            ## pprint( dictionary )
            ###if 'etwiki' in wd_page.sitelinks:
            pprint( wd_page )

            if not existingClaimFromYear(wd_page, pop_year, pop_mon, pop_day):
                time.sleep(10)
                
                population_claim = pywikibot.Claim(repo, 'P1082')
                population_claim.setTarget(pywikibot.WbQuantity(amount=pop)) #, error=1
                pywikibot.output('Adding %s --> %s' % (population_claim.getID(), population_claim.getTarget()))
                wd_page.addClaim(population_claim)
                    
                #time qualifier
                qualifier = pywikibot.Claim(repo, 'P585')
                pop_date = pywikibot.WbTime(year=pop_year, month=pop_mon, day=pop_day, precision='day')
                qualifier.setTarget(pop_date)
                population_claim.addQualifier(qualifier)

                #method qualifier       "rahvastikubilanss"
                qualifier = pywikibot.Claim(repo, 'P459')
                method = pywikibot.ItemPage(repo, 'Q15911027')
                qualifier.setTarget(method)
                population_claim.addQualifier(qualifier)
                                          
                #source as wiki page:   
                sourceWiki = pywikibot.Claim(repo, 'P248')
                sourceWiki.setTarget(pywikibot.ItemPage(repo, 'Q39420022'))              
                    
                #url as source
                source = pywikibot.Claim(repo, 'P854')
                source.setTarget(source_url)
                #vaadatud
                accessed = pywikibot.Claim(repo, 'P813')
                accessed_date = pywikibot.WbTime(year=access_year, month=access_mon, day=access_day, precision='day')
                accessed.setTarget(accessed_date)    
                        
                population_claim.addSources([sourceWiki, source, accessed])
                ## population_claim.addSources([source, accessed])

            else:
                print ("Population claim already exists "
                            "on %s for year %d, skipping") % (wd_page.title(), pop_year)
                logging.info ("Population claim already exists on %s" % (wd_page.title()))             


        else:
            print ('ERROR: NO DATA PAGE')
            logging.warning('[[%s]]: no data page in Wikidata' % (wd_page.title() ))



###  main

logging.basicConfig(filename='import-lv.log',level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s %(message)s')
  
f = codecs.open('klasifikators_29893.txt', encoding='utf-8')

##0320201	0320200	1	"Aizkraukles pilsēta"	

atvk_names = {}

for line in f:
    cells = line.split("\t")
    if len(cells)>2:
        atvk_id = cells[0]
        adm_name = cells[3]
        adm_name = adm_name.strip('"')
        atvk_names[adm_name] = atvk_id
        

f = codecs.open('2017.csv', encoding='utf-8')

wikidata = pywikibot.Site("wikidata", "wikidata")


for line in f:
    
    cells = line.split(";");
    if len(cells)>1:  
        try:
            name = cells[0]
            name = name.strip('"')
            name = name.strip()
            name = name.replace(u'.', u'')
            
            pop = int( cells[1] )
        
            if ( atvk_names.get(name) ):
                atvk_id = atvk_names.get(name)
                print "%s %s %d" % (atvk_id, name, pop)
                addPopData(wikidata, atvk_id, name, pop)
            else:
                print "no match for name: %s" % ( name )
                logging.info ("no match for name: %s" % ( name ))
            
        except ValueError:
            #do nothing
            continue
            
