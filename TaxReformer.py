#!/usr/bin/env python2

### Created by Bruno de Medeiros (souzademedeiros@fas.harvard.edu), starting on 08-jun-2016
### The purpose of the script is to correct name spelling
###    and obtain taxonomy to the order level for insects
### This script uses takes as input a text file containing a list of dictionaries
### These dictionaries must have keys g (genus) and s (species)
### Results are appended to input dictionaries and saved in a text file
### Open Tree of Life API is used as primary tool.
### If a species is not found there, we use Global Names Resolver API.
### The latter has a better database, but context-based search does not work.
### Therefore, results in cross-kingdom homonyms.
###     *if information on synonyms is available, uses senior synonym
### Open Tree of Life API is used to obtain taxonomy.
### If future versions of Open Tree of Life have a more complete taxonomy,
###     might be a good a idea to switch to their API entirely.
### If the program suspects a name is a cross-kingdom synonym, it requests user input


### In addition to python packages listed below, the script requires GNparser
### https://github.com/GlobalNamesArchitecture/gnparser

import argparse, requests, sys, subprocess, json, time, warnings, pandas, os
from fuzzywuzzy import fuzz #see note on function fuzzy_score
from requests.exceptions import ConnectionError, SSLError
from numpy import nan #needed at the end to parse temporary file
#argparse below inside if __name__ == '__main__'

# Function to call GNparser for a scientific name
# Takes as input the name as a string and the path to GNparser
# Assumes that uninomial names are genera
# Returns a dictionary with the following:
# cg: corrected genus (or higher) name 
# cs: corrected species name
# csub: corrected subspecific names

def GNparser(name, gnpath):
    out_dict = {}
    result_string = subprocess.check_output([gnpath, name], stderr=subprocess.STDOUT) #call GNparser
    result_dict = json.loads(result_string)['details'][0]
    try:
        out_dict['cg'] = result_dict['genus']['value']
    except KeyError:
        pass
    try:
        out_dict['cs'] = result_dict['specificEpithet']['value']
    except KeyError:
        pass
    try:
        out_dict['csub'] = result_dict['infraspecificEpithets'][0]['value']
    except KeyError:
        pass
    try:
        out_dict['cg'] = result_dict['uninomial']['value']
    except KeyError:
        pass

    return out_dict

#this function is a wrapper for taxonomic resolution services in otl api v3.
#if service returns an error code, it pauses execution and tries again  in wait_time seconds
#(useful if making a number of requests that can pass the api daily limit)
def otl_tnrs(query, do_approximate = True, wait_time = 600, context = 'Arthropods'):
    contact_otl = True
    while contact_otl:
        try:
            r = requests.post('https://api.opentreeoflife.org/v3/tnrs/match_names',
                    json = {'names':[query, query],
                            'do_approximate_matching':do_approximate,
                            'context_name':context})
        except (SSLError, ConnectionError):
            sys.stderr.write(time.ctime() + ': ' + 
                             'Error while connnecting to Open Tree of Life, will try again in ' + 
                             str(wait_time) + ' seconds.')
            time.sleep(wait_time)
            continue

        if r.status_code == 200:
            contact_otl = False
        else:
            sys.stderr.write(time.ctime() + ': ' + 
                             'Error with Open Tree of Life response, will try again in ' + 
                             str(wait_time) + ' seconds.')
            time.sleep(wait_time)
            continue
    return r

#this function is a wrapper for taxonomy in otl api v3.
#if service returns an error code, it pauses execution and tries again  in wait_time seconds
#(useful if making a number of requests that can pass the api daily limit)
def otl_taxon(query, wait_time = 600, ncbi = False):
    contact_otl = True
    while contact_otl:
        try:
            if ncbi:
                r = requests.post('https://api.opentreeoflife.org/v3/taxonomy/taxon_info',
                    json = {'source_id':'ncbi:' + str(query), #id for taxon being searched
                            'include_lineage':True}) #include higher taxa
            else:
                r = requests.post('https://api.opentreeoflife.org/v3/taxonomy/taxon_info',
                                json = {"ott_id":query, #id for taxon being searched
                                        "include_lineage":True}) #include higher taxa
        except (SSLError, ConnectionError):
            sys.stderr.write(time.ctime() + ': ' + 
                             'Error while connnecting to Open Tree of Life, will try again in ' + 
                             str(wait_time) + 
                             ' seconds.')
            time.sleep(wait_time)
            continue

        if r.status_code == 200:
            contact_otl = False
        elif r.status_code == 400:
            contact_otl = False
            sys.stderr.write(r.json()['message'])
            sys.stderr.write('skipping')
            return None
        else:
            sys.stderr.write(time.ctime() + ': ' +
                             'Error while contacting Open Tree of Life, will try again in ' + 
                             str(wait_time) + ' seconds.')
            time.sleep(wait_time)
    return r


