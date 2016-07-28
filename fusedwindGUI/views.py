# -*- coding: utf-8 -*-

from openmdao.main.vartree import VariableTree
from openmdao.main.api import set_as_top, Assembly
from openmdao.lib.drivers.api import DOEdriver
from openmdao.lib.doegenerators.api import Uniform
from Tornado_Generator import *

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


# Handling file upload -------------------------------------------------------
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
                inputs = yaml.load(f)  # yaml.load returns a python object
            except:
                inputs = None
                print('File {:} not a valid YAML file!'.format(
                    upload_file.filename))  # prints to terminal
                flash('File {:} not a valid YAML file!'.format(
                    upload_file.filename))  # flask-flash flashes to user
                return None

        outfiles.append({
            'filename': upload_file.filename,
            'content': inputs
        })

    return outfiles  # list of dictionary


# Views -----------------------------------------------------------------------
@app.route('/')  # default page
def hello():
    """ Welcoming page
    """
    provider = str(os.environ.get('PROVIDER', 'world'))
    return render_template('index.html', form={'hello': 'world'})


@app.route('/about.html')
def about():
    """ About Page
    """
    provider = str(os.environ.get('PROVIDER', 'world'))
    return render_template('about.html', form={'hello': 'world'})


@app.route('/documentation.html')
def documentation():
    """ Documentation
    """
    return render_template('documentation.html', form={'hello': 'world'})


