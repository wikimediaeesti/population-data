#!/usr/bin/python
# -*- coding: utf-8 -*-
# Import population data for Lithuanian cities from Statistics Lithuania REST XML service

import sys
import os, time
import urllib.request, datetime
import xml.etree.ElementTree as ET

import pywikibot
from pywikibot import pagegenerators
import logging

def getCityNames(struct_xml_url):
    names_dict = {}
    with urllib.request.urlopen(struct_xml_url) as fd:
        root = ET.fromstring(fd.read())
    
    # <str:Codelist id="miestasM3010210" 
    ns = {'my_str': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
      'my_com': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
      'my_xml': 'http://www.w3.org/XML/1998/namespace'}
    codelist = root.findall(".//my_str:Codelist[@id='miestasM3010210']/*", ns)

    for code in codelist:
        if ('id' in code.attrib):
            name = code.find("./my_com:Name[@my_xml:lang='lt']", ns)
            if (name is not None):
                names_dict[code.attrib['id']] = name.text
    return names_dict

def getPopData(pop_xml_url, pop_year):
    pop_dict = {}
    with urllib.request.urlopen(pop_xml_url) as fd:
        root = ET.fromstring(fd.read())
    
    ns = {'my_g': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'}
    observations = root.findall(".//my_g:Obs", ns)
    for observation in observations:
        obskey = observation.find("./my_g:ObsKey", ns)
        if (obskey is not None):
            name_key = obskey.find("./my_g:Value[@id='miestasM3010210']", ns)
            year_key = obskey.find("./my_g:Value[@id='LAIKOTARPIS']", ns)
            if (name_key is not None and year_key is not None):
                assert int(year_key.attrib['value']) == pop_year
                obsvalue = observation.find("./my_g:ObsValue", ns)
                if (obsvalue is not None):
                    try:
                        pop_count = int(obsvalue.attrib['value'])
                        pop_dict[name_key.attrib['value']] = pop_count
                    except ValueError:
                        #do nothing
                        continue
    return pop_dict

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
    

def addPopData(repo, source_url, name_lt, pop_year, pop_count):
    
    statoffice_wd = 'Q12663462'   # LT stat office
    
    #population record date
    pop_day = 1
    pop_mon = 1

    #data access date
    now = datetime.datetime.now()
    access_day = now.day
    access_mon = now.month
    access_year = now.year
    
    logging.info("Checking ... %s" % (name_lt))
    
    sparql = """PREFIX schema: <http://schema.org/>
    SELECT DISTINCT ?item ?LabelEN ?page_titleLT ?itemLabel WHERE {
    ?item wdt:P17 wd:Q37.
    ?item wdt:P31 ?sub1 . ?sub1 (wdt:P279)* wd:Q486972 .
    ?article schema:about ?item.
    ?article schema:isPartOf <https://lt.wikipedia.org/>.
    ?article schema:name ?page_titleLT.
    filter(STR(?page_titleLT) = '%s')
    }
    LIMIT 1""" % (name_lt, )
    wd_pages = pagegenerators.WikidataSPARQLPageGenerator(sparql, site=wikidata)
    wd_pages = list(wd_pages)
    
    wd_count = 0
    for wd_page in wd_pages:

        if wd_page.exists():
            wd_count += 1
            dictionary = wd_page.get()

            if not existingClaimFromYear(wd_page, pop_year, pop_mon, pop_day):
                time.sleep(10)
                
                population_claim = pywikibot.Claim(repo, 'P1082')
                population_claim.setTarget(pywikibot.WbQuantity(amount=pop_count, site=repo)) #, error=1
                pywikibot.output('Adding %s --> %s' % (population_claim.getID(), population_claim.getTarget()))
                wd_page.addClaim(population_claim)
                    
                #time qualifier
                qualifier = pywikibot.Claim(repo, 'P585')
                pop_date = pywikibot.WbTime(year=pop_year, month=pop_mon, day=pop_day, precision='day')
                qualifier.setTarget(pop_date)
                population_claim.addQualifier(qualifier)

                #method qualifier       "demographic balance"
                qualifier = pywikibot.Claim(repo, 'P459')
                method = pywikibot.ItemPage(repo, 'Q15911027')
                qualifier.setTarget(method)
                population_claim.addQualifier(qualifier)
                                          
                #source as wiki page:   
                sourceWiki = pywikibot.Claim(repo, 'P248')
                sourceWiki.setTarget(pywikibot.ItemPage(repo, statoffice_wd))              
                    
                #url as source
                source = pywikibot.Claim(repo, 'P854')
                source.setTarget(source_url)
                
                #accessed
                accessed = pywikibot.Claim(repo, 'P813')
                accessed_date = pywikibot.WbTime(year=access_year, month=access_mon, day=access_day, precision='day')
                accessed.setTarget(accessed_date)    
                        
                population_claim.addSources([sourceWiki, source, accessed])

            else:
                logging.info ("Population claim already exists on %s" % (wd_page.title()))             


        else:
            logging.warning('[[%s]]: no data page in Wikidata' % (wd_page.title() ))

    if (wd_count == 0):
        logging.warning('No Wikidata match found for ' % (name_lt ))


###  main

YEAR = 2017
struct_xml = 'https://osp-rs.stat.gov.lt/rest_xml/datastructure/LSD/M3010210'
pop_xml = "https://osp-rs.stat.gov.lt/rest_xml/data/S3R167_M3010210/?startPeriod=%d&endPeriod=%d" % (YEAR, YEAR)

logging.basicConfig(filename='import-lt.log',level=logging.DEBUG)
logging.basicConfig(format='%(asctime)s %(message)s')
wikidata = pywikibot.Site("wikidata", "wikidata")
  
names_dict = getCityNames(struct_xml)          

pop_dict = getPopData(pop_xml, YEAR)

for name_key in names_dict.keys():
    if name_key in pop_dict:
        addPopData(wikidata, pop_xml, names_dict[name_key], YEAR, pop_dict[name_key])