#helper function that parses ott taxonmy source results to a dictionary
def list2dict(taxlist):
    return {x.split(':')[0]:x.split(':')[1] for x in taxlist}

#This function uses Open Tree of Life API version 3(https://github.com/OpenTreeOfLife/germinator/wiki/Taxonomy-API-v3)
#Given a genus name, it returns its taxonomy up to order in a dictionary, and the ott_id for the genus
def taxonomy_OTT(ott_id = None):  
    #now, get taxonomic information
    r = otl_taxon(ott_id, wait_time = 3600)    

    #save all higher taxa in dict, keyed by ranks
    out_dict = {('tax_' + higher['rank']):higher['name'] for higher in r.json()['lineage']}
    out_dict['tax_higher_source'] = 'OTT'
    out_dict['rank'] = r.json()['rank']
    #remove unnecessary ranks
    for rank in ['tax_no rank']:
        out_dict.pop(rank,0)
    
    #OTT stores Collembola, Protura, and Diplura as classes, not orders
    #if out_dict['tax_class'] and out_dict['tax_class'] in ['Collembola','Diplura','Protura']:
    #    out_dict['tax_order'] = out_dict['tax_class']

    #add genus ott_id and ncbi_id to output dictionary, if species-level
    #or just ott_id and ncbi_id for taxon if not species-level
    out_dict['tax_ott_id'] = ott_id
    out_dict['tax_ott_accepted_name'] = r.json()['name'] #the searched genus might be a synonym, so we also keep the updated name according OTT
    try:
        out_dict.update({'tax_ncbi_id':list2dict(r.json()['tax_sources'])['ncbi']})
    except KeyError:
        pass
    
    #if species or subspecies, add genus information
    if r.json()['rank'] in ['species','subspecies']:
        try:
            genus_tax = [tax for tax in r.json()['lineage'] if tax['rank'] == 'genus'][0]
        except IndexError:
            out_dict['tax_cg_ott_id'] = nan
            if out_dict['rank'] in ['species', 'subspecies']:
                out_dict['cg'] = r.json()['unique_name'].split()[0]
        else:
            out_dict['tax_cg_ott_id'] = genus_tax['ott_id']
            out_dict['cg'] = out_dict['tax_genus']
            del out_dict['tax_genus']
            try:
                out_dict.update({'tax_cg_ncbi_id':list2dict(genus_tax['tax_sources'])['ncbi']})
            except KeyError:
                pass
                #warnings.warn('Genus ' + out_dict['cg'] +  ' not in ncbi!')
    #if subspecific rank, update ids ofr species
    try:
        species_tax = [tax for tax in r.json()['lineage'] if tax['rank'] == 'species'][0]
        out_dict['tax_cs_ott_id'] = species_tax['ott_id']
    except:
        pass
    
    try:
        del out_dict['tax_species']
    except KeyError:
        pass
    
    if out_dict['rank'] not in ['species','subspecies','genus','subgenus']:
        out_dict['cg'] = ''        
        
    return out_dict

