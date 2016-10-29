
# coding: utf-8

# In[1]:

import xml.etree.cElementTree as ET  # Use cElementTree or lxml if too slow
import re
from collections import defaultdict
import operator
import csv
import codecs
import cerberus
import schema
import sqlite3
import string


# In[2]:

#!/usr/bin/env python


#OSM_FILE contains all the data, SAMPLE_FILE contain just a sample
OSM_FILE = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/london_england.osm" 
SAMPLE_FILE = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/sample_london.osm"

#This gives us 1/500 of the data for my sample
k = 500 # Parameter: take every k-th top level element

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


with open(SAMPLE_FILE, 'wb') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output.write('<osm>\n  ')

    # Write every kth top level element
    for i, element in enumerate(get_element(OSM_FILE)):
        if i % k == 0:
            output.write(ET.tostring(element, encoding='utf-8'))

    output.write('</osm>')


# Information about users: 

# In[4]:

#1.1
def users(filename):
    '''Returns how many users there are from a file (filename), and how many edits each of them have.'''
    users = {}
    for _, element in ET.iterparse(filename):
        if element.get('uid'):
            id = element.attrib['uid']
            if id not in users:
                users[id] = 1
            else:
                users[id] += 1
    return users


# In[5]:

#1.2
def total_user_edits(filename):
    '''Counts the total number of user edits from a file(filename).'''
    all_users = users(filename)
    return sum(all_users.values())


# In[6]:

#1.3
def top_users(number_of_users, filename):
    '''
    Use the previous two function to determine how many users (number_of_users) 
    make what percentage of the total edits from a file.'''
    all_users = users(filename)
    sorted_users = sorted(all_users.items(), key=operator.itemgetter(1), reverse = True)
    total_edits = total_user_edits(filename)
    i = 1
    top_users = 0.0
    for user in sorted_users:
        top_users += user[1]
        if i == number_of_users:
            print top_users
            print round(top_users/total_edits,4)
        i += 1


# Types of Keys:

# In[8]:

#2.1
'''
"lower" - for tags that contain only lowercase letters and are valid; 
"lower_colon" - for otherwise valid tags with a colon in their names; 
"problemchars" - for tags with problematic characters; 
"other" - for other tags that do not fall into the other three categories.
'''
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')


# In[9]:

#2.2
def key_type(element, keys):
    '''Sort elements by which type of key they are, and returns the type of key.'''
    if element.tag == "tag":
        k = element.attrib['k']
        if lower.search(k):
            keys['lower'] += 1
        elif lower_colon.search(k):
            keys['lower_colon'] += 1
        elif problemchars.search(k):
            keys['problemchars'] += 1
        else:
            keys['other'] += 1
    return keys


# In[10]:

#2.3
def count_key_type(filename):
    '''Returns the total number of each type of key from a file.'''
    keys = {"lower": 0, "lower_colon": 0, "problemchars": 0, "other": 0}
    for _, element in ET.iterparse(filename):
        keys = key_type(element, keys)
    return keys


# Create Useful Functions:

# In[12]:

#3.1
def audit_key(filename, key):
    '''Find all the values for a particular key and returns a dictionary of all of the unique values.'''
    the_file = open(filename, "r")
    dic = set()
    for event, elem in ET.iterparse(the_file, events=("start",)):
        for tag in elem.iter("tag"):
            if tag.attrib['k'] == key:
                dic.add(tag.attrib['v'])
    the_file.close()
    return dic


# In[13]:

#3.2
def update_value(filename, key, old_v, new_v):
    '''Replaces the old values (old_v) with new_values (new_v) from a particular key.'''
    e = ET.parse(filename)
    for tag in e.iter("tag"):
        if tag.attrib['k'] == key:
            if tag.attrib['v'] == old_v:
                tag.attrib['v'] = new_v
    return new_v


# Update the Street Types:

# In[14]:

#4.1
'''A list of all of the street types I expect to find.'''
expected_streets = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Close"]


