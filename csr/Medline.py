
import sys, time
from Bio import Entrez

# Only used for the parser hack
# TODO: import c version?
from xml.etree import ElementTree

import requests
from lxml import html

from csr.Data import DataStream

def convert_document_id(doc_id, email, id_type='PMC'):
        """
        Convert document id to dictionary of other id
        see: http://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/ for more info
        Based on:
        https://github.com/titipata/pubmed_parser/blob/master/pubmed_parser/pubmed_web_parser.py
        """
        doc_id = str(doc_id)
        if id_type == 'PMC':
                doc_id = 'PMC%s' % doc_id
                pmc = doc_id
                convert_link = 'http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=custom&email=%s&ids=%s' % (email, doc_id)
        elif id_type in ['PMID', 'DOI', 'OTHER']:
                convert_link = 'http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=custom&email=%s&ids=%s' % (email, doc_id)
        else:
                raise ValueError('Give id_type from PMC or PMID or DOI or OTHER')
        
        convert_page = requests.get(convert_link)
        print(convert_page.content)
        convert_tree = html.fromstring(convert_page.content)
        record = convert_tree.find('record').attrib
        if 'status' in record or 'pmcid' not in record:
                raise ValueError('Cannot convert given document id to PMC')
        if id_type in ['PMID', 'DOI', 'OTHER']:
                if 'pmcid' in record:
                        pmc = record['pmcid']
                else:
                        pmc = ''
        return {'pmc': pmc,
                'pmid': record['pmid'] if 'pmid' in record else '',
                'doi': record['doi'] if 'doi' in record else ''}

def add_pmids_from_dois(email, records):
        i = 0
        for row in records:
                i += 1
                print("Handling record %i/%i" % (i, len(records)))
                if not row.PMID:
#                        ids = convert_document_id(row.doi, email, id_type='DOI')
                        pmids = retrieve_by_query(email, [row.doi])
                        if len(pmids) > 0:
                                print(pmids[0].PMID)
                                row.PMID = pmids[0].PMID

def retrieve_by_query(email, queries, offset=0, n=100):
        """
        This function is _not_ reentrant unless the email given is constant
        from call to call.
        """
        # We really shouldn't run the queries separately
        # Assume that the queries can be ORed together
        # This is true iff OR has the lowest priority in the query language
        # TODO: check this!
#        if isinstance(queries, basestring): queries = [queries]
        query_string = " OR ".join(queries)

        sys.stderr.write("Retrieving all references matching the query:\n")
        sys.stderr.write(query_string + "\n")

        # Required by the NCBI since 2010 to curb abuse
        Entrez.email = email
        # TODO: Sanity check that the email given is valid
        record = DataStream("PMID")
        try:
                # esearch can return a maximum of 100K articles per query. If we want to retrieve
                # more than that we need to iterate, setting incremental values of retstart
                # Retrieve a fraction of the results for now
                handle = Entrez.esearch(db="pubmed",
                                        term=query_string,
                                        sort="pub date",
                                        retmode="xml",
                                        retstart=offset,
                                        retmax=n)
                # Validate requires a DTD to either be installed or retrieved separately
                # Skip for now
                # Note: Read fails for efetch responses in versions of Biopython
                # The following may or may not work depending on which version is installed:
                # ~ record = Entrez.read(handle, validate=False)
                # Workaround hack, should work in any version of biopython but will
                # fail horribly if the NCBI ever changes the xml format
                res = ElementTree.parse(handle)
#                count = int(res.find('Count').text)
#                sys.stderr.write("%i references found\n" % count)
#                if count > n:
#                        sys.stderr.write("Retrieved articles %i--%i\n" % (offset+1, offset+count))
                for x in res.iterfind('IdList/Id'):
                        record.append([x.text])
        finally:
                try: handle.close()
                except NameError: pass # If the db lookup throws there is no handle to close
        
        return record

def retrieve_fulltext(email, input_records):
        """
        Retrieves fulltext articles from PubMed Central. Input should at least have a PMID field. All field values are retained in the output, but the order of the fields is not guaranteed to be preserved. This function is _not_ reentrant unless the email given is constant from call to call.
        """
        # Required by the NCBI since 2010 to curb abuse
        Entrez.email = email

        sys.stderr.write("Extracting %i records\n" % len(input_records))

        fields = ['fulltext']
        extra_fields = [field for field in input_records.header if not field in fields]
        records = DataStream(*(fields + extra_fields))

        
        batch_i = 0
        batch_size = 5000
        
        sought_pmids = list(set(map(str, input_records.PMID)))
        pmcids = set([])
        
        for ret_start in range(0, len(sought_pmids), batch_size):
                if batch_i == 1: break
                batch_i += 1
                ret_end = min(ret_start + batch_size, len(sought_pmids)+1)
                sys.stderr.write("Processing batch %i (range [%i, %i])\n" % (batch_i,
                                                                             ret_start,
                                                                             ret_end))
                batch_pmids = sought_pmids[ret_start:ret_end]
                id_string = ", ".join(batch_pmids)
                
                # Entrez gives a set to set mapping and doesn't care about order
                # or missing links. Thus the only way to get a mapping from pmid
                # to pmcid (and catch those missing) is by querying each independently.
                handle = Entrez.elink(dbfrom = 'pubmed', db = 'pmc',
                                      linkname = 'pubmed_pmc',
                                      id = id_string,
                                      retmode = 'xml')
                response = Entrez.read(handle, validate = False)
                if response[0]['LinkSetDb']:
                        batch_pmcids = [l['Id'] for l in response[0]['LinkSetDb'][0]['Link']]
                else:
                        batch_pmcids = []