#############################################
#In this section, we have a bunch of functions that simply check if a name exists in a service, without fuzzy matching
#All of them should take the name as a query, and return a dictionary with the following mandatory keys:
#currently accepted name, id on taxonomic service, level , taxonomic source and higher_taxonomy
#All of them should also check if the name is an arthropod
#If name not found as genus or species, it should return None
def otl_checkname(query, context):
    outdict = None
    
    r = otl_tnrs(query, do_approximate = False, context = context)
    if r.json()['results']:
        result = r.json()['results'][0]['matches'][0]
        outdict = {'current_name': result['taxon']['name'], 
                   'id': result['taxon']['ott_id'], 
                   'name_source': 'OTT'}
        outdict['higher_taxonomy'] = taxonomy_OTT(result['taxon']['ott_id'])

        if result['taxon']['rank'] == 'species':
            outdict['level'] = 'species'
            try: 
                outdict['ncbi_id'] = list2dict(result['taxon']['tax_sources'])['ncbi']
            except:
                pass
            
        elif result['taxon']['rank'] == 'genus':
            outdict['level'] = 'genus'
        else:
            warnings.warn(query + ': found in ott, but not as genus or species')
            return None
            
    return outdict


    
#Function to parse classification paths obtained from Global Names
def parse_GN_classpath(GN_result):
    if GN_result['classification_path_ranks']:
        ranks = [rank.lower() for rank in GN_result['classification_path_ranks'].split('|')]
        names = GN_result['classification_path'].split('|')
        taxdict = dict()
            
        if ranks[-1]:
            this_rank = ranks[-1]
        else:
            if 'family' in ranks[-2] or 'tribe' in ranks[-2]:
                this_rank = 'genus'
            elif 'genus' in ranks[-2]:
                this_rank = 'species'
            else: #in some sources, only ranks above family are reported, try to guess from space in name
                if ' ' in GN_result['canonical_form']:
                    this_rank = 'species'
                else:
                    this_rank = 'genus'
                
        
        for i, rank in enumerate(ranks[:-1]):
            taxdict['tax_' + rank] = names[i]
    else:
        this_rank = None
        taxdict = None
    
        
    return {'tax_level':this_rank, 'higher_taxonomy':taxdict}
               
#Function to do fuzzy search in Global Names
def fuzzy_search_GN(full_name, taxfilter):
    #start by fuzzy searching Global Names
    results_with_classpath = []
    all_results = []    
    trycounter = 0
    
    while trycounter < 10:
        try:
            r = requests.post('http://resolver.globalnames.org/name_resolvers.json',
                                json = {'names':full_name, #searching for genus + species first to avoid homonyms 
                                        'best_match_only':'false'})
            break
        except ConnectionError as err:
            trycounter += 1
            sys.stderr.write(err + '\n' + 'Trying again')
    else:
        'More than 10 failed connection attempts, skipping.'
        return None
    
    #save only results with a classification path including taxfilter               
    if 'results' in list(r.json()['data'][0].keys()):
        for result in r.json()['data'][0]['results']:
            all_results.append(result)

            if taxfilter and \
            'classification_path' in list(result.keys()) and \
            result['classification_path'] is not None and \
            taxfilter in result['classification_path']:
                results_with_classpath.append(result)

    #now we choose what to search for an exact match in ott
    #if we could filter results, we choose the best of them
    #and we check if we found only genus or genus + species
    #if we did not have a classification path, we proceed with the best result regardless
    #and if there is no results, we pass None
    if results_with_classpath:
        res_to_consider = results_with_classpath
    elif all_results:
        res_to_consider = all_results
    else:
        return None  

    max_score = max(result['score'] for result in res_to_consider)
    results_with_max_score = [result for result in res_to_consider if result['score'] == max_score]
    
    #if multiple results with maximum score, choose the one from OTT, NCBI or GBIF, in this order. If none of these, choose the first one
    ott_source = [i for i,x in enumerate(results_with_max_score) if x['data_source_id'] == 179]
    ncbi_source = [i for i,x in enumerate(results_with_max_score) if x['data_source_id'] == 4]
    gbif_source = [i for i,x in enumerate(results_with_max_score) if x['data_source_id'] == 11]
    
    if ott_source:
        chosen_result = results_with_max_score[ott_source[0]]
    elif ncbi_source:
        chosen_result = results_with_max_score[ncbi_source[0]]
    elif gbif_source:
        chosen_result = results_with_max_score[gbif_source[0]]
    else:
        chosen_result = results_with_max_score[0]
        
    return chosen_result
        


