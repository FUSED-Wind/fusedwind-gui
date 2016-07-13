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

import json
import yaml

from fusedwindGUI import app 
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
            if not 'group' in v.keys():
                v['group'] = 'Other'
            elif v['group'] is None:
                v['group'] = 'Other'
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


def build_hierarchy(cpnt, sub_comp_data, asym_structure=[], parent=''):
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
            try:
                inputs = yaml.load(f) # yaml.load returns a python object 
            except:
                inputs = None
                print('File {:} not a valid YAML file!'.format(upload_file.filename)) # prints to terminal
                flash('File {:} not a valid YAML file!'.format(upload_file.filename)) # flask-flash flashes to user
                return None

        outfiles.append({
            'filename': upload_file.filename,
            'content': inputs
        })

    return outfiles # list of dictionary 


## Views -----------------------------------------------------------------------
@app.route('/') # default page 
def hello():
    """ Welcoming page
    """
    provider = str(os.environ.get('PROVIDER', 'world'))
    return render_template('index.html', form={'hello':'world'})

@app.route('/about.html') 
def hello2():
    """ About Page
    """
    provider = str(os.environ.get('PROVIDER', 'world'))
    return render_template('about.html', form={'hello':'world'})
@app.route('/documentation.html')
def hello3():
    """ Documentation
    """
    return render_template('documentation.html', form={'hello':'world'})

@app.route('/upload/', methods=['POST']) # when uplaod
def upload():
    """Take care of the reception of the file upload. Return a json file
    to be consumed by a jQuery function
    """
    try:
        files = request.files
        uploaded_files = _handleUpload(files) # returned as a python object 
        if uploaded_files is None:
            raise ValueError
            return jsonify({'status': 'error'})
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
    if isinstance(thing, np.ndarray): # numpy ndarray 
        return thing.tolist() # returns as list
    elif isinstance(thing, np.float64):
        return float(thing) # returns as float
    elif isinstance(thing, Component):
        return get_io_dict(thing) # returns dictionary of i/o
    elif isinstance(thing, VariableTree):
        out = {}
        for k in thing.list_vars():
            out[k] = serialize(getattr(thing, k)) # returns dictionary after recursion
        return out # 
    elif isinstance(thing, float):
        return thing 
    elif isinstance(thing, int):
        return thing
    elif isinstance(thing, str):
        return thing

    return '??_' +  str(thing.__class__)

def to_unicode(dic):
# returns dictionary 
    new = {}
    for k, v in dic.iteritems():
        new[k] = unicode(v)
    return new

