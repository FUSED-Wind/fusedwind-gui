# -*- coding: utf-8 -*-
from openmdao.main.vartree import VariableTree

import os

from flask import Flask, request, render_template, flash
from wtforms.widgets import TextArea
from flask.ext.mail import Message, Mail
from flask.ext.bower import Bower
from flask import Blueprint, request, abort, jsonify, redirect, render_template
from flask_wtf.file import FileField
from flask_bootstrap import Bootstrap
from flask_appconfig import AppConfig
from flask import Response
from flask_wtf import Form, RecaptchaField

from functools import wraps
from werkzeug import secure_filename
from wtforms.widgets.core  import  html_params
from wtforms import widgets

import numpy as np

from jinja2 import evalcontextfilter, Markup, escape

from webcomponent import *

import json
import yaml

## Silly comment to test the RSS feed

## Configuring the Flask app ---------------------------------------------------
app = Flask(__name__)
configfile=None
AppConfig(app, configfile)  # Flask-Appconfig is not necessary, but
                            # highly recommend =)
                            # https://github.com/mbr/flask-appconfig

Bootstrap(app)
Bower(app) # Usefull to use bower-components

# in a real app, these should be configured through Flask-Appconfig
app.config['SECRET_KEY'] = 'devkey'

## Handeling Forms -------------------------------------------------------------
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
        html.append(u'<input class="form-control" id="%s" name="%s" type="text" value="%s">' % (field.name, field.name, field.data))
        html.append(u'<span class="input-group-addon">%s</span>'%(units))
        html.append(u'</div>')
        return u''.join(html)
    myfield.__name__ = name
    return myfield

def make_field(k,v):
    """Create the widget of the field, adds the units when necessary
    """
    field = type_fields[v['type']]
    if 'units' in v:
        class MyField(field):
            widget = unitfield(v['units'], k)
        MyField.__name__ = 'Field'+k
        return MyField(k, **prep_field(v))
    return field(k, **prep_field(v))

def WebGUIForm(dic, run=False):
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

    # sorting the keys alphabetically
    skeys = dic.keys()
    skeys.sort()
    for k in skeys:
        v = dic[k]
        setattr(MyForm, k, make_field(k,v))

    if run: # Add the run button
        setattr(MyForm, 'submit', SubmitField("Run"))

    return MyForm

try:
    from bokeh.embed import components
    from bokeh.plotting import figure
    from bokeh.charts import  Line
    from bokeh.resources import INLINE
    from bokeh.templates import RESOURCES
    from bokeh.util.string import encode_utf8
    from bokeh.charts import Donut, output_file, show
    use_bokeh = True
except:
    print 'Bokeh hasnt been installed properly'
    use_bokeh = False


if use_bokeh:
    def prepare_plot(func, *args, **kwargs):
        fig = figure()
        fig = func(fig, *args, **kwargs)
        # Create a polynomial line graph

        # Configure resources to include BokehJS inline in the document.
        # For more details see:
        #   http://bokeh.pydata.org/en/latest/docs/reference/resources_embedding.html#module-bokeh.resources
        plot_resources = RESOURCES.render(
            js_raw=INLINE.js_raw,
            css_raw=INLINE.css_raw,
            js_files=INLINE.js_files,
            css_files=INLINE.css_files,
        )

        # For more details see:
        #   http://bokeh.pydata.org/en/latest/docs/user_guide/embedding.html#components
        script, div = components(fig, INLINE)
        return script, div, plot_resources


def build_hierarchy(cpnt, sub_comp_data, asym_structure=[], parent=''):

    for name in cpnt.list_components():
        comp = getattr(cpnt, name)
        cname = comp.__class__.__name__
        sub_comp_data[cname] = {}

        asym_structure.append({
            'text':cname,
            'href':'#collapse-%s'%(cname)})

        inout = traits2json(comp)
        sub_comp_data[cname]['params'] = inout
        if hasattr(comp, "plot"):
            c_script, c_div, c_plot_resources = prepare_plot(comp.plot)
            sub_comp_data[cname]['plot'] = {'script': c_script, 'div': c_div, 'resources': c_plot_resources}

        if isinstance(comp, Assembly):

            sub_comp_data, sub_structure = build_hierarchy(comp, sub_comp_data, [], name)
            asym_structure[-1]['nodes'] = sub_structure

    return sub_comp_data, asym_structure