# Function to fuzzy search names using Open Tree of Life API or global names resolver API
# Returns a dictionary with the matched name, the senior synonym, the ott_id if rank is species, and the taxonomic source
# Starts by fuzzy searching OTL, and then Global names if can't find it
# If found on global names, name is subject to exact search on a number of services, using functions listed in variable namesearch_functions (currently only OTT and GBIF)
# UPDATE Apt 2019: dropping support for GBIF for now since pygbif does not work in python 3

def search_name(full_name, gnpath, context, taxfilter):
    namesearch_functions = [lambda x: otl_checkname(x, context=context)]#, 
                            #lambda x: gbif_checkname(x, taxfilter=taxfilter)]
    
    outdict = {'matched_name': None, 
               'current_name': None, 
               'source_id': None, 
               'sp_ncbi_id': None, 
               'tax_source': None,
               'tax_level': None,
               'higher_taxonomy': None}
    
   
        
    GN_search_result = fuzzy_search_GN(full_name, taxfilter = taxfilter)  
    search_for_genus = False
        
    #now check if chosen result has genus and species or only species
    if GN_search_result:
        try:
            chosen_name = GNparser(GN_search_result['current_name_string'],gnpath)
        except:
            chosen_name = GNparser(GN_search_result['canonical_form'],gnpath)
        if 'cs' not in list(chosen_name.keys()):
            search_for_genus = True
            genus_to_search = chosen_name['cg']
    #if no result and we searched for genus + species, trying searching for genus only
    elif 'cs' in GNparser(full_name,gnpath).keys:
        GN_search_result = fuzzy_search_GN(GNparser(full_name,gnpath)['cg'], taxfilter = taxfilter)
        if GN_search_result:
            try:
                chosen_name = GNparser(GN_search_result['current_name_string'],gnpath)
            except:
                chosen_name = GNparser(GN_search_result['canonical_form'],gnpath)
            search_for_genus = True
            genus_to_search = chosen_name['cg']
        #if still no result, we consider we can't find it
        else:
            return None
    #if no result and there was no species information, so it was already a genus search
    else:
        return None
        

    #if we do have a full name (genus + species), start by exact searching open tree of life
    #if we find a species, return with information from open tree of life
    if not search_for_genus:
        #chosen_name = GNparser(GN_search_result['canonical_form'],gnpath)
        if 'csub' in list(chosen_name.keys()): 
            full_name_to_search  = ' '.join([chosen_name['cg'],chosen_name['cs'],chosen_name['csub']])
        elif 'cs' in list(chosen_name.keys()):
            full_name_to_search  = ' '.join([chosen_name['cg'],chosen_name['cs']])
        else:
            full_name_to_search  = chosen_name['cg']
            
        r = otl_tnrs(full_name_to_search, do_approximate = False, context = context)
        if r.json()['results']:
            results = r.json()['results'][0]['matches']
            scores = [results[i]['score'] for i in range(len(results))] #make a list with matches' scores
            best = scores.index(max(scores)) #returns index for result with highest score. If more than one, keeps first
            
            outdict['tax_level'] = results[best]['taxon']['rank']
            
            if outdict['tax_level'] in ['species','subspecies']:
                ott_id = results[best]['taxon']['ott_id']
                try:
                    ncbi_id = list2dict(results[best]['taxon']['tax_sources'])['ncbi']
                except KeyError:
                    ncbi_id = None       
                outdict['matched_name'] =  GN_search_result['canonical_form']
                outdict['current_name'] =  results[best]['taxon']['name']
                outdict['source_id'] = ott_id
                outdict['sp_ncbi_id'] = ncbi_id
                outdict['tax_source'] = 'OTT'
                outdict['higher_taxonomy'] = taxonomy_OTT(ott_id)
                return outdict
            #if match in OTT is not a species, try searching for genus
            else:
                genus_to_search = chosen_name['cg']
                search_for_genus = True
        #if no results from open tree of life, try searching for genus        
        else:
            genus_to_search = chosen_name['cg']
            search_for_genus = True
        
            
    
    if search_for_genus:
        #start by searching for genus or higher names found in GN in OTL without fuzzy matching
        r = otl_tnrs(genus_to_search, do_approximate = False, context = context)
        if r.json()['results']: #if results found, return the best
            results = r.json()['results'][0]['matches']
            scores = [results[i]['score'] for i in range(len(results))] #make a list with matches' scores
            best = scores.index(max(scores)) #returns index for result with highest score. If more than one, keeps first
            
            outdict['tax_level'] = results[best]['taxon']['rank']                        
            outdict['matched_name'] =  results[best]['matched_name']
            outdict['current_name'] =  results[best]['taxon']['name']
            outdict['source_id'] = results[best]['taxon']['ott_id']
            outdict['tax_source'] = 'OTT'
            outdict['higher_taxonomy'] = taxonomy_OTT(results[best]['taxon']['ott_id'])
            
            return outdict

                
    #now that a name was found in global names or OTT, try exact matches in our taxonomic sources (currently, OTT only)
    for search_fun in namesearch_functions:
        r = search_fun(GN_search_result['canonical_form'])
        if r: #at the first result found, get information and break loop
            outdict['tax_level'] = r['level']
            outdict['matched_name'] =  GN_search_result['canonical_form']
            outdict['current_name'] =  r['current_name']
            outdict['source_id'] = r['id']
            outdict['tax_source'] = r['name_source']
            
            if 'higher_taxonomy' in list(r.keys()):
                outdict['higher_taxonomy'] = r['higher_taxonomy']
            
            if r['level'] == 'species' and 'ncbi_id' in list(r.keys()):
                outdict['sp_ncbi_id'] = r['ncbi_id']
            
            break

                    
    #if nothing found, return only name from GN 
    else: 
        outdict['matched_name'] =  GN_search_result['canonical_form']
        outdict['current_name'] =  GN_search_result['canonical_form']
        outdict['tax_source'] = 'GN_datasourceid_' + str(GN_search_result['data_source_id']) 
        outdict['source_id'] = str(GN_search_result['data_source_id'])
        
        
        GNparsed = parse_GN_classpath(GN_search_result)
        outdict['tax_level'] = GNparsed['tax_level']
        #!!!!!!!!!!!!!!!!for now, we are only accepting higher taxonomy from OTT
        #outdict['higher_taxonomy'] = GNparsed['higher_taxonomy']
        
    return outdict 




