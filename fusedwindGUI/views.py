# -*- coding: utf-8 -*-
from openmdao.main.vartree import VariableTree
from openmdao.main.api import set_as_top, Assembly
from openmdao.lib.drivers.api import DOEdriver
from openmdao.lib.doegenerators.api import FullFactorial, Uniform

import os

from flask import Flask, flash, request, render_template, make_response
from wtforms.widgets import TextArea
from wtforms import SelectField
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

from fusedwindGUI import app, session

debug = True # GNS 2015 09 08 - lots of debugging info - feel free to turn off or delete
debug = False

## Handling Forms -------------------------------------------------------------

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

    # sorting the keys alphabetically
    skeys = dic.keys()
    skeys.sort()

    for k in skeys:
        v = dic[k]
        setattr(MyForm, k, make_field(k,v))

    if sens_flag:
        for k in skeys:
            v = dic[k]
            if v['type'] == 'Float':
                kselect = "select." + k
                newdic = {'default':False, 'state':False, 'desc':kselect, 'type':'Bool', 'group':v['group']}
                setattr(MyForm, kselect, make_field(kselect,newdic))
                klow = "low." + k
                setattr(MyForm, klow, make_field(klow, v))
                khigh = "high." + k
                setattr(MyForm, khigh, make_field(khigh, v))

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
        #   http://bokeh.pydata.org/en/latest/docs/user_guide/embed.html#components  (as of 2015 09 28)
        script, div = components(fig, INLINE)
        return script, div


def build_hierarchy(cpnt, sub_comp_data, asym_structure=[], parent=''):
    #print 'In build_hierarchy...'
    
    for name in cpnt.list_components():
        comp = getattr(cpnt, name)
        #if debug:
        #    print '  bld_hierarchy: {:} : {:}'.format(name, comp) #gns
            
        cname = comp.__class__.__name__
        if cname <> 'Driver':
            sub_comp_data[cname] = {}

            asym_structure.append({
                'text':cname,
                'href':'#collapse-%s'%(cname)})

            tmp = get_io_dict(comp)
            sub_comp_data[cname]['params'] = tmp['inputs'] + tmp['outputs']
            # no plots for now since bootstrap-table and bokeh seem to be in conflict
            if hasattr(comp, "plot"):
                c_script, c_div = prepare_plot(comp.plot)
                sub_comp_data[cname]['plot'] = {'script': c_script, 'div': c_div}

            if isinstance(comp, Assembly):

                sub_comp_data, sub_structure = build_hierarchy(comp, sub_comp_data, [], name)
                asym_structure[-1]['nodes'] = sub_structure

    return sub_comp_data, asym_structure

## Handling file upload -------------------------------------------------------

def _handleUpload(files):
    """Handle the files uploaded, put them in a tmp directory, read the content
    using a yaml library, and return its content as a python object.
    """
    if not files:
        return None

    outfiles = []
    import tempfile
    tmpdir = tempfile.gettempdir()
    for upload_file in files.getlist('files[]'):
        upload_file.save(os.path.join(tmpdir, upload_file.filename))

        with open(os.path.join(tmpdir, upload_file.filename), 'r') as f:
            inputs = yaml.load(f)

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
        response =  jsonify({'files': uploaded_files})
        # fix for legacy browsers
        response.headers['Content-Type'] = 'text/plain'
        return response
    except:
        raise
        return jsonify({'status': 'error'})


def traits2json(cpnt):
    """Get the traits information about the component and return a json dictionary"""

    # I/O are separated in two lists with a dict for each variable
    out = {'inputs':[], 'outputs':[]}
    for ty, se in zip(['inputs', 'outputs'],
                    [set(cpnt.list_inputs()).difference(Assembly().list_inputs()),
                     set(cpnt.list_outputs()).difference(Assembly().list_outputs())]):
        for s in se:
            t = cpnt.get_trait(s)
            var = {'name':s}
            var['type'] = t.trait_type.__class__.__name__
            for d in ['iotype','desc', 'units', 'high', 'low','values', 'group']:
                val = getattr(t, d)
                if not val == None:
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

    return '??_' +  str(thing.__class__)

cpnt = None
desc = ''
analysis = 'Individual Analysis'