# In[15]:

#4.2
'''Compile a regular expression pattern.'''
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)


# In[16]:

#4.3
def audit_street_type(street_types, street_name):
    '''Add unexpected street types into a dictionary.'''
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected_streets:
            street_types[street_type].add(street_name)


# In[17]:

#4.4
def audit_streets(filename):
    '''Finds and creates a dictionary of all the unexpected street types.'''
    the_file = open(filename, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(the_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if tag.attrib['k'] == 'addr:street':
                    audit_street_type(street_types, tag.attrib['v'])
    the_file.close()
    return street_types


# In[18]:

#4.5
'''A dictionary of street types that need to be corrected.'''
corrected_street_types = {"Ave": "Avenue"}


# In[19]:

#4.6
def update_street_name(filename, old_v, new_v):
    '''Replaces the old street types (old_v) with new street types (new_v) and returns the new street name.'''
    e = ET.parse(filename)
    for tag in e.iter("tag"):
        if tag.attrib['k'] == 'addr:street':
            if old_v in tag.attrib['v']:
                fix = tag.attrib['v'].split()
                if old_v == fix[-1]:
                    fix[-1] = new_v
                    new_street_name = ''
                    for word in fix:
                        new_street_name += word + " "
    return new_street_name


# Update City Names:

# In[20]:

#5.1
'''Find all the city names.'''
audit_key(SAMPLE_FILE, 'addr:city')


# In[21]:

#5.2
'''Create a dictionary to correct all the incorract city names.'''
corrected_city_names = {'key_name': 'addr:city',
                        'corrected_values': {"LONDON": "London",
                                            "St Albans": "St. Albans",
                                            "Twickenham": "London",
                                            "Wembley": "London",
                                            "London Borough of Lewisham": "London",
                                            "Royal Borough of Greenwich": "London"
                                          }
                        }


# Update Types of Building:

# In[22]:

#6.1
'''Find all the types of buildings.'''
audit_key(SAMPLE_FILE, 'building')


# In[23]:

#6.2
'''There are no types of buildings that need to be corrected, so no further action will be taken.'''


# Update Types of Amenities: 

# In[24]:

#7.1
'''Find all the types of amenities.'''
audit_key(SAMPLE_FILE, 'amenity')


# In[25]:

#7.2
'''There are no types of amenities that need to be corrected, so no further action will be taken.'''


# Update Speed Limits:

# In[26]:

#8.1
'''Find all the speed limits.'''
audit_key(SAMPLE_FILE, 'maxspeed')


# In[27]:

#8.2
'''Create a dictionary to correct all the incorract speed limits.'''
corrected_speed_limits = {'key_name': 'maxspeed',
                          'corrected_values': {'20': '20 mph',
                                               '30mph': '30 mph',
                                               '40': '40 mph'
                                              }
                         }


# Update Postal Codes:

# In[28]:

#9.1
'''Find all the postal codes.'''
audit_key(SAMPLE_FILE, 'addr:postcode')


# In[29]:

#9.2
'''Create a dictionary to correct all the incorract postal codes.'''
corrected_postal_codes = {'key_name': 'addr:postcode',
                          'corrected_values': {"RG291AL": "RG29 1AL",
                                               "TW196AQ": "TW19 6AQ"
                                              }
                         }


# Update Sources:

# In[30]:

#10.1
'''Find all the sources.'''
audit_key(SAMPLE_FILE, 'source')


# In[31]:

#10.2
'''Create a dictionary to correct all the incorract sources.'''
corrected_sources = {'key_name': 'source',
                     'corrected_values': {'Bing (2015-12-16)': 'Bing',
                                          'Bing 2012': 'Bing',
                                          'Local knowledge': 'Local Knowledge',
                                          'OS Opendata Streetview': 'OS OpenData StreetView',
                                          'OS Street View': 'OS OpenData StreetView',
                                          'OS Streetview': 'OS OpenData StreetView',
                                          'OS_OpenData_Boundary-Line': 'OS OpenData Boundary-Line',
                                          'OS_OpenData_BoundaryLine': 'OS OpenData Boundary-Line',
                                          'OS_OpenData_Streetview': 'OS OpenData StreetView',
                                          'OS_Opendata_StreetView': 'OS OpenData StreetView',
                                          'OS_Opendata_StreetView auto-trace (Tom Chance)': 'OS OpenData StreetView',
                                          'OS_opendata_streetview': 'OS OpenData StreetView',
                                          'Surrey aerial': 'Surrey Aeriel',
                                          'Surrey_Aerial': 'Surrey Aeriel',
                                          'Yahoo - mid-construction!': 'Yahoo',
                                          'Yahoo!': 'Yahoo',
                                          'auto_os_street_view': 'OS OpenData StreetView',
                                          'knowledge': 'Local Knowledge',
                                          'local knowledge': 'Local Knowledge',
                                          'local_knowledge': 'Local Knowledge',
                                          'photo': 'photograph',
                                          'visual_estimate': 'visual estimate',
                                          'yahoo imagery': 'Yahoo',
                                          'yahoo satellite images': 'Yahoo',
                                          'bing': 'Bing',
                                          'survey, bing': 'survey; Bing',
                                          'survey,Bing': 'survey; Bing',
                                          'survey/Bing aerials': 'survey; Bing',
                                          'survey;Bing': 'survey; Bing',
                                          'survey;Bing 2012': 'survey; Bing',
                                          'survey;bing': 'survey; Bing',
                                          'yahoo': 'Yahoo',
                                          'OS_OpenData_StreetView': 'OS OpenData StreetView'
                                         }
                    }
    


# Convert the XML data into csv:

# In[32]:

#11.1
'''Perpare the scheme and all the files that the data will be written to.'''
import schema

schema = {
    'node': {
        'type': 'dict',
        'schema': {
            'id': {'required': True, 'type': 'integer', 'coerce': int},
            'lat': {'required': True, 'type': 'float', 'coerce': float},
            'lon': {'required': True, 'type': 'float', 'coerce': float},
            'user': {'required': True, 'type': 'string'},
            'uid': {'required': True, 'type': 'integer', 'coerce': int},
            'version': {'required': True, 'type': 'string'},
            'changeset': {'required': True, 'type': 'integer', 'coerce': int},
            'timestamp': {'required': True, 'type': 'string'}
        }
    },
    'node_tags': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'required': True, 'type': 'integer', 'coerce': int},
                'key': {'required': True, 'type': 'string'},
                'value': {'required': True, 'type': 'string'},
                'type': {'required': True, 'type': 'string'}
            }
        }
    },
    'way': {
        'type': 'dict',
        'schema': {
            'id': {'required': True, 'type': 'integer', 'coerce': int},
            'user': {'required': True, 'type': 'string'},
            'uid': {'required': True, 'type': 'integer', 'coerce': int},
            'version': {'required': True, 'type': 'string'},
            'changeset': {'required': True, 'type': 'integer', 'coerce': int},
            'timestamp': {'required': True, 'type': 'string'}
        }
    },
    'way_nodes': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'required': True, 'type': 'integer', 'coerce': int},
                'node_id': {'required': True, 'type': 'integer', 'coerce': int},
                'position': {'required': True, 'type': 'integer', 'coerce': int}
            }
        }
    },
    'way_tags': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'id': {'required': True, 'type': 'integer', 'coerce': int},
                'key': {'required': True, 'type': 'string'},
                'value': {'required': True, 'type': 'string'},
                'type': {'required': True, 'type': 'string'}
            }
        }
    }
}