@app.route('/upload/', methods=['POST'])  # when uplaod
def upload():
    """Take care of the reception of the file upload. Return a json file
    to be consumed by a jQuery function
    """
    try:
        files = request.files
        uploaded_files = _handleUpload(files)  # returned as a python object
        if uploaded_files is None:
            raise ValueError
            return jsonify({'status': 'error'})
        response = jsonify({'files': uploaded_files})
        # fix for legacy browsers
        response.headers['Content-Type'] = 'text/plain'
        return response
    except:
        raise
        return jsonify({'status': 'error'})




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
                   'choices': ['Tier 1 Full Plant Analysis: WISDEM CSM',
                               'Tier 2 Full Plant Analysis: WISDEM/DTU Plant']},
                  {'name': 'Analysis Type',
                   'choices': ['Individual Analysis',
                               'Sensitivity Analysis']},
                  {'name': 'Turbine Selection',
                   'choices': ['NREL 5MW RWT',
                               'DTU 10MW RWT']}]

        for dic in models:
            name = dic['name']
            choices = [(val, val) for val in dic['choices']]
            setattr(ConfigForm, name, SelectField(name, choices=choices))

        if request.method == 'POST':  # Receiving a POST request
            inputs = request.form.to_dict()
            winenv = ''
            if platform.system() == 'Windows':
                winenv = os.getenv("SystemDrive").replace(":", "")

            if inputs[
                    'Model Selection'] == 'Tier 1 Full Plant Analysis: WISDEM CSM':
                # 2015 09 28: move desc assignment AFTER import etc. so it
                # doesn't get changed if import fails - GNS
                try:
                    from wisdem.lcoe.lcoe_csm_assembly import lcoe_csm_assembly
                    cpnt = set_as_top(lcoe_csm_assembly())
                    cpnt.gui_recorder = {}

                    desc = "The NREL Cost and Scaling Model (CSM) is an empirical model for wind plant cost analysis based on the NREL cost and scaling model."
                    if inputs['Turbine Selection'] == 'NREL 5MW RWT':
                        # TODO: fix abspath
                        filename = winenv + \
                            os.path.join(abspath, 'wt_models', 'nrel5mw_tier1.inp')
                    elif inputs['Turbine Selection'] == 'DTU 10MW RWT':
                        filename = os.path.join(
                            abspath, 'wt_models/dtu10mw_tier1.inp')
                    # returns a python object. 'r' means open text file for
                    # reading only.
                    f = open(filename, 'r')
                    wt_inputs = to_unicode(yaml.load(f))
                except:
                    print 'lcoe_csm_assembly could not be loaded!'
                    return render_template(
                        'error.html',
                        errmssg='{:} : lcoe_csm_assembly could not be loaded!'.format(
                            inputs['Model Selection']))
            else:
                try:
                    from wisdem.lcoe.lcoe_se_seam_assembly import create_example_se_assembly
                    lcoe_se = create_example_se_assembly(
                        'I', 0., True, False, False, False, False, '')
                    cpnt = lcoe_se
                    cpnt.gui_recorder = {}

                    desc = "The NREL WISDEM / DTU SEAM integrated model uses components across both model sets to size turbine components and perform cost of energy analysis."
                    if inputs['Turbine Selection'] == 'NREL 5MW RWT':
                        # TODO: fix abspath
                        filename = winenv + \
                            os.path.join(abspath, 'wt_models', 'nrel5mw_tier2.inp')
                    elif inputs['Turbine Selection'] == 'DTU 10MW RWT':
                        filename = os.path.join(
                            abspath, 'wt_models/dtu10mw_tier2.inp')
                    f = open(filename, 'r')
                    wt_inputs = to_unicode(yaml.load(f))
                except:
                    print 'lcoe_se_seam_assembly could not be loaded!'
                    return render_template(
                        'error.html',
                        errmssg='{:} : lcoe_se_seam_assembly could not be loaded!'.format(
                            inputs['Model Selection']))

            analysis = inputs['Analysis Type']
            fused_webapp(True)

            return render_template('configure.html',
                                   config=ConfigForm(MultiDict()),
                                   config_flag=True)

        else:
            return render_template('configure.html',
                                   config=ConfigForm(MultiDict()),
                                   config_flag=False)

    configure.__name__ = 'configure'
    app.route('/configure.html', methods=['Get', 'Post'])(configure)


    #---------------

    def download():
        """ This downloads into a file called fused_inputs.yaml the inputs """
        out = get_io_dict(cpnt)
        params = {}
        for param in out['inputs']:
            params[param['name']] = param['state']
        r = yaml.dump(params, default_flow_style=False)

        response = make_response(r)
        response.headers[
            "Content-Disposition"] = "attachment; filename=fused_inputs.yaml"
        return response
        # return Response(r, content_type='text/yaml; charset=utf-8',
        # filename='books.csv')

    download.__name__ = 'analysis_download'
    app.route('/analysis/download', methods=['GET'])(download)


    #---------------

    def download_full():
        """ This downloads inputs and outputs to a file called fused_model.yaml """
        if not 'gui_recorder' in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            # flash('No case downloaded - NO gui_recorder in component!')
            return 'No case downloaded - NO gui_recorder in component!'

        if len(cpnt.gui_recorder.keys()) == 0:
            record_case()
            r = cpnt.gui_recorder['recorder']

        r = yaml.dump(cpnt.gui_recorder['recorder'], default_flow_style=False)
        response = make_response(r)
        response.headers[
            "Content-Disposition"] = "attachment; filename=fused_model.yaml"
        return response
        # return Response(r, content_type='text/yaml; charset=utf-8',
        # filename='books.csv')

    download_full.__name__ = 'analysis_download_full'
    app.route('/analysis/download_full', methods=['GET'])(download_full)

    #---------------

    @app.route('/analysis/download_sensitivity_results', methods=['GET'])
    def download_sensitivity_results():
        global sensitivityResults

        if not 'inputs' in sensitivityResults:
            msg = "Could not find sensitivity results!"
            print '\n***%s\n' % msg
            return '<h2>%s</h2>' % msg

        csvFile = "Results of sensitivity analysis, Created: %s\n" % str(
            dt.datetime.now())

        # Identify as input or output
        csvFile += "-"
        for k, v in sensitivityResults['inputs'].iteritems():
            csvFile += ",input"
        for k, v in sensitivityResults['outputs'].iteritems():
            csvFile += ",output"
        csvFile += "\n"

        # Print Units
        csvFile += "#"
        for k, v in sensitivityResults['inputs'].iteritems():
            csvFile += ",%s" % v['units']
        for k, v in sensitivityResults['outputs'].iteritems():
            csvFile += ",%s" % v['units']
        csvFile += "\n"

        # Print variable name
        csvFile += "Iteration Number"
        for k, v in sensitivityResults['inputs'].iteritems():
            csvFile += ",%s" % k
        for k, v in sensitivityResults['outputs'].iteritems():
            csvFile += ",%s" % k
        csvFile += "\n"

        # Print Results
        N = len(
            sensitivityResults['inputs'][
                sensitivityResults['inputs'].keys()[0]]['value'])
        N2 = len(
            sensitivityResults['outputs'][
                sensitivityResults['outputs'].keys()[0]]['value'])

        for i in range(N):
            csvFile += "%d" % (i + 1)
            for k, v in sensitivityResults['inputs'].iteritems():
                try:
                    csvFile += ",%f" % v['value'][i]
                except IndexError:
                    csvFile += ",NaN"
            for k, v in sensitivityResults['outputs'].iteritems():
                try:
                    csvFile += ",%f" % v['value'][i]
                except IndexError:
                    csvFile += ",NaN"
            csvFile += "\n"

        # Create/send response
        response = make_response(csvFile)
        response.headers[
            "Content-Disposition"] = "attachment; filename=Sensitivity_Results.csv"
        response.headers['Content-Type'] = "text/csv"

        return response


    #---------------

    def record_case():
        """
        Saves inputs/outputs into dictionary defined in the component.
        cpnt.gui_recorder['counter'] contains a counter for the number of cases recorded
        cpnt.gui_recorder['recorder'] contains all the names, values, units.
        """
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
            cpnt.gui_recorder['recorder']['case%i' %
                                          cpnt.gui_recorder['counter']] = params
        except:
            cpnt.gui_recorder['recorder'] = {}
            cpnt.gui_recorder['recorder']['case%i' %
                                          cpnt.gui_recorder['counter']] = params
        # flash('recorded case! %i' % cpnt.gui_recorder['counter'], category='message')
        return 'Case %i recorded successfully!' % cpnt.gui_recorder['counter']

    record_case.__name__ = 'analysis_record_case'
    app.route('/analysis/record_case', methods=['POST'])(record_case)

    #------------------

    @app.route('/compare_results', methods=['POST'])
    def compare_results():
        """
        Finds relevant input/output values and units to be plotted
        """

        if not 'gui_recorder' in vars(cpnt):
            print '\n*** NO gui_recorder in component!\n'
            return 'No case downloaded - NO gui_recorder in component!'
        if len(cpnt.gui_recorder.keys()) == 0:
            print '\n *** NO cases recorded!\n'
            return 'No Cases Recorded'

        inputName = request.form['inVar']
        outputName = request.form['outVar']
        global myUnits

        try:  # find all the values/units of the variables of interest
            input_vals, output_vals = [], []
            num_cases = int(cpnt.gui_recorder['counter'])
            for i in range(num_cases):
                caseNum = i + 1
                current_input = finditem(
                    cpnt.gui_recorder['recorder'][
                        'case%i' %
                        caseNum], inputName)
                current_output = finditem(
                    cpnt.gui_recorder['recorder'][
                        'case%i' %
                        caseNum], outputName)

                input_vals.append(current_input)
                output_vals.append(current_output)
            
            xArray = np.array(input_vals)
            yArray = np.array(output_vals)
            xUnit = myUnits[inputName]
            yUnit = myUnits[outputName]
        except KeyError:
            script, div = prepare_plot(CompareResultsPlot, ("", []), ("", []))
        else:
            if (xUnit == "None" or xUnit is None):
                xUnit = ""
            if (yUnit == "None" or yUnit is None):
                yUnit = ""

            script, div = prepare_plot(CompareResultsPlot, (inputName + (" (%s)" %
                                                                         xUnit if xUnit != "" else ""), xArray), (outputName + (" (%s)" %
                                                                                                                                yUnit if yUnit != "" else ""), yArray), units=(xUnit, yUnit))
        f = {"script": script, "div": div}

        return jsonify(**f)
    compare_results.__name__ = 'analysis_compare_results'
    app.route(
        '/analysis/compare_results',
        methods=[
            'GET',
            'POST'])(compare_results)


    #---------------

    def clear_recorder():
        """
        Clears the recorder (cpnt.gui_recorder) dictionary
        """

        if not 'gui_recorder' in vars(cpnt):       # GNS
            print '\n*** NO gui_recorder in component!\n'
            #flash('No recorder to clear!', category='message')
            return 'No recorder to clear!'

        cpnt.gui_recorder = {}
        # flash('Recorder cleared!', category='message')
        return 'All cases cleared successfully!'

    clear_recorder.__name__ = 'analysis_clear_recorder'
    app.route('/analysis/clear_recorder', methods=['POST'])(clear_recorder)


    #---------------

    def fused_webapp(config_flag=False):
        """ Runs the analysis page """
        if analysis == 'Individual Analysis':
            sens_flag = False
        else:
            sens_flag = True
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
        skeys = sorted(io['inputs'].keys())
        for k in skeys:
            v = io['inputs'][k]
            if 'group' in v.keys():
                if v['group'] not in group_list:
                    group_list.append(v['group'])
                group_dic[k] = v['group']
            else:
                group_dic[k] = 'Global'
        group_list.sort()
        group_list.insert(0, group_list.pop(group_list.index('Global')))

        # Build assembly hierarchy
        assembly_structure = [{'text': cpname,
                               'nodes': []}]
        sub_comp_data = {}
        if isinstance(cpnt, Assembly):
            sub_comp_data, structure = build_hierarchy(cpnt, sub_comp_data, [])
            assembly_structure[0]['nodes'] = structure

        failed_run_flag = False
        if (not config_flag) and request.method == 'POST':

            inputs = request.form.to_dict()
            io = traits2jsondict(cpnt)

            try:
                if inputs['select.alpha'] == "y":
                    tornado = True
                else:
                    tornado = False
            except KeyError:
                tornado = False

            if not sens_flag:    
                toggle = False
                try:
                    toggle = 'toggle_record' in inputs
                except KeyError:
                    pass
                try:
                    for k in inputs.keys():
                        if k in io[
                                'inputs']:  # Loading only the inputs allowed
                            setattr(
                                cpnt, k, json2type[
                                    io['inputs'][k]['type']](
                                    inputs[k]))
                except:
                    print "Something went wrong when setting the model inputs, one of them may have a wrong type"
                    failed_run_flag = True
                    failed_run_flag = "Something went wrong when setting the model inputs, one of them may have a wrong type"
                    flash(failed_run_flag)
                try:
                    cpnt.run()
                except NameError as detail:
                        print "att Error:" , detail
                except TypeError as detail:
                    print "att Error:" , detail
                except AttributeError as detail:
                    print "att Error:" , detail
                except ValueError as detail:
                    print "att Error:" , detail


                except:
                    print sys.exc_info()[0]

                
                    print "Analysis did not execute properly (sens_flag = False)"
                    failed_run_flag = True
                    failed_run_flag = "Analysis did not execute properly - check input parameters!"

                sub_comp_data = {}
                if isinstance(cpnt, Assembly):

                    sub_comp_data, structure = build_hierarchy(
                        cpnt, sub_comp_data, [])
                    assembly_structure[0]['nodes'] = structure
                    outputs = get_io_dict(cpnt)
                    if not failed_run_flag:
                        myInputs = outputs['inputs']
                        myOutputs = outputs['outputs']

                        # saving the elements that will appear in the form
                        # under the compare results tab
                        inputs_names_form = form_names(myInputs)
                        outputs_names_form = form_names(myOutputs)

                        global myUnits
                        saveUnits(myInputs[:])
                        saveUnits(myOutputs[:])

                        # capitalize and change underscore to spaces for display purposes. Should not affect variables themselves for any other purposes
                        # such as saving or plotting
                        makePretty(myInputs)
                        makePretty(myOutputs)

                        combIO = outputs['inputs'] + outputs['outputs']
                    else:
                        combIO = None
                        inputs_names_form, outputs_names_form = None, None

                    if not failed_run_flag:
                        # if isinstance(cpnt, Assembly) and not
                        # failed_run_flag: # if added - GNS 2015 09 28
                        try:
                            # plots the capital costs
                            script, div = prepare_plot(cpnt.plot)
                            script_lcoe, div_lcoe = prepare_plot(
                                cpnt.lcoe_plot) 
                            script_comp, div_comp = prepare_plot(
                                CompareResultsPlot, ("", []), ("", []), ("", []))
                            draw_plot = True
                        except:
                            # TODO: gracefully inform the user of why he doesnt
                            # see his plots
                            print "Failed to prepare any plots for " + cpnt.__class__.__name__
                            flash(
                                "Analysis ran; failed to prepare any plots for " +
                                cpnt.__class__.__name__)
                            script, div, plot_resources, draw_plot = None, None, None, None
                            script_lcoe, div_lcoe, plot_resources, draw_plot = None, None, None, None
                            script_comp, div_comp, plot_resources, draw_plot = None, None, None, None
                    else:
                        script, div, plot_resources, draw_plot = None, None, None, None
                        script_lcoe, div_lcoe, plot_resources, draw_plot = None, None, None, None
                        script_comp, div_comp, plot_resources, draw_plot = None, None, None, None

                    return render_template('webgui.html',  # basically rerenter webgui.html with results or no results dependingon success
                                           inputs=WebGUIForm(
                                               io['inputs'], run=True, sens_flag=sens_flag)(
                                               MultiDict(inputs)),
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
                                           desc=desc, failed_run_flag=failed_run_flag, sens_flag=sens_flag, toggle=toggle)

            # if sensitivity analysis and selected tornado option
            elif sens_flag and tornado:

                # alpha is variation parameter: 
                alpha = int(inputs['alpha'])
                # if alpha is invalid or if no parameters checked
                check_select = inputs.keys()[:]
                if 'select.alpha' in inputs.keys():
                    check_select.remove('select.alpha')

                if not any('select.' in x for x in check_select) or alpha > 100 or alpha <= 0: 
                    if alpha > 100 or alpha <= 0:
                        print "Vary between -100 and 100 only "
                        flash("Vary between -100 and 100 only ")
                    else:
                        print "Select parameters"
                        flash("Select parameters")
                    extra_inputs = {"sensitivity_iterations": 1000, "alpha":20}
                    # Show the standard form
                    return render_template(
                        'webgui.html',
                        inputs=WebGUIForm(
                            io['inputs'],
                            run=True,
                            sens_flag=sens_flag)(
                            MultiDict(wt_inputs)),
                        extra_inputs=extra_inputs,
                        outputs=None,
                        name=cpname,
                        plot_script=None,
                        plot_div=None,
                        plot_resources=None,
                        sub_comp_data=sub_comp_data,
                        assembly_structure=assembly_structure,
                        group_list=group_list,
                        group_dic=group_dic,
                        desc=desc,
                        failed_run_flag=failed_run_flag,
                        sens_flag=sens_flag,
                        tornado_flag=tornado)

                
                global tornadoInputs
                global tornadoOutputs
                tornadoInputs, tornadoOutputs = {}, {}
                outputVars, removeFromOutputs = [], []

                extra_inputs = {"sensitivity_iterations": int(
                                    inputs['iteration_count']),
                                "alpha": alpha }
                skipInputs = ['iteration_count', 'alpha', 'select.alpha']
                #print inputs.keys()  - this has all the inputs not just the ones we selected from the form
                for k in inputs.keys():
                    if k in skipInputs:
                        continue
                    try:
                        if k in io['inputs']:                         
                            setattr(
                                cpnt, k, json2type[
                                    io['inputs'][k]['type']](
                                    inputs[k]))
                    except:
                        print "Something went wrong when setting the model inputs, one of them may have a wrong type"
                        failed_run_flag = True
                        failed_run_flag = "Something went wrong when setting the model inputs, one of them may have a wrong type"
                        flash(failed_run_flag)
                                            # this adds the input variable to vary 
                for k in inputs.keys():
                    if k in skipInputs or 'select.' not in k:
                        continue
                    else:
                        my_sa = Assembly()
                        my_sa.add('asym', cpnt)
                        my_sa.add('driver', TORdriver())
                        my_sa.driver.workflow.add('asym')
                        my_sa.driver.DOEgenerator = Tornado_Generator(alpha)

                        kselect = k[7:] 
                        tornadoInputs[kselect] = {}
                        tornadoOutputs[kselect] = {}

                        my_sa.driver.add_parameter(
                            'asym.' + kselect, start=float(inputs[kselect]))

                        for s in io['outputs']:
                            t = cpnt.get_trait(s)
                            if t.trait_type.__class__.__name__ != 'VarTree':
                                my_sa.driver.add_response('asym.' + s)

                        try:
                            my_sa.run()

                        except NameError as detail:
                            print "att Error:" , detail
                        except TypeError as detail:
                            print "att Error:" , detail
                        except AttributeError as detail:
                            print "att Error:" , detail
                        except ValueError as detail:
                            print "att Error:" , detail
                        except:
                            print sys.exc_info()[0]
                            print "Analysis did not execute properly (sens_flag = True)"
                            failed_run_flag = True
                            failed_run_flag = "Analysis did not execute properly - check input parameters!"
                            draw_plot = False
                            script, div = None, None
                            inputVars = None
                            outputVars = None
                            plot_controls = None

                        else:
                            try:
                                my_sa.driver.case_inputs.asym.list_vars()
                            except:
                                draw_plot = False
                                script, div = None, None
                                inputVars = None
                                outputVars = None
                                plot_controls = None

                            else:
                                draw_plot = True
                                for val in my_sa.driver.case_inputs.asym.list_vars():
                                    try:
                                        tornadoInputs[val] = {
                                            'value': my_sa.driver.case_inputs.asym.get(val),
                                            'units': getattr(cpnt.get_trait(val), 'units')}
                                    except Exception:
                                        pass
                                
                                global myUnits
                                for val in my_sa.driver.case_outputs.asym.list_vars():
                                    try:
                                        tmp = my_sa.driver.case_outputs.asym.get(val)
                                    except Exception:
                                        print val
                                        pass
                                    else:
                                        if(isinstance(tmp.pop(), np.float64)):
                                            tornadoOutputs[kselect][val] = {
                                                'value': tmp,
                                                'units': getattr(cpnt.get_trait(val), 'units')}
                                            if val not in outputVars:
                                                outputVars.append(val)
                                            myUnits[val] = getattr(cpnt.get_trait(val), 'units')
                                        else:
                                            if val not in removeFromOutputs:
                                                removeFromOutputs.append(val)

                                # after each run, set the attributes back to baseline
                                setattr(
                                cpnt, kselect, json2type[
                                    io['inputs'][kselect]['type']](
                                    inputs[kselect]))

                            script, div = prepare_plot(tornadoPlt,(""), ([], [], [] , [], [], [],[]))
                            plot_controls = True

                io = traits2jsondict(cpnt)

                # remove the outputs that didnt work for every parameter
                for el in removeFromOutputs:
                    if el in outputVars:
                        outputVars.remove(el)
            
                return render_template(
                    'webgui.html',
                    inputs=WebGUIForm(
                        io['inputs'],
                        run=True,
                        sens_flag=sens_flag)(
                        MultiDict(inputs)),
                    extra_inputs=extra_inputs,
                    name=cpname,
                    plot_script=script,
                    plot_div=div,
                    draw_sens_plot=draw_plot,
                    plot_controls=plot_controls,
                    plot_outputVars=outputVars,
                    group_list=group_list,
                    group_dic=group_dic,
                    desc=desc,
                    failed_run_flag=failed_run_flag,
                    sens_flag=sens_flag,
                    tornado_flag=tornado)

            else:  # sens_flag == True
                my_sa = Assembly()
                my_sa.add('asym', cpnt)
                my_sa.add('driver', DOEdriver())
                my_sa.driver.workflow.add('asym')
                my_sa.driver.DOEgenerator = Uniform(
                    int(inputs['iteration_count']))

                # using add_parameter and add_response not only tells the DOEdriver what variables to vary, 
                # but also tells the driver what information to store in the case_input and case_output variable trees.
                extra_inputs = {
                    "alpha": 20, 
                    "sensitivity_iterations": int(
                        inputs['iteration_count'])}
                skipInputs = ['iteration_count']    
                # inputs variable currently has all the allowable inputs. 
                for k in inputs.keys():
                    if k in skipInputs:
                        continue
                    try:
                        if k in io['inputs']:  # io = traits2jsondict(cpnt)
                            setattr(
                                cpnt, k, json2type[
                                    io['inputs'][k]['type']](
                                    inputs[k]))
                    except:
                        print "Something went wrong when setting the model inputs, one of them may have a wrong type"
                        failed_run_flag = True
                        failed_run_flag = "Something went wrong when setting the model inputs, one of them may have a wrong type"
                        flash(failed_run_flag)
                    else:
                        # this adds the input variable to vary 
                        if 'select.' in k:
                            for kselect in inputs.keys():
                                if 'select.' + kselect == k and 'low.' + kselect in inputs.keys() and 'high.' + kselect in inputs.keys():
                                    my_sa.driver.add_parameter(
                                        'asym.' + kselect, low=float(inputs['low.' + kselect]), high=float(inputs['high.' + kselect]))

                # this selects the valid output variables
                for s in io['outputs']:
                    t = cpnt.get_trait(s)
                    if t.trait_type.__class__.__name__ != 'VarTree':
                        my_sa.driver.add_response('asym.' + s)
                try:
                    my_sa.run()

                except:
                    print "Analysis did not execute properly (sens_flag = True)"
                    failed_run_flag = "Analysis did not execute properly - check input parameters!"
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

                        # Make plotting of results available (Severin)
                        global sensitivityResults
                        sensitivityResults = {
                            "inputs": {},
                            "outputs": {}
                        }

                        inputVars, outputVars = [], []

                        for val in my_sa.driver.case_inputs.asym.list_vars():
                            temp = val
                            try:
                                sensitivityResults['inputs'][val] = {
                                    'value': my_sa.driver.case_inputs.asym.get(val),
                                    'units': getattr(cpnt.get_trait(val), 'units')}
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
                                if(isinstance(tmp.pop(), np.float64)):
                                    sensitivityResults['outputs'][val] = {
                                        'value': tmp,
                                        'units': getattr(cpnt.get_trait(val), 'units')}
                                    outputVars.append(val)

                        script, div = prepare_plot(
                            SensPlot1D, ("", []), ("", []))
                        plot_controls = True

                io = traits2jsondict(cpnt)
                sub_comp_data = {}
                if isinstance(cpnt, Assembly):
                    sub_comp_data, structure = build_hierarchy(
                        cpnt, sub_comp_data, [])
                    assembly_structure[0]['nodes'] = structure
                    # show both inputs and outputs in right side table
                    outputs = get_io_dict(cpnt)
                    if not failed_run_flag:
                        combIO = outputs['inputs'] + outputs['outputs']
                    else:
                        combIO = None
                return render_template(
                    'webgui.html',
                    inputs=WebGUIForm(
                        io['inputs'],
                        run=True,
                        sens_flag=sens_flag)(
                        MultiDict(inputs)),
                    extra_inputs=extra_inputs,
                    outputs=combIO,
                    name=cpname,
                    plot_script=script,
                    plot_div=div,
                    draw_sens_plot=draw_plot,
                    plot_controls=plot_controls,
                    plot_inputVars=inputVars,
                    plot_outputVars=outputVars,
                    sub_comp_data=sub_comp_data,
                    assembly_structure=assembly_structure,
                    group_list=group_list,
                    group_dic=group_dic,
                    desc=desc,
                    failed_run_flag=failed_run_flag,
                    sens_flag=sens_flag)

        else:

            extra_inputs = {"sensitivity_iterations": 1000, "alpha":20}
            # Show the standard form
            return render_template(
                'webgui.html',
                inputs=WebGUIForm(
                    io['inputs'],
                    run=True,
                    sens_flag=sens_flag)(
                    MultiDict(wt_inputs)),
                extra_inputs=extra_inputs,
                outputs=None,
                name=cpname,
                plot_script=None,
                plot_div=None,
                plot_resources=None,
                sub_comp_data=sub_comp_data,
                assembly_structure=assembly_structure,
                group_list=group_list,
                group_dic=group_dic,
                desc=desc,
                failed_run_flag=failed_run_flag,
                sens_flag=sens_flag)

    fused_webapp.__name__ = 'analysis'
    app.route('/' + 'analysis', methods=['GET', 'POST'])(fused_webapp)


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
            # deterine if input or output
            if(colorName in sensitivityResults['outputs']):
                colors = np.array(
                    sensitivityResults['outputs'][colorName]['value'])
            else:
                colors = np.array(
                    sensitivityResults['inputs'][colorName]['value'])
        else:
            colors = None
    except KeyError:
        script, div = prepare_plot(SensPlot1D, ("", []), ("", []))
        summary = "<p>Error Retrieving Data</p>"
    else:
        if (xUnit == "None" or xUnit is None):
            xUnit = ""
        if (yUnit == "None" or yUnit is None):
            yUnit = ""
        script, div = prepare_plot(SensPlot1D,
                                   (inputName + (" (%s)" % xUnit if xUnit != "" else ""), xArray),
                                   (outputName + (" (%s)" % yUnit if yUnit != "" else ""), yArray),
                                   colorAxis={"name": colorName, "values": colors},
                                   units=(xUnit, yUnit))

        # Produce summary report
        summary = "<p>\n"
        summary += "\t<b>Input Variable: %s </b><br>\n" % inputName
        summary += "\t  Range: %s %s - %s %s<br>\n" % (
            prettyNum(min(xArray)), xUnit, prettyNum(max(xArray)), xUnit)
        summary += "<br>\n"
        summary += "\t<b>Output Variable: %s </b><br>\n" % outputName
        summary += "\t  Range: %s %s - %s %s<br>\n" % (
            prettyNum(min(yArray)), yUnit, prettyNum(max(yArray)), yUnit)
        summary += "\t  Average: %s %s<br>\n" % (
            prettyNum(yArray.mean()), yUnit)
        summary += "\t  Std Dev: %s %s<br>\n" % (
            prettyNum(yArray.std()), yUnit)
        summary += "</p>"
    f = {"script": script, "div": div, "summary": summary}
    return jsonify(**f)

# Bokeh stuff after run
try:
    from bokeh.embed import components
    from bokeh.plotting import *
    from bokeh.charts import Line
    from bokeh.resources import INLINE
    from bokeh.templates import JS_RESOURCES
    from bokeh.util.string import encode_utf8
    from bokeh._legacy_charts import Donut, output_file, show
    from bokeh.palettes import Spectral11
    from bokeh.models import HoverTool
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
        plot_resources = JS_RESOURCES.render(
            js_raw=INLINE.js_raw,
            css_raw=INLINE.css_raw,
            js_files=INLINE.js_files,
            css_files=INLINE.css_files,
        )

        # For more details see:
        #   http://bokeh.pydata.org/en/latest/docs/user_guide/embedding.html#components
        # http://bokeh.pydata.org/en/latest/docs/user_guide/embed.html#components
        # (as of 2015 09 28)
        # components(plot_objs) returns HTML components to embed a Bokeh Plot.
        # THe data for the plot is stored direclty in the returned HTML.
        script, div = components(fig, INLINE)
        return script, div
        # Function used to print pretty numbers

    # Create 1D sensitivitey Bokeh plots
    def SensPlot1D(fig, *args, **kwargs):

        fig = figure(title="Sensitivity Results",
                     x_axis_label=args[0][0],
                     y_axis_label=args[1][0])

        # Set colors according to input
        colors = []
        try:
            colorData = kwargs['colorAxis']['values']
            # colorData has the y-values for the colored coordinate

            for val in colorData:
                d = 200 * (max(colorData) - val) / \
                    (max(colorData) - min(colorData))
                colors.append("#%02x%02x%02x" % (200 - d, 150, d))

        except:
            colors = ["#22AEAA" for i in args[0][1]]

        # plot data
        fig.scatter(args[0][1], args[1][1], size=10, fill_color=colors)

        if(len(args[0][1]) > 0 and len(args[1][1]) > 0 and (kwargs['colorAxis']['name'] != "Mono")):
            # draw color name

            xDiff = max(args[0][1]) - min(args[0][1])
            yDiff = max(args[1][1]) - min(args[1][1])

            xPos = min(args[0][1]) + 0.05 * xDiff
            yPos = max(args[1][1]) + 0.10 * yDiff

            fig.text(
                x=xPos + 0.125 * xDiff,
                y=yPos - 0.05 * yDiff,
                text=["%s" % kwargs['colorAxis']['name']],
                text_align="center")
            # draw color scale
            fig.line(
                x=[xPos, xPos + 0.25 * xDiff],
                y=[yPos, yPos],
                line_color="black")

            fig.circle(x=xPos, y=yPos, size=10, fill_color="#0096C8")
            fig.circle(
                x=xPos + 0.25 * xDiff,
                y=yPos,
                size=10,
                fill_color="#C89600")

            fig.text(
                x=xPos,
                y=yPos +
                0.02 *
                yDiff,
                text=[
                    "%s" %
                    prettyNum(
                        min(colorData))],
                text_align="center")
            fig.text(
                x=xPos +
                0.25 *
                xDiff,
                y=yPos +
                0.02 *
                yDiff,
                text=[
                    "%s" %
                    prettyNum(
                        max(colorData))],
                text_align="center")
        return fig

    def CompareResultsPlot(fig, *args, **kwargs):
        """ Configures the compare results plot """
        if len(args) == 0:
            pass
        fig = figure(title="Compare Results",
                     x_axis_label=args[0][0],
                     y_axis_label=args[1][0],
                     tools="crosshair,pan,wheel_zoom,box_zoom,reset,hover,previewsave")

        
        numDataPoints = len(args[0][1])
        source = ColumnDataSource(
            data=dict(
                x=args[0][1],
                y=args[1][1],
                label=[i + 1 for i in range(numDataPoints)]
            )
        )
        fig.circle(
            'x',
            'y',
            color="#2222aa",
            line_width=2,
            source=source,
            size=12)

        hover = fig.select(dict(type=HoverTool))

        hover.tooltips = OrderedDict([
            ("x", "%s" % args[0][0]),
            ("y", "%s" % args[1][0]),
            ("(x,y)", "(@x, @y)"),
            ("Case", "@label")
        ])
        return fig
    


# --------------------------


    def tornadoPlt(fig, *args, **kwargs):
        if len(args) != 2:
            return fig
    
        try:
            totals = args[1][0]
            lows = args[1][1]
            highs = args[1][2]
            values = args[1][3]
            names = args[1][4]
            outputName = args[1][5]

            # create a new plot with a title and axis labels
            fig = figure(title="Parameter Sensitivity", x_axis_label=args[0], y_axis_label='Parameters')

            # iterate through palette
            import itertools
            palette = itertools.cycle(Spectral11)

            def addBar(top, bottom, left, right):
                fig.quad(top=top, bottom=bottom, left=left, right=right, color=palette.next())

            def mtext(x, y, textstr, color="black"):
                fig.text(x, y, text=[textstr],
                text_color=color, text_align="center", text_font_size="10pt")

            numVars = len(lows)
            start = numVars * 2
            for i in range(len(lows)):
                if highs[i] >= lows[i]:
                    mtext(lows[i]-.03*lows[i], start-.75, prettyNum(lows[i]), "red")
                    mtext(highs[i]+.03*highs[i], start-.75, prettyNum(highs[i]),"green")
                else:
                    mtext(lows[i]+.03*lows[i], start-.75, prettyNum(lows[i]), "red")
                    mtext(highs[i]-.03*highs[i], start-.75, prettyNum(highs[i]), "green")
                addBar(start, start-1.25, lows[i], highs[i])
                mtext(values[i], start, names[i])
                start -= 1.75

            # add baseline
            fig.line([values[0], values[0]],[numVars*2, start+.5], line_width=2, line_color="black")
            mtext(values[0], start-.5, prettyNum(values[0]))
            mtext(values[0], start, "Baseline")
        
        except:
            # create a new plot with a title and axis labels
            fig = figure(title="Parameter Sensitivity", x_axis_label=None , y_axis_label='Parameters')
        return fig