## Handeling file upload -------------------------------------------------------
def _handleUpload(files):
    """Handle the files uploaded, put them in a tmp directory, read the content
    using a yaml library, and return its content as a python object.
    """
    if not files:
        return None

    outfiles = []

    for upload_file in files.getlist('files[]'):
        upload_file.save('/tmp/' + upload_file.filename)

        with open('/tmp/'+upload_file.filename, 'r') as f:
            inputs = yaml.load(f)

        print inputs

        outfiles.append({
            'filename': upload_file.filename,
            'content': inputs
        })

    return outfiles


## Views -----------------------------------------------------------------------
@app.route('/')
def hello():
    """ Welcoming page
    """
    provider = str(os.environ.get('PROVIDER', 'world'))
    return render_template('index.html', form={'hello':'world'})



@app.route('/upload/', methods=['POST'])
def upload():
    """Take care of the reception of the file upload. Return a json file
    to be consumbed by a jQuery function
    """
    try:
        files = request.files
        uploaded_files = _handleUpload(files)
        return jsonify({'files': uploaded_files})
    except:
        raise
        return jsonify({'status': 'error'})


def get_io_dict(cpnt):
    io = traits2json(cpnt)
    out = {}
    for k in io['inputs']:
        out[k] = serialize(getattr(cpnt, k))
    for k in io['outputs']:
        out[k] = serialize(getattr(cpnt, k))
    return out


def serialize(thing):
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

    print thing, thing.__class__
    return '??_' +  str(thing.__class__)


def webgui(cpnt, app=None):
    cpname = cpnt.__class__.__name__
    if app == None:
        app = start_app(cpname)


    def download():
        out = get_io_dict(cpnt)
        r = yaml.dump(out, default_flow_style=False)
        #print r
        #print out

        return Response(r, content_type='text/yaml; charset=utf-8')

    download.__name__ = cpname+'_download'
    app.route('/'+cpname+'/download/', methods=['GET'])(download)

    def myflask():
        io = traits2json(cpnt)
        form_inputs = WebGUIForm(io['inputs'], run=True)()

        assembly_structure = [{'text':cpname,
                               'nodes':[]}]

        inputs =  request.form.to_dict()

        for k in inputs.keys():
            if k in io['inputs']: # Loading only the inputs allowed
                setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))

        sub_comp_data = {}
        if isinstance(cpnt, Assembly):

            sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
            assembly_structure[0]['nodes'] = structure

        if request.method == 'POST': # Receiving a POST request

            inputs =  request.form.to_dict()

            for k in inputs.keys():
                if k in io['inputs']: # Loading only the inputs allowed
                    setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))

            cpnt.run()
            io = traits2json(cpnt)
            sub_comp_data = {}
            if isinstance(cpnt, Assembly):

                sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
                assembly_structure[0]['nodes'] = structure
                outputs = traits2json(cpnt)['outputs']

            try:
                script, div, plot_resources = prepare_plot(cpnt.plot)
            except:
                # TODO: gracefully inform the user of why he doesnt see his plots
                script, div, plot_resources = None, None, None


            return render_template('webgui.html',
                        inputs=WebGUIForm(io['inputs'], run=True)(MultiDict(inputs)),
                        outputs=outputs,
                        name=cpname,
                        plot_script=script, plot_div=div, plot_resources=plot_resources,
                        sub_comp_data=sub_comp_data,
                        assembly_structure=assembly_structure)


        # Show the standard form
        return render_template('webgui.html',
            inputs=form_inputs, outputs=None,
            name=cpname,
            plot_script=None, plot_div=None, plot_resources=None,
            sub_comp_data=sub_comp_data,
            assembly_structure=assembly_structure)

    myflask.__name__ = cpname
    app.route('/'+cpname, methods=['GET', 'POST'])(myflask)
    return app


from openmdao.main.api import set_as_top
from SEAM.seam_assemblies import SEAMAssembly


webgui(set_as_top(SEAMAssembly()), app)
#try:
from wisdem.lcoe.lcoe_csm_assembly import lcoe_csm_assembly
webgui(set_as_top(lcoe_csm_assembly()), app)
#except:
#    print 'WARNING: WISDEM not installed'

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.


    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
