# -*- coding: utf-8 -*-

import os

from flask import Flask, request, render_template, flash
from wtforms.widgets import TextArea
from flask_bootstrap import Bootstrap
from flask_appconfig import AppConfig
from flask_wtf import Form, RecaptchaField
from flask.ext.mail import Message, Mail
from flask.ext.bower import Bower
import numpy as np
import re

from jinja2 import evalcontextfilter, Markup, escape

import yaml

app = Flask(__name__)
configfile=None
AppConfig(app, configfile)  # Flask-Appconfig is not necessary, but
                            # highly recommend =)
                            # https://github.com/mbr/flask-appconfig


Bootstrap(app)
Bower(app) # Usefull to use bower-components

# in a real app, these should be configured through Flask-Appconfig
app.config['SECRET_KEY'] = 'devkey'

@app.route('/')
def hello():
    provider = str(os.environ.get('PROVIDER', 'world'))
    return render_template('index.html', form={'hello':'world'})



#from webcomponent import deploy, start_app, register_Component, webgui
from paraboloid import Paraboloid

from SEAMTower.SEAMTower import SEAMTower
from SEAMCosts.SEAMCAPEX import SEAMCAPEX
from webcomponent import *
from flask_wtf.file import FileField
from werkzeug import secure_filename
from wtforms.widgets.core  import  html_params

from bokeh.charts import Donut, output_file, show
def donuts(fig):
    # dict, OrderedDict, lists, arrays and DataFrames are valid inputs
    xyvalues = [[2., 5., 3., 2.], [4., 1., 4., 0.], [6., 4., 3., 0.]]
    donut = Donut(xyvalues, ['cpu1', 'cpu2', 'cpu3', 'cpu4'])
    return donut

def unitfield(units, name):
    def myfield(field, ul_class='', **kwargs):
        field_id = kwargs.pop('id', field.id)
        html = [u'<div id="%s">' % (field_id)]
        html.append(u'<div class="input-group">')
        html.append(u'<input class="form-control" id="%s" name="%s" type="text" value="%s">' % (field_id, field.name, field.data))
        html.append(u'<span class="input-group-addon">%s</span>'%(units))
        html.append(u'</div>')
        html.append(u'</div>')
        return u''.join(html)
    myfield.__name__ = name
    return myfield

def make_field(k,v):
    field = type_fields[v['type']]
    if 'units' in v:
        class MyField(field):
            widget = unitfield(v['units'], k)
        MyField.__name__ = 'Field'+k
        return MyField(k, **prep_field(v))
    return field(k, **prep_field(v))



from wtforms import widgets
def WebGUIForm(dic, run=False):
    """Automagically generate the form from a FUSED I/O dictionary.
    TODO:
    * Add type validators
    * Add low/high validators
    * Add units nice looking extension using 'input-group-addon'
     (http://getbootstrap.com/components/#input-groups)
    """
    #field_dict = {k:type_fields[v['type']](k, **prep_field(v)) for k,v in dic.iteritems()}
    #if run: # Add the submit button
    #    field_dict['submit'] = SubmitField("Send")

    # 9th level python magic to dynamically create classes, don't try it at home kiddo...
    #MyForm = type('magicform', (Form,), field_dict)

    class MyForm(Form):
        pass


    # sorting the keys alphabetically
    skeys = dic.keys()
    skeys.sort()
    for k in skeys:
        v = dic[k]
        try:
            setattr(MyForm, k, make_field(k,v))
            #setattr(MyForm, k, type_fields[v['type']](k, **prep_field(v)))
        except:
            pass

    if run: # Add the run button
        setattr(MyForm, 'submit', SubmitField("Run"))

    #setattr(MyForm, 'widget', widgets.TableWidget(with_table_tag=True))

    return MyForm

class FormLoadInputFile(Form):
    upload = FileField('Input File')
    load = SubmitField('Load Inputs')



from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.charts import  Line
from bokeh.resources import INLINE
from bokeh.templates import RESOURCES
from bokeh.util.string import encode_utf8

def test_plot(fig, s,t, title="", color='#000000', _from=0, to=100):
    xyvalues = OrderedDict(

    )
    fig = Line(s, t, color=color, line_width=2, xlabel='Height [m]', ylabel='Mass [kg]',
        title='Tower mass distribution')
    return fig


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

#from wtforms import Form, TextField, widgets

test_ass = [{
        'text': "Parent 1",
        'nodes': [{
            'text': "Child 1",
            'nodes': [
                {'text': "Grandchild 1"},
                {'text': "Grandchild 2"}]},
          {'text': "Child 2"}]},
      {'text': "Parent 2"},
      {'text': "Parent 3"},
      {'text': "Parent 4"},
      {'text': "Parent 5"}]



def webgui(cpnt, app=None):
    cpname = cpnt.__class__.__name__
    if app == None:
        app = start_app(cpname)

    def myflask():
        io = traits2json(cpnt)
        form_load = FormLoadInputFile()
        form_inputs = WebGUIForm(io['inputs'], run=True)()
        form_outputs = WebGUIForm(io['outputs'])()

        assembly_structure = [{'text':cpname,
                               'nodes':[]}]
        if request.method == 'POST': # Receiving a POST request

            try: # Trying to load the file
                filename = secure_filename(form_load.upload.data.filename)
                if filename is not None:
                    form_load.upload.data.save('/tmp/' + filename)
                    with open('/tmp/'+filename, 'r') as f:
                        inputs = yaml.load(f)

                return render_template('webgui.html',
                            inputs=WebGUIForm(io['inputs'], run=True)(MultiDict(inputs)),
                            outputs=None, load=form_load, name=cpname, plot_script=None,
                            assembly_structure=assembly_structure)

            except: # no files are passed, using the form instead
                inputs =  request.form.to_dict()

                for k in inputs.keys():
                    if k in io['inputs']: # Loading only the inputs allowed
                        setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))

                cpnt.run()
                outputs = traits2json(cpnt)['outputs']

                script, div, plot_resources = prepare_plot(cpnt.plot)

                # sub-component data
                sub_comp_data = {}
                if isinstance(cpnt, Assembly):
                    for name in cpnt.list_components():
                        comp = getattr(cpnt, name)
                        cname = comp.__class__.__name__
                        sub_comp_data[cname] = {}

                        assembly_structure[0]['nodes'].append({
                            'text':cname,
                            'href':'#collapse-%s'%(cname)})

                        inout = traits2json(comp)
                        sub_comp_data[cname]['params'] = inout
                        if hasattr(comp, "plot"):
                            c_script, c_div, c_plot_resources = prepare_plot(comp.plot)
                            sub_comp_data[cname]['plot'] = {'script': c_script, 'div': c_div, 'resources': c_plot_resources}

                return render_template('webgui.html',
                            inputs=WebGUIForm(io['inputs'], run=True)(MultiDict(inputs)),
                            outputs=outputs,
                            load=form_load,
                            name=cpname,
                            plot_script=script, plot_div=div, plot_resources=plot_resources,
                            sub_comp_data=sub_comp_data,
                            assembly_structure=assembly_structure)



        # Show the standard form
        return render_template('webgui.html',
            inputs=form_inputs, outputs=None,
            load=form_load, name=cpname,
            plot_script=None, plot_div=None, plot_resources=None,
            assembly_structure=assembly_structure)

    myflask.__name__ = cpname
    app.route('/'+cpname, methods=['GET', 'POST'])(myflask)
    return app


webgui(SEAMTower(20), app)
webgui(SEAMCAPEX(), app)


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
