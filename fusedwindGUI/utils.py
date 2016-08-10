# -*- coding: utf-8 -*-

from openmdao.main.vartree import VariableTree
from openmdao.main.api import set_as_top, Assembly
from openmdao.lib.drivers.api import DOEdriver
from openmdao.lib.doegenerators.api import Uniform
import os
import sys
import platform
from flask import flash, make_response
from flask import request, jsonify, redirect, render_template
from flask_wtf import Form
from wtforms import SelectField
import numpy as np
import datetime as dt
from webcomponent import *
from utils import *
from collections import OrderedDict
import json
import yaml
import types
from fusedwindGUI import app



def finditem(obj, key): 
	""" 
    This function performs a deep search in a dictionary for a value associated with any key.
	Params: 
        @obj is the dictionary
        @key is the key you want the value for 
	Returns:
        @item, is the value associated with the key parameter     
	"""
	if key in obj: 
		return obj[key]
	for k, v in obj.items():
	    if isinstance(v, dict):
	        item = finditem(v, key)
	        if item is not None:
	            return item



def makePretty(myList):
    """ 
    It modifies (mutative) variable names and descriptions to be more human readable. 
    Params:
        @myList is a list of dictionaries -- each dictionary represents an input/output
    Returns:
        None

    """
    for myDict in myList:
        if 'name' in myDict.keys():
            myDict['name'] = myDict['name'].replace("_"," ").title()
        if 'desc' in myDict.keys():
            myDict['desc'] = myDict['desc'][0].upper()+myDict['desc'][1:]


import types
NumberTypes = (types.IntType,
    types.LongType,
    types.FloatType,
    types.ComplexType)
def form_names(varList):
	""" 
    Used in the compare results feature. Populates the drop down menu for inputs
    Params: 
        @varList
    Return:
        - Variables to populate drop down form. These variables include number types only

	"""

	return [varList[:][i]['name'] for i in range(len(varList)) if (isinstance(varList[i]['state'], NumberTypes) and varList[i]['state'] is not True)]

def prettyNum(num):
	""" 
	Returns a prettier version of a number. Includes truncations
    Params:
        @num is the input, unmodified number
    Returns
        - Formatted number

	"""
	anum = abs(num)
	if(anum > 1e4 or anum < 1e-2):
	    return "%.2e" % num
	elif(anum > 10.0):
	    # this just means to print the 2 values after the decimal point for
	    # float
	    return "%.2f" % num
	elif(anum < 1.0):
	    return "%.4f" % num
	else:
	    return "%.3f" % num

# Handling Forms -------------------------------------------------------------
def unitfield(units, name):
    """A simple widget generating function. The nested function is necessary in order
    to have a different function name for each widget. This whole code should
    really be moved to the template side, but that would require passing the units
    along in the form
    """
    def myfield(field, ul_class='', **kwargs):
        field_id = kwargs.pop('id', field.id)
        html = []
        html.append(u'<div class="input-group">')
        html.append(
            u'<input class="form-control" id="%s" name="%s" type="text" value="%s">' %
            (field.name, field.name, field.data))
        html.append(u'<span class="input-group-addon">%s</span>' % (units))
        html.append(u'</div>')

        return u''.join(html)
    myfield.__name__ = name
    return myfield


def make_field(k, v):
    """Create the widget of the field, adds the units when necessary
    """
    field = type_fields[v['type']]
    if 'units' in v:
        class MyField(field):
            widget = unitfield(v['units'], k)
        MyField.__name__ = 'Field' + k
        return MyField(k, **prep_field(v))
    return field(k, **prep_field(v))



def build_hierarchy(cpnt, sub_comp_data, asym_structure=[], parent=''):
    for name in cpnt.list_components():
        comp = getattr(cpnt, name)

        cname = comp.__class__.__name__
        if cname != 'Driver':
            sub_comp_data[cname] = {}

            asym_structure.append({
                'text': cname,
                'href': '#collapse-%s' % (cname)})

            tmp = get_io_dict(comp)

            sub_comp_data[cname]['params'] = tmp['outputs'] + tmp['inputs']
            # no plots for now since bootstrap-table and bokeh seem to be in
            # conflict
            if hasattr(comp, "plot"):
                c_script, c_div = prepare_plot(comp.plot)
                sub_comp_data[cname]['plot'] = {
                    'script': c_script, 'div': c_div}

            if isinstance(comp, Assembly):

                sub_comp_data, sub_structure = build_hierarchy(
                    comp, sub_comp_data, [], name)
                asym_structure[-1]['nodes'] = sub_structure

    return sub_comp_data, asym_structure

def traits2json(cpnt):
    """
    Get the traits information about the component and return a json dictionary
    Params:
        @cpnt: the openMDAO component
    Returns:
        @out is a json dictionary with component trait info
    """

    # I/O are separated in two lists with a dict for each variable
    out = {'inputs': [], 'outputs': []}
    for ty, se in zip(['inputs', 'outputs'],
                      [set(cpnt.list_inputs()).difference(Assembly().list_inputs()),
                       set(cpnt.list_outputs()).difference(Assembly().list_outputs())]):
        for s in se:
            t = cpnt.get_trait(s)
            var = {'name': s}
            var['type'] = t.trait_type.__class__.__name__
            for d in [
                'iotype',
                'desc',
                'units',
                'high',
                'low',
                'values',
                    'group']:
                val = getattr(t, d)
                if not val is None:
                    var[d] = val
            var['state'] = getattr(cpnt, s)
            out[ty].append(var)
    return out


def get_io_dict(cpnt):
    """
    Params:
        @cpnt: openMDAO component
    Returns:
        @io: json dictionary with entries serialized
    """
    io = traits2json(cpnt)
    for i, k in enumerate(io['inputs']):
        io['inputs'][i]['state'] = serialize(getattr(cpnt, k['name']))
    for i, k in enumerate(io['outputs']):
        io['outputs'][i]['state'] = serialize(getattr(cpnt, k['name']))
    return io


def serialize(thing):
    """
    Params:
        @thing to serialize
    Returns:
        @thing after serialization in form of list, float, dictionary, float, int, or string
    """
    if isinstance(thing, np.ndarray):  
        return thing.tolist()  
    elif isinstance(thing, np.float64):
        return float(thing)  
    elif isinstance(thing, Component):
        return get_io_dict(thing)  
    elif isinstance(thing, VariableTree):
        out = {}
        for k in thing.list_vars():
            out[k] = serialize(getattr(thing, k))
        return out
    elif isinstance(thing, float):
        return thing
    elif isinstance(thing, int):
        return thing
    elif isinstance(thing, str):
        return thing

    return '??_' + str(thing.__class__)


def to_unicode(dic):
    """
    Params:
        @dic is a dictionary
    Returns:
        @new is new dictionary with values in unicode
    """
    new = {}
    for k, v in dic.iteritems():
        new[k] = unicode(v)
    return new


# Palette of colors from green to blue
greenBluePalette = ['#00E504',
'#00E306',
'#00E109',
'#00E00B',
'#00DE0E',
'#00DD11',
'#00DB13',
'#00DA16',
'#00D818',
'#00D71B',
'#00D51E',
'#00D420',
'#00D223',
'#00D126',
'#00CF28',
'#00CE2B',
'#00CC2D',
'#00CB30',
'#00C933',
'#00C835',
'#00C638',
'#00C53B',
'#00C33D',
'#00C140',
'#00C042',
'#00BE45',
'#00BD48',
'#00BB4A',
'#00BA4D',
'#00B84F',
'#00B752',
'#00B555',
'#00B457',
'#00B25A',
'#00B15D',
'#00AF5F',
'#00AE62',
'#00AC64',
'#00AB67',
'#00A96A',
'#00A86C',
'#00A66F',
'#00A572',
'#00A374',
'#00A177',
'#00A079',
'#009E7C',
'#009D7F',
'#009B81',
'#009A84',
'#009886',
'#009789',
'#00958C',
'#00948E',
'#009291',
'#009194',
'#008F96',
'#008E99',
'#008C9B',
'#008B9E',
'#0089A1',
'#0088A3',
'#0086A6',
'#0185A9']