#                sys.stderr.write("Found %i PMCIDs\n" % len(batch_pmcids))
                pmcids.update(batch_pmcids)
        
        sys.stderr.write("Found %i PMCIDs\n" % len(pmcids))

        id_string = ','.join(pmcids)
        handle = Entrez.efetch(db = "pmc",
                               id = id_string,
                               rettype = 'full',
                               retmode = "xml")
        #response = Entrez.read(handle, validate = False)
        articles = ElementTree.parse(handle).getroot()
        pmid_to_article = {}
        for article in articles:
                # ElementTree queries are horribly broken
                for tag in article.findall(".//pub-id"):
                        if tag.attrib['pub-id-type'] == 'pmid':
                                pmid = tag.text
                for tag in article.findall(".//article-id"):
                        if tag.attrib['pub-id-type'] == 'pmid':
                                pmid = tag.text
#                if not pmid:
#                        print(ElementTree.tostring(article))
#                print("Article for PMID: '%s'" % pmid)
                pmid_to_article[pmid] = article
        for record in input_records:
                if record.PMID in pmid_to_article:
                        values = [ElementTree.tostring(pmid_to_article[record.PMID])]
                else:
                        values = ['MISSING_DATA']
                extra_values = [record[f] for f in extra_fields]
                records.append(values + extra_values)
                        
        return records

def retrieve_by_pmid(email, input_records):
        """
        Retrieves abstracts and metadata from PubMed. Input should at least have a PMID field. All field values are retained in the output, but the order of the fields is not guaranteed to be preserved. This function is _not_ reentrant unless the email given is constant from call to call.
        """
        # Required by the NCBI since 2010 to curb abuse
        Entrez.email = email

        sys.stderr.write("Extracting %i records\n" % len(input_records))
        
        def extract_abstract_section(blocks, section):
                blocks = [t for t in blocks if hasattr(t, 'attributes')]
                blocks = [t for t in blocks if 'NlmCategory' in t.attributes]
                return '\n'.join([t for t in blocks if t.attributes['NlmCategory'] == section])
        def extract_mesh_terms(headings):
                terms = []
                for heading in headings:
                        field = heading['DescriptorName']
                        major_topic = field.attributes['MajorTopicYN']
                        ui = field.attributes['UI']
                        terms.append("<%s: %s>" % (ui, field))

                        for field in heading['QualifierName']:
                                major_topic = field.attributes['MajorTopicYN']
                                ui = field.attributes['UI']
                                terms.append("<%s: %s>" % (ui, field))
                return terms
        def try_extract(container, key):
                ''' Returns [] if the key-value is not in the container '''
                try: return container[key]
                except KeyError: return []
                except TypeError: return []

        n_missing_abstracts = 0
        batch_i = 0
        batch_size = 10000
        
        # There are two major gotchas here:
        #   1) We cannot assume that Medline will return results in the same
        #      order as we give it
        #   2) PMIDs can be duplicate in the input (they are in cohen15)
        # The solution to both is to extract from medline and store these for
        # individual pmids, then reassociate the extracted data to the input
        # Make unique list and make sure pmids are *strings*
        sought_pmids = list(set(map(str, input_records.PMID)))
        extracted_records = {}
        sys.stderr.write("Extracting %i unique citations\n" % len(sought_pmids))

        for ret_start in range(0, len(sought_pmids), batch_size):
                batch_i += 1
                ret_end = min(ret_start + batch_size, len(sought_pmids)+1)
                sys.stderr.write("Processing batch %i (range [%i, %i])\n" % (batch_i,
                                                                             ret_start,
                                                                             ret_end))
                batch_pmids = sought_pmids[ret_start:ret_end]
                id_string = ", ".join(batch_pmids)
                
                try:
                        handle = Entrez.efetch(db = "pubmed",
                                               id = id_string,
                                               retmode = "xml")
                        # Note: Read fails for efetch responses in versions of Biopython
                        # The following may or may not work depending on which version is installed:
                        response = Entrez.read(handle, validate = False)