@app.route("/tornado", methods=['POST'])
def GetTornado():
    outputName = str(request.form['outVar'])
    global tornadoInputs
    global tornadoOutputs
    variables = tornadoInputs.keys()  
    lows, highs, values, totals = [], [], [], []
    names = variables[:]
    for i in range(len(variables)):
        low_val = tornadoOutputs[variables[i]][outputName]['value'][0]
        lows.append(low_val)
        high_val = tornadoOutputs[variables[i]][outputName]['value'][2]
        highs.append(high_val)
        val = tornadoOutputs[variables[i]][outputName]['value'][1]
        values.append(val)
        totals.append(abs(high_val - low_val))
        base = tornadoOutputs[variables[0]][outputName]['value'][1] 

    # insertion sort based on totals.
    if (len(totals)-1) > 0:
        for i in range(len(totals)-1):
            i += 1
            temp_total = totals[i]
            temp_lows = lows[i]
            temp_highs = highs[i]
            temp_name = names[i]
            j = i - 1
            while j >= 0 and totals[j] > temp_total:
                totals[j+1] = totals[j]
                lows[j+1] = lows[j]
                highs[j+1] = highs[j]
                names[j+1] = names[j]
                j = j - 1
            totals[j+1] = temp_total
            lows[j+1] = temp_lows
            highs[j+1] = temp_highs
            names[j+1] = temp_name
        totals.reverse()
        lows.reverse()
        highs.reverse()
        names.reverse()
    try:
        yUnit = myUnits[outputName]
    except KeyError:
        script, div = prepare_plot(tornadoPlt, ("", []), ("", []))
        summary = "<p>Error Retrieving Data</p>"
    else:
        if (yUnit == "None" or yUnit is None):
            yUnit = ""
        script, div = prepare_plot(tornadoPlt,
                                   (outputName + (" (%s)" % yUnit if yUnit != "" else "")),
                                   (totals, lows, highs, values, names, outputName) )

    f = {"script": script, "div": div}
    return jsonify(**f)
tornadoPlt.__name__ = 'tornadoPlt'
app.route("/tornado", methods=['GET', 'POST'])(tornadoPlt)



def saveUnits(inputList): 
    """ Saves the units to a global variable for use later (when using compare case feature).
    Saves only number types, which are identified if they have units -- compared to booleans or "geared"
    """
    global myUnits
    for el in inputList:
        if el['name'] not in myUnits.keys() and 'units' in el.keys():
            myUnits[el['name']] = el['units']
        elif el['name'] not in myUnits.keys() and isinstance(el['state'], NumberTypes):
            myUnits[el['name']] = None 





##########################################################################
# Initial global values
cpnt = None
desc = ''
analysis = 'Individual Analysis'
tornadoInputs = {}
tornadoOutputs = {}
sensitivityResults = {"empty": True}
myUnits = {"empty": True}
debug = False