def webgui(app=None):

    def configure():
        """ Configuration page
        """

        global cpnt
        global desc
        global analysis
        import fusedwindGUI
        global wt_inputs
        global sensitivityResults

        abspath = fusedwindGUI.__file__.strip('__init__.pyc')

        class ConfigForm(Form):
            pass

        models = [{'name': 'Model Selection',
                   'choices': ['Tier 1 Full Plant Analysis: WISDEM CSM', 'Tier 2 Full Plant Analysis: WISDEM/DTU Plant']},
                  {'name': 'Analysis Type',
                   'choices': ['Individual Analysis', 'Sensitivity Analysis']},
                   {'name': 'Turbine Selection',
                    'choices': ['NREL 5MW RWT',
                                'DTU 10MW RWT']}]

        for dic in models:
            name = dic['name']
            choices = [(val, val) for val in dic['choices']] # the tuple: 1st is value that will be submitted, 2nd is text that'll show to end user
            setattr(ConfigForm, name, SelectField(name, choices=choices)) # adds fields. field = name, selectfield = choices
            # for example, Field Model Selection has 2 options of Tier1 and Tier 2. 


        if request.method == 'POST': # Receiving a POST request

            inputs =  request.form.to_dict()

            winenv = ''
            if platform.system() == 'Windows':
                winenv = os.getenv("SystemDrive").replace(":","")

            if inputs['Model Selection'] == 'Tier 1 Full Plant Analysis: WISDEM CSM':
                # 2015 09 28: move desc assignment AFTER import etc. so it doesn't get changed if import fails - GNS
                try:
                    from wisdem.lcoe.lcoe_csm_assembly import lcoe_csm_assembly
                    cpnt = set_as_top(lcoe_csm_assembly())
                    cpnt.gui_recorder = {}

                    desc = "The NREL Cost and Scaling Model (CSM) is an empirical model for wind plant cost analysis based on the NREL cost and scaling model."
                    if inputs['Turbine Selection'] == 'NREL 5MW RWT':
                        filename = winenv + os.path.join(abspath, 'wt_models', 'nrel5mw_tier1.inp') #TODO: fix abspath
                    elif inputs['Turbine Selection'] == 'DTU 10MW RWT':
                        filename = os.path.join(abspath, 'wt_models/dtu10mw_tier1.inp')
                    f = open(filename, 'r') # returns a python object. 'r' means open text file for reading only. 
                    wt_inputs = to_unicode(yaml.load(f))
                except:
                    print 'lcoe_csm_assembly could not be loaded!'
                    return render_template('error.html',
                                  errmssg='{:} : lcoe_csm_assembly could not be loaded!'.format(inputs['Model Selection']))
            else:
                try:
                    from wisdem.lcoe.lcoe_se_seam_assembly import create_example_se_assembly
                    lcoe_se = create_example_se_assembly('I', 0., True, False, False,False,False, '')
                    cpnt = lcoe_se
                    cpnt.gui_recorder = {}

                    desc = "The NREL WISDEM / DTU SEAM integrated model uses components across both model sets to size turbine components and perform cost of energy analysis."
                    if inputs['Turbine Selection'] == 'NREL 5MW RWT':
                        filename = winenv + os.path.join(abspath, 'wt_models', 'nrel5mw_tier2.inp') #TODO: fix abspath
                    elif inputs['Turbine Selection'] == 'DTU 10MW RWT':
                        filename = os.path.join(abspath, 'wt_models/dtu10mw_tier2.inp')
                    f = open(filename, 'r')
                    wt_inputs = to_unicode(yaml.load(f))
                except:
                    print 'lcoe_se_seam_assembly could not be loaded!'
                    return render_template('error.html',
                                   errmssg='{:} : lcoe_se_seam_assembly could not be loaded!'.format(inputs['Model Selection']))

            analysis = inputs['Analysis Type']
            fused_webapp(True)

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
            # flash('No case downloaded - NO gui_recorder in component!')
            return 'No case downloaded - NO gui_recorder in component!'

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
    @app.route('/analysis/download_sensitivity_results', methods=['GET'])
    def download_sensitivity_results():
        global sensitivityResults

        if not 'inputs' in sensitivityResults: 
            msg =  "Could not find sensitivity results!"
            print '\n***%s\n' % msg
            return '<h2>%s</h2>' % msg

       
        csvFile = "Results of sensitivity analysis, Created: %s\n" % str(dt.datetime.now())

        # Identify as input or output
        csvFile += "-"
        for k,v in sensitivityResults['inputs'].iteritems():
            csvFile += ",input"
        for k,v in sensitivityResults['outputs'].iteritems():
            csvFile += ",output"
        csvFile += "\n"

        # Print Units
        csvFile += "#"
        for k,v in sensitivityResults['inputs'].iteritems():
            csvFile += ",%s" % v['units']
        for k,v in sensitivityResults['outputs'].iteritems():
            csvFile += ",%s" % v['units']
        csvFile += "\n"

        # Print variable name
        csvFile += "Iteration Number"
        for k,v in sensitivityResults['inputs'].iteritems():
            csvFile += ",%s" % k
        for k,v in sensitivityResults['outputs'].iteritems():
            csvFile += ",%s" % k
        csvFile += "\n"
        
        # Print Results
        N = len( sensitivityResults['inputs'][ sensitivityResults['inputs'].keys()[0] ]['value'] )
        N2 = len( sensitivityResults['outputs'][ sensitivityResults['outputs'].keys()[0] ]['value'] )

        for i in range(N):
            csvFile += "%d" % (i+1)
            for k,v in sensitivityResults['inputs'].iteritems():
                try:
                    csvFile += ",%f" % v['value'][i]
                except IndexError:
                    csvFile += ",NaN"
            for k,v in sensitivityResults['outputs'].iteritems():
                try:
                    csvFile += ",%f" % v['value'][i]
                except IndexError:
                    csvFile += ",NaN"
            csvFile += "\n"
        

        # Create/send response
        response = make_response(csvFile)
        response.headers["Content-Disposition"] = "attachment; filename=Sensitivity_Results.csv"
        response.headers['Content-Type'] = "text/csv"

        return response

    #---------------

    def record_case():
        if 'gui_recorder' not in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            #flash('No case recorded - NO gui_recorder in component!')
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
        # flash('recorded case! %i' % cpnt.gui_recorder['counter'], category='message')
        # print cpnt.gui_recorder['recorder']
        return 'Case %i recorded successfully!' % cpnt.gui_recorder['counter']

    record_case.__name__ = 'analysis_record_case'
    app.route('/analysis/record_case', methods=['POST'])(record_case)

    #------------------
    # assume comparing results between 2 cases (varying 1 input causing other outputs)
    @app.route('/compare_results', methods=['POST'])
    def compare_results():
        if not 'gui_recorder' in vars(cpnt):     
            print '\n*** NO gui_recorder in component!\n'
            return 'No case downloaded - NO gui_recorder in component!'
        if len(cpnt.gui_recorder.keys()) == 0:
            print '\n *** NO cases recorded!\n'
            return 'No Cases Recorded'

        inputName = request.form['inVar']
        outputName = request.form['outVar']

        try: # find all the values/units of the variables of interess
            def _finditem(obj, key): 
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
                        item = _finditem(v, key)
                        if item is not None:
                            return item

            # find values associated with the selected fields
            input_vals, output_vals = [], []
            num_cases = int(cpnt.gui_recorder['counter']) 
            for i in range(num_cases):
                caseNum = i + 1
                input_vals.append(_finditem(cpnt.gui_recorder['recorder']['case%i' %caseNum], inputName) )
                output_vals.append(_finditem(cpnt.gui_recorder['recorder']['case%i' %caseNum], outputName) )
            global myUnits
        
            xArray = np.array(input_vals)
            yArray = np.array(output_vals)
            xUnit = myUnits[inputName]
            yUnit = myUnits[outputName]
                

        except KeyError:
            script, div = prepare_plot( CompareResultsPlot, ("",[]), ("",[]))
        else:
            if (xUnit == "None" or xUnit==None):
                xUnit = ""
            if (yUnit == "None" or yUnit==None):
                yUnit = ""

            script, div = prepare_plot( CompareResultsPlot,
                (inputName + (" (%s)"%xUnit if xUnit!="" else ""), xArray),
                (outputName+ (" (%s)"%yUnit if yUnit!="" else ""), yArray),
                units=(xUnit, yUnit) )
        f = {"script":script, "div":div}
        return jsonify(**f)
    compare_results.__name__ = 'analysis_compare_results'
    app.route('/analysis/compare_results', methods=['GET', 'POST'])(compare_results)

    #---------------

    def clear_recorder():

        if not 'gui_recorder' in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            #flash('No recorder to clear!', category='message')
            return 'No recorder to clear!'

        cpnt.gui_recorder = {}
        # flash('Recorder cleared!', category='message')
        return 'All cases cleared successfully!'

    clear_recorder.__name__ = 'analysis_clear_recorder'
    app.route('/analysis/clear_recorder', methods=['POST'])(clear_recorder)






        #     record_case()
        #     r = cpnt.gui_recorder['recorder']

        # r = yaml.dump(cpnt.gui_recorder['recorder'], default_flow_style=False)
        # response = make_response(r)
        # response.headers["Content-Disposition"] = "attachment; filename=fused_model.yaml"
        # return response

    #---------------

    def fused_webapp(config_flag=False): 
        if analysis == 'Individual Analysis':
            sens_flag=False
        else:
            sens_flag=True
        cpname = cpnt.__class__.__name__
        if cpnt is None:
            print '\n*** WARNING: component is None\n'
            failed_run_flag = 'WARNING: component is None in fused_webapp() - try another model(?)'

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
            sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
            assembly_structure[0]['nodes'] = structure

        failed_run_flag = False
        if (not config_flag) and request.method == 'POST': 

            inputs =  request.form.to_dict() 
            io = traits2jsondict(cpnt)


            if not sens_flag: 
                try:
                    for k in inputs.keys():
                        if k in io['inputs']: # Loading only the inputs allowed
                                setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))
                except:
                    print "Something went wrong when setting the model inputs, one of them may have a wrong type"
                    failed_run_flag = True
                    failed_run_flag = "Something went wrong when setting the model inputs, one of them may have a wrong type"
                    flash(failed_run_flag)
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

                        # Start 
                        myInputs = outputs['inputs']
                        myOutputs = outputs['outputs']

                        inputs_names_form = [myInputs[:][i]['name'] for i in range(len(myInputs))]
                        outputs_names_form = [myOutputs[:][i]['name'] for i in range(len(myOutputs))]
                     
                        global myUnits
                        for el in myInputs[:]:
                            if el['name'] not in myUnits.keys() and 'units' in el.keys():

                                myUnits[el['name']] = el['units']
                        for el in myOutputs[:]:
                            if el['name'] not in myUnits.keys() and 'units' in el.keys():
                                myUnits[el['name']] = el['units']



                        def makePretty(myList):
                            """ 
                            This function takes in a list of dictionaries, where each dictionary represents an input/output
                            It modifies variable names and descriptions to be more human readable. 

                            * This mutative method may be a problem if trying to save a file then trying to reload the file.
                            If needed, comment out from #start to #End and it should work.

                            Alternatively, when importing you can just reverse these operations below. Make everything lower 
                            case and replace white space with underscore. 

                            EDIT: checking the saved files, it doesn't seem to affect what is recorded/saved in the .yaml files
                            """
                            for myDict in myList:
                                if 'name' in myDict.keys():
                                    myDict['name'] = myDict['name'].replace("_"," ").title()
                                if 'desc' in myDict.keys():
                                    myDict['desc'] = myDict['desc'][0].upper()+myDict['desc'][1:]
                        makePretty(myInputs)
                        makePretty(myOutputs)
                    
                        # End

                        combIO = outputs['inputs'] + outputs['outputs']

                    else:
                        combIO = None

                    if not failed_run_flag:
                #if isinstance(cpnt, Assembly) and not failed_run_flag: # if added - GNS 2015 09 28
                    # no plots for now since bootstrap-table and bokeh seem to be in conflict
                        try:
                            script, div = prepare_plot(cpnt.plot) # plots the capital costs
                            script_lcoe, div_lcoe = prepare_plot(cpnt.lcoe_plot) # plots Lcoe 
                            script_comp, div_comp = prepare_plot( CompareResultsPlot, ("", []), ("", []), ("",[]))

                            draw_plot = True
                        except:
                            # TODO: gracefully inform the user of why he doesnt see his plots
                            print "Failed to prepare any plots for " + cpnt.__class__.__name__
                            flash("Analysis ran; failed to prepare any plots for " + cpnt.__class__.__name__)
                            script, div, plot_resources, draw_plot = None, None, None, None
                    else:
                        script, div, plot_resources, draw_plot = None, None, None, None

                    return render_template('webgui.html', # basically rerenter webgui.html with results or no results dependingon success
                                inputs=WebGUIForm(io['inputs'], run=True, sens_flag=sens_flag)(MultiDict(inputs)),
                                outputs=combIO,
                                name=cpname,
                                plot_script=script, plot_div=div, draw_plot=draw_plot,
                                plot_script_lcoe=script_lcoe, plot_div_lcoe=div_lcoe,
                                plot_inputVars=inputs_names_form, plot_outputVars=outputs_names_form,
                                plot_script_comp=script_comp, plot_div_comp=div_comp,
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
                my_sa.driver.DOEgenerator = Uniform( int(inputs['iteration_count']) )

                extra_inputs = {"sensitivity_iterations":int(inputs['iteration_count'])}
                skipInputs = ['iteration_count']

                for k in inputs.keys():
                    if k in skipInputs :
                        continue  
                    try:
                        if k in io['inputs']: #   io = traits2jsondict(cpnt)
                            setattr(cpnt, k, json2type[io['inputs'][k]['type']](inputs[k]))
                    except:
                        print "Something went wrong when setting the model inputs, one of them may have a wrong type"
                        failed_run_flag = True
                        failed_run_flag = "Something went wrong when setting the model inputs, one of them may have a wrong type"
                        flash(failed_run_flag)
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
                        my_sa.driver.add_response('asym.' + s)

                try:
                    my_sa.run()
                except:
                    print "Analysis did not execute properly (sens_flag = True)"
                    failed_run_flag = True
                    failed_run_flag = "Analysis did not execute properly - check input parameters!"
                    #flash(failed_run_flag) # no need to flash a failed_run_flag
                else:
                    try:
                        my_sa.driver.case_inputs.asym.list_vars()
                    except AttributeError:
                        draw_plot = False
                        script, div = None, None
                        inputVars = None
                        outputVars = None
                        plot_controls = None

                    else:
                        draw_plot = True
                        ## Make plotting of results available (Severin)
                        global sensitivityResults

                        sensitivityResults = {
                            "inputs":{},
                            "outputs":{}
                        }

                        inputVars = []
                        outputVars = []

                        for val in my_sa.driver.case_inputs.asym.list_vars():
                            try:
                                sensitivityResults['inputs'][val] = {
                                    'value':my_sa.driver.case_inputs.asym.get(val),
                                    'units':getattr(cpnt.get_trait(val), 'units' )}
                            except Exception:
                                pass
                            else:
                                inputVars.append(val)

                        for val in my_sa.driver.case_outputs.asym.list_vars():
                            try:
                                tmp = my_sa.driver.case_outputs.asym.get(val)
                            except Exception:
                                pass
                            else:
                                if( isinstance(tmp.pop(), np.float64)):
                                    sensitivityResults['outputs'][val] = {
                                    'value':tmp,
                                    'units':getattr(cpnt.get_trait(val), 'units' )}
                                    outputVars.append(val)


                        script, div = prepare_plot( SensPlot1D, ("", []), ("", []), ("",[]))
                        plot_controls = True


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


                return render_template('webgui.html',
                            inputs=WebGUIForm(io['inputs'], run=True, sens_flag=sens_flag)(MultiDict(inputs)),
                            extra_inputs=extra_inputs,
                            outputs=combIO,
                            name=cpname,
                            plot_script=script, plot_div=div, draw_sens_plot=draw_plot, plot_controls=plot_controls,
                            plot_inputVars=inputVars, plot_outputVars=outputVars,
                            sub_comp_data=sub_comp_data,
                            assembly_structure=assembly_structure,
                            group_list=group_list,
                            group_dic=group_dic,
                            desc=desc, failed_run_flag=failed_run_flag, sens_flag=sens_flag)

        else: # a 'GET' request?

            extra_inputs={"sensitivity_iterations":1000}
            # Show the standard form
            return render_template('webgui.html',
                inputs=WebGUIForm(io['inputs'], run=True, sens_flag=sens_flag)(MultiDict(wt_inputs)),
                extra_inputs=extra_inputs,
                outputs=None, name=cpname,
                plot_script=None, plot_div=None, plot_resources=None,
                sub_comp_data=sub_comp_data,
                assembly_structure=assembly_structure,
                group_list=group_list,
                group_dic=group_dic,
                desc=desc, failed_run_flag = failed_run_flag, sens_flag=sens_flag)

    fused_webapp.__name__ = 'analysis'
    app.route('/'+ 'analysis', methods=['GET', 'POST'])(fused_webapp)


# Retrieve data from sensitivity analysis for plotting
@app.route('/RetrieveSensPlot', methods=['POST'])
def GetSensPlot():
    global sensitivityResults

    inputName = request.form['inVar']
    outputName = request.form['outVar']
    colorName = request.form['colVar']

    try:
        xArray = np.array(sensitivityResults['inputs'][inputName]['value'])
        xUnit = sensitivityResults['inputs'][inputName]['units']
        yArray = np.array(sensitivityResults['outputs'][outputName]['value'])
        yUnit = sensitivityResults['outputs'][outputName]['units']

        if(colorName != "Mono"):
            #deterine if input or output
            if( colorName in sensitivityResults['outputs']):
                colors = np.array(sensitivityResults['outputs'][colorName]['value'])
            else:
                colors = np.array(sensitivityResults['inputs'][colorName]['value'])
        else:
            colors = None
    except KeyError:
        script, div = prepare_plot( SensPlot1D, ("",[]), ("",[]))

        summary = "<p>Error Retrieving Data</p>"

    else:
        if (xUnit == "None" or xUnit==None):
            xUnit = ""
        if (yUnit == "None" or yUnit==None):
            yUnit = ""

        script, div = prepare_plot( SensPlot1D,
            (inputName + (" (%s)"%xUnit if xUnit!="" else ""), xArray),
            (outputName+ (" (%s)"%yUnit if yUnit!="" else ""), yArray),
            colorAxis={"name": colorName, "values":colors},
            units=(xUnit, yUnit) )

        ## Produce summary report
        summary = "<p>\n"
        summary += "\t<b>Input Variable: %s </b><br>\n" %inputName
        summary += "\t  Range: %s %s - %s %s<br>\n" %( prettyNum(min(xArray)), xUnit, prettyNum(max(xArray)), xUnit )
        summary += "<br>\n"
        summary += "\t<b>Output Variable: %s </b><br>\n" %outputName
        summary += "\t  Range: %s %s - %s %s<br>\n" %( prettyNum(min(yArray)), yUnit, prettyNum(max(yArray)), yUnit )
        summary += "\t  Average: %s %s<br>\n" %( prettyNum(yArray.mean()), yUnit )
        summary += "\t  Std Dev: %s %s<br>\n" %( prettyNum(yArray.std()), yUnit )
        summary += "</p>"

    f = {"script":script, "div":div, "summary":summary}

    return jsonify(**f)


################################### SCRIPT #######################################################

# Bokeh stuff after run
try:
    from bokeh.embed import components
    from bokeh.plotting import figure
    from bokeh.charts import  Line
    from bokeh.resources import INLINE #inline configures to provide entire BokehJS code and CSS inline
    from bokeh.templates import JS_RESOURCES
    from bokeh.util.string import encode_utf8
    from bokeh._legacy_charts import Donut, output_file, show 
    from bokeh.palettes import Spectral9
    use_bokeh = True
except:
    print 'Bokeh hasnt been installed properly'
    use_bokeh = False


if use_bokeh:
    def prepare_plot(func, *args, **kwargs): # the func seems to be either sens1dplot or copnt.plot 
        fig = figure()
        fig = func(fig, *args, **kwargs)
        # Create a polynomial line graph

        # Configure resources to include BokehJS inline in the document.
        # For more details see:
        #   http://bokeh.pydata.org/en/latest/docs/reference/resources_embedding.html#module-bokeh.resources
        plot_resources = JS_RESOURCES.render(
            js_raw=INLINE.js_raw,
            css_raw=INLINE.css_raw,
            js_files=INLINE.js_files,
            css_files=INLINE.css_files,
        )

        # For more details see:
        #   http://bokeh.pydata.org/en/latest/docs/user_guide/embedding.html#components
        #   http://bokeh.pydata.org/en/latest/docs/user_guide/embed.html#components  (as of 2015 09 28)
        script, div = components(fig, INLINE) # components(plot_objs) returns HTML components to embed a Bokeh Plot. THe data for the plot is stored direclty in the returned HTML. 
        return script, div 
            # Function used to print pretty numbers
    def prettyNum( num ):
        anum = abs(num)
        if( anum > 1e4 or anum < 1e-2):
            return "%.2e" % num 
        elif( anum > 10.0 ):
            return "%.2f" % num # this just means to print the 2 values after the decimal point for float
        elif( anum < 1.0):
            return "%.4f" % num
        else:
            return "%.3f" % num

    # Create 1D sensitivitey Bokeh plots
    def SensPlot1D( fig, *args, **kwargs ):

        fig = figure( title="Sensitivity Results",
                    x_axis_label = args[0][0],
                    y_axis_label = args[1][0])

        #Set colors according to input
        colors = []
        try:
            colorData = kwargs['colorAxis']['values']
            # colorData has the y-values for the colored coordinate

            for val in colorData:
                d = 200* (max(colorData) - val) / (max(colorData) - min(colorData))
                colors.append("#%02x%02x%02x" % (200-d, 150, d))

        except:
            colors = ["#22AEAA" for i in args[0][1]]


        # plot data
        fig.scatter( args[0][1], args[1][1], size=10, fill_color=colors)

        if( len(args[0][1])>0 and len(args[1][1])>0 and (kwargs['colorAxis']['name'] != "Mono" )):
            # draw color name

            xDiff = max(args[0][1]) - min(args[0][1])
            yDiff = max(args[1][1]) - min(args[1][1])

            xPos = min(args[0][1]) + 0.05 * xDiff
            yPos = max(args[1][1]) + 0.10 * yDiff

            fig.text(
                x = xPos + 0.125 * xDiff,
                y = yPos - 0.05 * yDiff,
                text = ["%s" %kwargs['colorAxis']['name']],
                text_align="center" )
            #draw color scale
            fig.line(
                x= [xPos, xPos + 0.25 * xDiff],
                y= [yPos, yPos],
                line_color="black")

            fig.circle(x= xPos, y= yPos, size=10, fill_color="#0096C8" )
            fig.circle(x= xPos+0.25*xDiff, y= yPos, size=10, fill_color="#C89600" )

            fig.text(x=xPos, y=yPos+0.02*yDiff, text = ["%s" % prettyNum(min(colorData))], text_align="center")
            fig.text(x=xPos+0.25*xDiff, y=yPos+0.02*yDiff, text = ["%s" % prettyNum(max(colorData))], text_align="center")
        return fig

    def CompareResultsPlot(fig, *args, **kwargs):
        if len(args)==0:
            pass
        import itertools
        fig = figure( title="Compare Results",
                    x_axis_label = args[0][0],
                    y_axis_label = args[1][0])

        # Set colors to bokeh palette (Can change palettes in import statement above)
        # http://bokeh.pydata.org/en/0.10.0/docs/gallery/palettes.html
        palette = itertools.cycle(Spectral9)
        # plot data
        def mscatter(p,x,y,typestr="circle"):
            p.scatter(x,y,marker=typestr, line_color="#000000", fill_color=palette.next(), fill_alpha=0.8, size=12)

        # use for loop to iterate through palette
        print args[0]
        print args[0][1]
        numDataPoints = len(args[0][1])
        for i in range(numDataPoints):
            mscatter(fig, args[0][1][i], args[1][1][i])
        return fig






cpnt = None
desc = ''
analysis = 'Individual Analysis'
sensitivityResults = {"empty":True}
myUnits = {"empty":True}