#                        print "%i references returned" % len(response['PubmedArticle'])
                        for citation in response['PubmedArticle']:
                                # These first three fields should always be present
                                article = citation['MedlineCitation']['Article']
                                title = article['ArticleTitle']
                                pmid = str(citation['MedlineCitation']['PMID'])
                                
                                text = try_extract(try_extract(article, 'Abstract'), 'AbstractText')
                                abstract_BACKGROUND  = extract_abstract_section(text, 'BACKGROUND')
                                abstract_METHODS     = extract_abstract_section(text, 'METHODS')
                                abstract_RESULTS     = extract_abstract_section(text, 'RESULTS')
                                abstract_CONCLUSIONS = extract_abstract_section(text, 'CONCLUSIONS')
                                abstract = '\n'.join(text)
                                if not abstract: n_missing_abstracts += 1
                                pub_type_list = try_extract(article, 'PublicationTypeList')
                                publication_types = '; '.join(pub_type_list)
                                keyword_list = try_extract(citation['MedlineCitation'], 'KeywordList')
                                keyword_list = [x for xx in keyword_list for x in xx] # Flatten list
                                keywords = '; '.join(keyword_list)
                                mesh_list = try_extract(citation['MedlineCitation'], 'MeshHeadingList')
                                mesh_list = extract_mesh_terms(mesh_list)
#                                mesh_list = [x for xx in mesh_list for x in xx] # Flatten list
                                mesh_terms = '; '.join(mesh_list)
                                journal = try_extract(citation['MedlineCitation']['MedlineJournalInfo'], 'MedlineTA')
                                values = [pmid,
                                          title,
                                          abstract_BACKGROUND,
                                          abstract_METHODS,
                                          abstract_RESULTS,
                                          abstract_CONCLUSIONS,
                                          abstract,
                                          publication_types,
                                          mesh_terms,
                                          keywords,
                                          journal]
                                extracted_records[pmid] = values
                                
                finally:
                        try: handle.close()
                        except NameError:
                                pass # If the db lookup fails there is no handle to close
        
        extracted_links = {}
        sys.stderr.write("Extracting %i unique linksets\n" % len(sought_pmids))

        for ret_start in range(0, len(sought_pmids), batch_size):
                batch_i += 1
                ret_end = min(ret_start + batch_size, len(sought_pmids)+1)
                sys.stderr.write("Processing batch %i (range [%i, %i])\n" % (batch_i,
                                                                             ret_start,
                                                                             ret_end))
                batch_pmids = sought_pmids[ret_start:ret_end]
                
                try:
                        handle = Entrez.elink(db = "pubmed",
                                               dbfrom = "pubmed",
                                               id = batch_pmids,
                                               retmode = "xml")
                        response = Entrez.read(handle, validate = False)
#                        print "%i references returned" % len(response)
                        for linkset in response:
                                # We only give one id, so we should receive only one
                                pmid = str(linkset['IdList'][0])
                                
                                refs = []
                                similar = []
                                for db in linkset['LinkSetDb']:
                                        if db['LinkName'] == 'pubmed_pubmed_refs':
                                                refs = [l['Id'] for l in db['Link']]
                                        if db['LinkName'] == 'pubmed_pubmed':
                                                similar = [l['Id'] for l in db['Link']]
                                refs    = '; '.join(refs)
                                similar = '; '.join(similar)
                                
                                extracted_links[pmid] = [refs, similar]
                                
                finally:
                        try: handle.close()
                        except NameError:
                                pass # If the db lookup fails there is no handle to close

        # Reassociate
        fields = ['PMID',
                  'title',
                  'abstract_BACKGROUND',
                  'abstract_METHODS',
                  'abstract_RESULTS',
                  'abstract_CONCLUSIONS',
                  'abstract',
                  'publication_types',
                  'mesh_terms',
                  'keywords',
                  'journal',
                  'references',
                  'similar_articles']
        # We could use sets, but this preserves order
        # Switch to sets if this ever becomes an issue speedwise
        extra_fields = [field for field in input_records.header if not field in fields]
        records = DataStream(*(fields + extra_fields))
        for row in input_records:
                try:
                        extra_values = [row[f] for f in extra_fields]
                        values = []
                        values += extracted_records[row.PMID]
                        values += extracted_links[row.PMID]
                        values += extra_values
                        records.append(values)
                except KeyError:
                        # Sometimes we are given erroneous data (e.g. pmid
                        # 12168612 in cohen15)
                        sys.stderr.write('Missing pmid: %s\n' % row.PMID)
                        records.append([f in input_records.header and row[f] or '' for f in records.header])
        
        sys.stderr.write("Extracted %i records\n" % len(records))
        sys.stderr.write("Missing abstracts: %i\n" % n_missing_abstracts)
        return records

        