#This function returns a fuzzy matching score between the searched name and the corrected name.
#Since we are using different sources for taxonomy (open tree of life and global names), scores are not comparable
#If in the future global names includes OTT as a source of data, we might be able to rewrite the search_names() function and deprecate this one
def fuzzy_score(name1,name2):
    return fuzz.ratio(name1, name2)

#read input and run program
# for each record in the input file, it will try to find a name
# the folling keys will be added to the record, saved in a new file named corrected_new_lines.txt
# cg: corrected genus name (senior synonym if available)
# cs: corrected species name (senior synonym if available)
# csub: corrected subspecific names (senior synonym if available)
# tax_match: matched name in canonical form
# tax_score: fuzzy matching score between query name and matched name
# tax_source: OTT (open tree of life) or GN (global names)
# tax_[taxonomic rank]: several optional keys containing higher taxonomic levels for the
# problem: reason why record was rejected

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help = 'Path to input file, see docs for options')
    #parser.add_argument('output', help = 'Path to problem file')
    parser.add_argument('-o','--output', help = 'Prefix to add to output files', default = 'output')
    parser.add_argument('-p', '--gnparser', help = 'Path to GNparser (by default search in PATH)')
    parser.add_argument('-c','--context', help = 'Taxonomic context (see Open Tree Taxonomy API for options)', default = 'All life')
    parser.add_argument('-f','--tax-filter', help = '''Comma-separated list of names of higher taxa in which queries must be included. 
                                                    Used to filter results from services other than Open Tree Taxonomy.
                                                    A result matching any taxon in the list will be kept.''')
    
    args = parser.parse_args()
    if not args.gnparser:
        gnpath = 'gnparser'    
    else:
        gnpath = args.gnparser
    #args = parser.parse_args(['-o','egg_database.txt']) #this is here for testing


    #first, generate name of outfile
    #outbase = 'corrected_' + os.path.basename(args.input) #12-aug-16 we changed the folder structure. Keeping code here for now in case needed
    #outpath = os.path.join(os.path.dirname(args.input), outbase)
    outpath = '.matched.txt'
    problems_path = '.unmatched.txt'

    #read input
    intable = pandas.read_csv(args.input)
    other_cols = intable.columns.tolist()
    other_cols.remove('name')
    
    records = intable.to_dict('records')
    #print records

    #loop through records, correct names and add taxonomy. Write to file after each record
    with open(outpath,'w') as outfile, open(problems_path, 'w') as problems:
        #record version of ott taxonomy used here
        ott_version = requests.post('https://api.opentreeoflife.org/v3/taxonomy/about').json()['source']

        for i in range(len(records)):
            try:
                has_tax = any([key.find('tax_') > -1 for key in list(records[i].keys())])
            except KeyError:
                has_tax = False
                       
            #first, record version of open tree taxonomy used here
            records[i]['tax_ott_version'] = ott_version
            
            try:
                searchname_response =  search_name(records[i]['name'], gnpath, context = args.context, taxfilter = args.tax_filter)
            except (ValueError, TypeError):
                searchname_response = None
            #except KeyError as err:
            #    if 's' in err.args:
            #        searchname_response = search_name(records[i]['g'], gnpath,context = args.context, taxfilter = args.tax_filter)
            #    else:
            #        raise err
            
            #if nothing was found, add to problems with flag no_name               
            if not searchname_response:
                records[i].update({'problem':'no_name'})
                print(records[i], file=problems)
                sys.stdout.write('Record ' + str(i + 1) + ' of ' + str(len(records)) + ' processed. Taxonomy Error: no_name\n')
                continue
            
            #if something was found, parse matched name to genus and species and add information to output database
            else:
                records[i].update(GNparser(searchname_response['current_name'], gnpath)) #this parses name found, separating genus and species
                records[i].update({'tax_updated_fullname':searchname_response['current_name']})
                records[i].update({'tax_name_source':searchname_response['tax_source']})
                records[i].update({'tax_matched':searchname_response['matched_name']})
                records[i]['tax_matched_id_in_source'] = searchname_response['source_id']
                if searchname_response['tax_source'] == 'OTT':
                   if searchname_response['tax_level'] == 'species':
                       records[i]['tax_cs_ott_id'] = searchname_response['source_id']
                   elif searchname_response['tax_level'] == 'genus':
                       records[i]['tax_cg_ott_id'] = searchname_response['source_id']
                if searchname_response['sp_ncbi_id']:
                    records[i]['tax_cs_ncbi_id'] = searchname_response['sp_ncbi_id']
                
                try:
                    records[i].update({'tax_score':fuzzy_score(records[i]['name'] + ' ' + records[i]['s'], records[i]['tax_matched'])})
                except KeyError:
                    records[i].update({'tax_score':fuzzy_score(records[i]['name'], records[i]['tax_matched'])})
                

            #if name was found, but not in OTT, try obtaining higher taxonomy from genus name in ott first
            #if can't be found in OTT, use the taxonomy from the name source
            #if no taxonomy from name source, output as a problem
            if searchname_response['tax_source'] != 'OTT':
                ott_genus_search = otl_checkname(records[i]['cg'], context = args.context)
                if ott_genus_search and ott_genus_search['level'] == 'genus' and ott_genus_search['higher_taxonomy']:
                    records[i].update(ott_genus_search['higher_taxonomy'])
                    records[i]['tax_taxonomy_source'] = 'OTT'
                    
                elif searchname_response['higher_taxonomy'] is None:
                    records[i].update({'problem':'no_taxonomy'})
                    print(records[i], file=problems)
                    sys.stdout.write('Record ' + str(i + 1) + ' of ' + str(len(records)) + ' processed. Taxonomy Error: no_taxonomy\n')
                    continue
                    
                else:
                    records[i].update(searchname_response['higher_taxonomy'])
                    records[i]['tax_taxonomy_source'] = searchname_response['tax_source']

            #if tax_source is OTT, just record higher taxonomy        
            else:
                records[i]['tax_taxonomy_source'] = 'OTT'
                records[i].update(searchname_response['higher_taxonomy'])
                

            #finally, if record had a species read from OCR but only genus found, output to problems            
            if 's' in list(records[i].keys()) and 'cs' not in list(records[i].keys()) and not args.genus_search:
                records[i].update({'problem':'no_species'})
                print(records[i], file=problems)
                sys.stdout.write('Record ' + str(i + 1) + ' of ' + str(len(records)) + ' processed. Taxonomy Error: no_species\n')
            else:
                print(records[i], file=outfile)
                sys.stdout.write('Record ' + str(i + 1) + ' of ' + str(len(records)) + ' processed. Record OK          \n')
                
            
            sys.stdout.flush()
            
    #if table input, should write table output and delete dict output        
    sys.stderr.write('Search finished, deleting temporary files and writing table output.\n')
    with open(outpath,'r') as outfile, open(problems_path, 'r') as problems:
        matched = [eval(line) for line in outfile]
        unmatched = [eval(line) for line in problems]

    
    
    taxonomic_ranks = ['tax_' + prefyx + root for root in ['domain',
                       'kingdom',
                       'phylum',
                       'class',
                       'order',
                       'family',
                       'tribe'] for prefyx in ['super','','sub','infra','parv']]
    
    first_cols = ('name',
                        'tax_updated_fullname',
                        'tax_taxonomy_source',
                        'rank',
                        'tax_matched',
                        'tax_score',
                        'tax_ott_id',
                        'tax_ncbi_id',
                        'tax_name_source',
                        'tax_matched_id_in_source',
                        'cg',
                        'tax_cg_ott_id',
                        'tax_cg_ncbi_id',
                        'cs',
                        'tax_cs_ott_id',
                        'tax_cs_ncbi_id',
                        'csub',
                        'tax_ott_accepted_name',
                        'tax_ott_version',
                        'tax_higher_source')
    
    
    if matched:
        matched_df = pandas.DataFrame(matched)
        
        
        present_ranks = [tax for tax in taxonomic_ranks if tax in matched_df.columns]
        
        ordered_cols = list(first_cols)
        ordered_cols.extend(present_ranks)
        ordered_cols.extend(other_cols)
        
        final_cols = [col for col in matched_df.columns if col not in ordered_cols]
        ordered_cols.extend(final_cols)
        
        
        matched_df = matched_df[[ col for col in ordered_cols if col in matched_df.columns]]
        matched_df.rename(inplace=True, columns= lambda x: x.replace('tax_',''))
        matched_df.rename(inplace=True, columns= lambda x: x.replace('rank','rank_matched'))
        matched_df.rename(inplace=True, columns= lambda x: x.replace('csub','updated_subspecies'))
        matched_df.rename(inplace=True, columns= lambda x: x.replace('cg','updated_genus'))
        matched_df.rename(inplace=True, columns= lambda x: x.replace('cs','updated_species'))
        matched_df.to_csv(args.output + '_matched.csv')
    
    if unmatched:
        
        unmatched_df = pandas.DataFrame(unmatched)
        
        ordered_cols = list(first_cols)
        ordered_cols.extend(other_cols)
        final_cols = [col for col in unmatched_df.columns if col not in ordered_cols]
        ordered_cols.extend(final_cols)
        
        unmatched_df = unmatched_df[[ col for col in ordered_cols if col in unmatched_df.columns]]
        
        unmatched_df.rename(inplace=True, columns = lambda x: x.replace('tax_',''))
        unmatched_df.rename(inplace=True, columns= lambda x: x.replace('rank','rank_matched'))
        unmatched_df.rename(inplace=True, columns = lambda x: x.replace('csub','updated_subspecies'))
        unmatched_df.rename(inplace=True, columns = lambda x: x.replace('cg','updated_genus'))
        unmatched_df.rename(inplace=True, columns = lambda x: x.replace('cs','updated_species'))
        unmatched_df.to_csv(args.output + '_unmatched.csv')
    
    
    os.remove(outpath)
    os.remove(problems_path)
        
        