corrected_dictionaries = [corrected_city_names,
                          corrected_speed_limits,
                          corrected_postal_codes,
                          corrected_sources]

key_names = ['addr:city', 'maxspeed', 'addr:postcode', 'source']

OSM_PATH = SAMPLE_FILE #File to use for export
NODES_PATH = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/nodes.csv"
NODE_TAGS_PATH = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/nodes_tags.csv"
WAYS_PATH = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/ways.csv"
WAY_TAGS_PATH = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/ways_tags.csv"
WAY_NODES_PATH = "/Users/Dave/Desktop/Programming/Personal Projects/OpenStreetMap/ways_nodes.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema

NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# In[33]:

#11.2
def correct_k(k):
    index=k.find(':')
    typ=k[:index]
    k=k[index+1:]    
    return k,typ

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    '''Clean and shape node or way XML element to Python dict.'''
    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements
    
    if element.tag=='node':
        for node in NODE_FIELDS:
            try:
                node_attribs[node] = element.attrib[node]
            except:
                node_attribs[node] = '0000000'
            
    if element.tag=='way':
        for way in WAY_FIELDS:
            way_attribs[way]=element.attrib[way]
        
    for tag in element.iter("tag"):
        dic={}
    
        if tag.attrib['k'] == 'addr:street':
            value = tag.attrib['v']
            if value.split()[-1] in corrected_street_types.keys():
                street_type = value.split()[-1]
                dic['value'] = update_street_name(OSM_PATH, street_type, corrected_street_types[street_type])
                tag.attrib['v'] = dic['value']
        
        if tag.attrib['k'] in key_names:
            value = tag.attrib['v']
            for dictionary in corrected_dictionaries:
                if value in dictionary['corrected_values']:
                    dic['value'] = update_value(OSM_PATH, 
                                                tag.attrib['k'], 
                                                value, 
                                                dictionary['corrected_values'][value])
                    tag.attrib['v'] = dic['value']
        
        if problem_chars.search(tag.attrib['k']):
            continue
        
        if element.tag=='node':
            dic['id']=node_attribs['id']
        else:
            dic['id']=way_attribs['id']
        dic['value']=tag.attrib['v']
        
        colon_k=LOWER_COLON.search(tag.attrib['k'])
        if colon_k:
            dic['key'],dic['type']=correct_k(tag.attrib['k'])
            
        else:
            dic['key']=tag.attrib['k']
            dic['type']='regular'
        
        tags.append(dic)
    
    if element.tag=='way':
        position=0
        for nd in element.iter("nd"):
            way_node_dic={}
            way_node_dic['id']=way_attribs['id']
            way_node_dic['node_id']=nd.attrib['ref']
            way_node_dic['position']=position
            position = position + 1
            way_nodes.append(way_node_dic)
        
        
    if element.tag == 'node':
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# In[34]:

#11.3
def get_element(osm_file, tags=('node', 'way', 'relation')):
    '''Yield element if it is the right type of tag.'''
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


# In[35]:

#11.4
def validate_element(element, validator, schema=SCHEMA):
    '''Raise ValidationError if element does not match schema.'''
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_strings = (
            "{0}: {1}".format(k, v if isinstance(v, str) else ", ".join(v))
            for k, v in errors.iteritems()
        )
        raise cerberus.ValidationError(
            message_string.format(field, "\n".join(error_strings))
        )


# In[36]:

#11.5
class UnicodeDictWriter(csv.DictWriter, object):
    '''Extend csv.DictWriter to handle Unicode input.'''
    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# In[34]:

#11.6
def process_map(file_in, validate):
    '''Iteratively process each XML element and write to csv(s).'''
    with codecs.open(NODES_PATH, 'w') as nodes_file,          codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file,          codecs.open(WAYS_PATH, 'w') as ways_file,          codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file,          codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])
                    
if __name__ == '__main__':
    process_map(OSM_PATH, validate=True)


# Websites used to help complete this project:
# https://www.udacity.com/
# http://stackoverflow.com/
# https://wiki.openstreetmap.org/wiki/Main_Page
# https://www.python.org/
# https://www.sqlite.org/index.html
# https://www.tutorialspoint.com/index.htm
# http://www.w3schools.com/

# In[ ]:



