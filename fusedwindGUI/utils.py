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
	Parameters: 
	Obj -- going to be a dictionary; 
	key -- key of a dictionary entry.
	Returns: item -- a value associated with a key

	This function will perform a deep search in a dictionary
	for a value associated with a key        
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
    This function takes in a list of dictionaries, where each dictionary represents an input/output
    It modifies variable names and descriptions to be more human readable. 

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
	Returns the variables to populate the drop down forms. It has to be a number type to populate the forms

	"""

	return [varList[:][i]['name'] for i in range(len(varList)) if isinstance(varList[i]['state'], NumberTypes)]

def prettyNum(num):
	""" 
	Returns a prettier version of a number. Includes truncations

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


def WebGUIForm(dic, run=False, sens_flag=False):
    """Automagically generate the form from a FUSED I/O dictionary.
    TODO:
    [ ] Add type validators
    [ ] Add low/high validators
    [x] Add units nice looking extension using 'input-group-addon'
             (http://getbootstrap.com/components/#input-groups)
    [ ] Move the units formating into the html code directly
    """

    class MyForm(Form):
        pass


    for k in dic.keys():
        v = dic[k]
        setattr(MyForm, k, make_field(k, v))


    if sens_flag:
        for k in dic.keys():
            v = dic[k]
            if not 'group' in v.keys():
                v['group'] = 'Other'
            elif v['group'] is None:
                v['group'] = 'Other'
            if v['type'] == 'Float':
                kselect = "select." + k
                newdic = {
                    'default': False,
                    'state': False,
                    'desc': kselect,
                    'type': 'Bool',
                    'group': v['group']}
                setattr(MyForm, kselect, make_field(kselect, newdic))
                klow = "low." + k
                setattr(MyForm, klow, make_field(klow, v))
                khigh = "high." + k
                setattr(MyForm, khigh, make_field(khigh, v))
        setattr(MyForm, "select.alpha", make_field("select.alpha", newdic))

    if run:  # Add the run button
        setattr(MyForm, 'submit', SubmitField("Run"))

    return MyForm


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
            # tmp = dict(tmp)
            # makePretty(tmp['outputs'])
            # makePretty(tmp['inputs'])

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
    """Get the traits information about the component and return a json dictionary"""

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
    io = traits2json(cpnt)

    for i, k in enumerate(io['inputs']):
        io['inputs'][i]['state'] = serialize(getattr(cpnt, k['name']))
    for i, k in enumerate(io['outputs']):
        io['outputs'][i]['state'] = serialize(getattr(cpnt, k['name']))
    return io


def serialize(thing):
    if isinstance(thing, np.ndarray):  # numpy ndarray
        return thing.tolist()  # returns as list
    elif isinstance(thing, np.float64):
        return float(thing)  # returns as float
    elif isinstance(thing, Component):
        return get_io_dict(thing)  # returns dictionary of i/o
    elif isinstance(thing, VariableTree):
        out = {}
        for k in thing.list_vars():
            # returns dictionary after recursion
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
    new = {}
    for k, v in dic.iteritems():
        new[k] = unicode(v)
    return new