def webgui(app=None):

    def configure():
        """ Configuration page
        """

        global cpnt
        global desc
        global analysis

        class ConfigForm(Form):
            pass

        models = [{'name': 'Model Selection',
                   'choices': ['Tier 1 Full Plant Analysis: WISDEM CSM', 'Tier 2 Full Plant Analysis: WISDEM/DTU Plant']},
                  {'name': 'Analysis Type',
                   'choices': ['Individual Analysis', 'Sensitivity Analysis']}]
        for dic in models:
            name = dic['name']
            choices = [(val, val) for val in dic['choices']]
            setattr(ConfigForm, name, SelectField(name, choices=choices))


        if request.method == 'POST': # Receiving a POST request

            inputs =  request.form.to_dict()

            if inputs['Model Selection'] == 'Tier 1 Full Plant Analysis: WISDEM CSM':
                # 2015 09 28: move desc assignment AFTER import etc. so it doesn't get changed if import fails - GNS
                import sys
                try:
                    from wisdem.lcoe.lcoe_csm_assembly import lcoe_csm_assembly
                    cpnt = set_as_top(lcoe_csm_assembly())
                    desc = "The NREL Cost and Scaling Model (CSM) is an empirical model for wind plant cost analysis based on the NREL cost and scaling model."
                except:
                    print 'lcoe_csm_assembly could not be loaded!'
                    return render_template('error.html', 
                                   errmssg='{:} : lcoe_csm_assembly could not be loaded!'.format(inputs['Model Selection'])) 

                try:
                    sys.path.append('d:/systemsengr/fusedwind-gui/src/plant-costsse/src')
                    sys.stderr.write("\n*** NOTE: views.py importing plant-costsse (because setup.py didn't install it properly)\n\n")
                except:
                    print 'plant-costsse could not be loaded!'
                    return render_template('error.html', 
                                   errmssg='{:} : plant-costsse could not be loaded!'.format(inputs['Model Selection'])) 
                    
            else:
                try:
                    from wisdem.lcoe.lcoe_se_seam_assembly import create_example_se_assembly
                    lcoe_se = create_example_se_assembly('I', 0., True, False, False,False,False, '')
                    cpnt = lcoe_se
                    desc = "The NREL WISDEM / DTU SEAM integrated model uses components across both model sets to size turbine components and perform cost of energy analysis."
                except:
                    print 'lcoe_se_seam_assembly could not be loaded!'
                    return render_template('error.html', 
                                   errmssg='{:} : lcoe_se_seam_assembly could not be loaded!'.format(inputs['Model Selection'])) 

            analysis = inputs['Analysis Type']
            myflask(True)

            return render_template('configure.html',
                            config=ConfigForm(MultiDict()),
                            config_flag = True)
        
        else:
            return render_template('configure.html',
                config=ConfigForm(MultiDict()),
                config_flag = False)
        
    configure.__name__ = 'configure'
    app.route('/configure.html', methods=['Get', 'Post'])(configure)

    #---------------
    
    def download():
        out = get_io_dict(cpnt)
        params = {}
        for param in out['inputs']:
            params[param['name']] = param['state']
        r = yaml.dump(params, default_flow_style=False)

        response = make_response(r)
        response.headers["Content-Disposition"] = "attachment; filename=fused_inputs.yaml"
        return response
        # return Response(r, content_type='text/yaml; charset=utf-8', filename='books.csv')

    download.__name__ = 'analysis_download'
    app.route('/analysis/download', methods=['GET'])(download)

    #---------------
    
    def download_full():

        if not 'gui_recorder' in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            flash('No case recorded - NO gui_recorder in component!')
            return 'No case recorded - NO gui_recorder in component!'
            
        if len(cpnt.gui_recorder.keys()) == 0:
            record_case()
            r = cpnt.gui_recorder['recorder']

        r = yaml.dump(cpnt.gui_recorder['recorder'], default_flow_style=False)
        response = make_response(r)
        response.headers["Content-Disposition"] = "attachment; filename=fused_model.yaml"
        return response
        # return Response(r, content_type='text/yaml; charset=utf-8', filename='books.csv')

    download_full.__name__ = 'analysis_download_full'
    app.route('/analysis/download_full', methods=['GET'])(download_full)

    #---------------
    
    def record_case():

        if not 'gui_recorder' in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            flash('No case recorded - NO gui_recorder in component!')
            return 'No case recorded - NO gui_recorder in component!'
            
        if 'counter' in cpnt.gui_recorder.keys():
            cpnt.gui_recorder['counter'] += 1
        else:
            cpnt.gui_recorder['counter'] = 1

        out = get_io_dict(cpnt)
        cmp_data, _ = build_hierarchy(cpnt, {}, [])
        params = {}
        top_name = cpnt.__class__.__name__
        params[top_name] = {}
        for param in out['inputs'] + out['outputs']:
            pname = param['name']
            params[top_name][pname] = param['state']

        for cmp_name in cmp_data:
            params[cmp_name] = {}
            for param in cmp_data[cmp_name]['params']:
                pname = param['name']
                params[cmp_name][pname] = param['state']

        try:
            cpnt.gui_recorder['recorder']['case%i' % cpnt.gui_recorder['counter']] = params
        except:
            cpnt.gui_recorder['recorder'] = {}
            cpnt.gui_recorder['recorder']['case%i' % cpnt.gui_recorder['counter']] = params
        flash('recorded case! %i' % cpnt.gui_recorder['counter'], category='message')
        return 'Case %i recorded successfully!' % cpnt.gui_recorder['counter']

    record_case.__name__ = 'analysis_record_case'
    app.route('/analysis/record_case', methods=['POST'])(record_case)

    #---------------
    
    def clear_recorder():

        if not 'gui_recorder' in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            flash('No recorder to clear!', category='message')
            return 'No recorder to clear!'
            
        cpnt.gui_recorder = {}
        flash('Recorder cleared!', category='message')
        return 'All cases cleared successfully!'

    clear_recorder.__name__ = 'analysis_clear_recorder'
    app.route('/analysis/clear_recorder', methods=['POST'])(clear_recorder)

    #---------------
    
    def myflask(config_flag=False):

        if analysis == 'Individual Analysis':
            sens_flag=False
        else:
            sens_flag=True

        cpname = cpnt.__class__.__name__

        if cpnt is None:
            print '\n*** WARNING: component is None\n'
            failed_run_flag = 'WARNING: component is None in myflask() - try another model(?)'
            
            return render_template('error.html', 
                                   errmssg=failed_run_flag, 
                                   sens_flag=sens_flag)            
            
        io = traits2jsondict(cpnt)

        # Create input groups
        group_list = ['Global']
        group_dic = {}
        skeys = io['inputs'].keys()
        skeys.sort()
        for k in skeys:
            v = io['inputs'][k]
            if 'group' in v.keys():
                if v['group'] not in group_list:
                    group_list.append(v['group'])
                group_dic[k] = v['group']
            else: group_dic[k] = 'Global'
        group_list.sort()
        group_list.insert(0, group_list.pop(group_list.index('Global')))

        # Build assembly hierarchy
        assembly_structure = [{'text':cpname,
                               'nodes':[]}]
        sub_comp_data = {}
        if isinstance(cpnt, Assembly):
            print '\nmyflask(): calling build_hierarchy()'
            sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
            assembly_structure[0]['nodes'] = structure

        # Get inputs for form
        form_inputs = WebGUIForm(io['inputs'], run=True, sens_flag=sens_flag)()
       
        failed_run_flag = False
        if (not config_flag) and request.method == 'POST': # Receiving a POST request

            inputs =  request.form.to_dict()
            io = traits2jsondict(cpnt)

            if not sens_flag:
                for k in inputs.keys():
                    if k in io['inputs']: # Loading only the inputs allowed
                            setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))
                try:
                    cpnt.run()
                except:
                    print "Analysis did not execute properly (sens_flag = False)"
                    failed_run_flag = True
                    failed_run_flag = "Analysis did not execute properly - check input parameters!"
                
                sub_comp_data = {}
                if isinstance(cpnt, Assembly):
    
                    sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
                    assembly_structure[0]['nodes'] = structure
                    # show both inputs and outputs in right side table
                    outputs = get_io_dict(cpnt)
                    if debug:
                        print ' INPUTS ', outputs['inputs'] 
                        print 'OUTPUTS ', outputs['outputs'] 
                    if not failed_run_flag:
                        combIO = outputs['inputs'] + outputs['outputs']
                    else:
                        combIO = None
                
                if isinstance(cpnt, Assembly) and not failed_run_flag: # if added - GNS 2015 09 28 
                      # no point in running plots for a failed run
                            
                    # no plots for now since bootstrap-table and bokeh seem to be in conflict
                    try:
                        script, div = prepare_plot(cpnt.plot)
                    except:
                        # TODO: gracefully inform the user of why he doesnt see his plots
                        print "Failed to prepare any plots for " + cpnt.__class__.__name__
                        flash("Failed to prepare any plots for " + cpnt.__class__.__name__)
                        script, div, plot_resources = None, None, None
                else:
                    script, div, plot_resources = None, None, None
                    
                return render_template('webgui.html',
                            inputs=WebGUIForm(io['inputs'], run=True, sens_flag=sens_flag)(MultiDict(inputs)),
                            outputs=combIO,
                            name=cpname,
                            plot_script=script, plot_div=div,
                            sub_comp_data=sub_comp_data,
                            assembly_structure=assembly_structure,
                            group_list=group_list,
                            group_dic=group_dic,
                            desc=desc, failed_run_flag=failed_run_flag, sens_flag=sens_flag)
            
            else: # sens_flag == True

                my_sa = Assembly()
                my_sa.add('asym',cpnt)
                my_sa.add('driver', DOEdriver())
                my_sa.driver.workflow.add('asym')
                my_sa.driver.DOEgenerator = Uniform(1000)

                for k in inputs.keys():
                    print k
                    if k in io['inputs']:
                        setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))
                    else:
                        if 'select.' in k:
                            for kselect in inputs.keys():
                                if 'select.'+kselect == k:
                                    for klow in inputs.keys():
                                        if 'low.'+kselect == klow:
                                            for khigh in inputs.keys():
                                                if 'high.'+kselect == khigh:
                                                    my_sa.driver.add_parameter('asym.'+kselect, low=float(inputs[klow]), high=float(inputs[khigh]))


                for s in io['outputs']:
                    t = cpnt.get_trait(s)
                    if t.trait_type.__class__.__name__ != 'VarTree':
                        my_sa.driver.add_response('asym.'+s)

                try:
                    my_sa.run()
                except:
                    print "Analysis did not execute properly (sens_flag = True)"
                    failed_run_flag = True
                    failed_run_flag = "Analysis did not execute properly - check input parameters!"

                io = traits2jsondict(cpnt)
                sub_comp_data = {}
                if isinstance(cpnt, Assembly):
    
                    sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
                    assembly_structure[0]['nodes'] = structure
                    # show both inputs and outputs in right side table
                    outputs = get_io_dict(cpnt)
                    if not failed_run_flag:
                        combIO = outputs['inputs'] + outputs['outputs']
                    else:
                        combIO = None

                script, div, plot_resources = None, None, None

                return render_template('webgui.html',
                            inputs=WebGUIForm(io['inputs'], run=True, sens_flag=sens_flag)(MultiDict(inputs)),
                            outputs=combIO,
                            name=cpname,
                            plot_script=script, plot_div=div,
                            sub_comp_data=sub_comp_data,
                            assembly_structure=assembly_structure,
                            group_list=group_list,
                            group_dic=group_dic,
                            desc=desc, failed_run_flag=failed_run_flag, sens_flag=sens_flag)            
        
        else: # a 'GET' request?

            # Show the standard form
            return render_template('webgui.html',
                inputs=form_inputs, outputs=None,
                name=cpname,
                plot_script=None, plot_div=None, plot_resources=None,
                sub_comp_data=sub_comp_data,
                assembly_structure=assembly_structure,
                group_list=group_list,
                group_dic=group_dic,
                desc=desc, failed_run_flag = failed_run_flag, sens_flag=sens_flag)

    myflask.__name__ = 'analysis'
    app.route('/'+ 'analysis', methods=['GET', 'POST'])(myflask)

#
#
# if __name__ == '__main__':
#     # Bind to PORT if defined, otherwise default to 5000.
#
#
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port, debug=True)
