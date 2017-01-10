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
from collections import OrderedDict
import json
import yaml
import types
from fusedwindGUI import app
from Tornado_Generator import *


# Bokeh stuff after run
try:
    from bokeh.embed import components
    from bokeh.plotting import *
    from bokeh.resources import INLINE
    from bokeh.core.templates import JS_RESOURCES
    from bokeh.util.string import encode_utf8
    from bokeh.palettes import Spectral11
    from bokeh.models import HoverTool, Arrow, OpenHead, NormalHead, VeeHead
    from bokeh.models.glyphs import Quad
    from bokeh.charts import show, output_file
    use_bokeh = True
except Exception as e:
    print 'Bokeh hasnt been installed properly:', str(e)
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
                     y_axis_label=args[1][0],
                     toolbar_location="above",
                     tools="crosshair,pan,wheel_zoom,box_zoom,reset,hover,previewsave")

        # Set colors according to input
        colors = []
        try:
            colorData = kwargs['colorAxis']['values']
            # colorData has the y-values for the colored coordinate

            for val in colorData:
                d = 200 * (max(colorData) - val) / \
                    (max(colorData) - min(colorData))
                colors.append("#%02x%02x%02x" % (200 - d, 150, d))
            source = ColumnDataSource(
            dict(
                x=args[0][1],
                y=args[1][1],
                colorData=colorData))
            fig.circle( x="x", y="y", size=10, fill_color=colors, source=source)


        except:
            colors = ["#22AEAA" for i in args[0][1]]

        # plot data
            fig.circle(x=args[0][1], y=args[1][1], size=10, fill_color=colors)

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
        try:
            hover = fig.select(dict(type=HoverTool))
            hover.tooltips = OrderedDict([
                ("%s" % args[0][0], "@x"),
                ("%s" % args[1][0], "@y"),
                ("%s" % kwargs['colorAxis']['name'], "@colorData")

            ])
        except KeyError:
            pass
        except:
            pass
        return fig

    def CompareResultsPlot(fig, *args, **kwargs):
        """
        Configures the compare results plot
        Params:
            @fig: figure object from bokeh
            @args: data for plotting
            @kwargs: not used
        Returns:
            @fig: returns the bokeh figure object after populating it
        """
        if len(args) == 0:
            pass
        fig = figure(title="Compare Results",
                     x_axis_label=args[0][0],
                     y_axis_label=args[1][0],
                     tools="crosshair,pan,wheel_zoom,box_zoom,reset,hover,previewsave",
                     toolbar_location="above")

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
        """
        Generates a tornado plot for sensitivity analysis.
        Params:
            @fig: figure object from bokeh
            @args: parameters are either empty or from the GetTornado() function.
                   these args include numerical values to be plotted
            @kwargs: keywords aren't used in this function, but
                     added as optional input for consistency with other plots
        Returns:
            @fig: returns the bokeh figure object after populating it

        """
        if len(args) != 2:
            return fig
        try:
            import itertools
            totals = args[1][0]
            lows = args[1][1]
            highs = args[1][2]
            values = args[1][3]
            names = args[1][4]
            outputName = args[1][5]

            # create a new plot with a title and axis labels
            fig = figure(title="Parameter Sensitivity", x_axis_label=args[0], y_axis_label='Parameters',
                toolbar_location="above", tools="crosshair,pan,wheel_zoom,box_zoom,reset,hover,previewsave")

            def mtext(x, y, textstr, color="black"):
                """
                Adds text at coordinates
                Params:
                    @x: x coordinate, type = int, float, etc.
                    @y: y coordinate
                    @textstr: text to display, type='str'
                    @color: color of text, can be str or hex values
                Returns:
                    None
                """
                fig.text(x, y, text=[textstr],
                text_color=color, text_align="center", text_font_size="10pt")

            numVars = len(lows)
            start = numVars * 3

            # colors is a palette for a gradient between red and green. Can change this to desired colors
            # via importing an existing palette or changing values below
            colors = ['#178726','#168722','#16881E','#168919','#178A16','#1B8B15','#208C15','#248D15','#298E15',
                    '#2E8F15','#329014','#379014','#3C9114','#419214','#469313',
                    '#4B9413','#519513','#569613','#5B9712','#619812','#679912','#6C9A12','#729A11','#789B11',
                    '#7E9C11','#849D10','#8A9E10','#919F10','#97A00F','#9DA10F','#A29F0F','#A39B0E','#A3960E',
                    '#A4910E','#A58B0D','#A6860D','#A7810D','#A87C0C','#A9760C','#AA700C','#AB6B0B','#AC650B',
                    '#AD5F0B','#AD590A','#AE530A','#AF4D09','#B04609','#B14009','#B23908','#B33308','#B42C07',
                    '#B52507','#B61E06','#B61706','#B71006','#B80905','#B90508','#BA040F',
                    '#BB0415','#BC031C','#BD0323','#BE022A','#BF0231','#C00139'][::-1]
            # colors = greenBluePalette
            numColors = len(colors)

            # color, width, x-coord, y-coord and relevant information for glyphs
            param_colors = []
            c_width, c_x, c_y, c_lows, c_highs, c_base, c_names = [], [], [], [], [], [], []

            # for every parameter the user selected
            for i in range(numVars):
                param_range = highs[i]-lows[i]
                width = param_range/numColors
                mtext(values[0], start, names[i] )

                # sometimes increasing parameter value decreases output value
                if highs[i] < lows[i]:
                    temp = highs[i]
                    for x in range(numColors):
                        c_lows.append(lows[i])
                        c_highs.append( highs[i] )
                        c_base.append(values[0])
                        c_width.append(width)
                        c_y.append(start-1)
                        c_x.append(temp-width/2)
                        c_names.append(names[i])
                        temp-=width
                        param_colors.append(colors[numColors-x-1])
                else:
                    temp = lows[i]
                    for x in range(numColors):
                        c_lows.append(lows[i])
                        c_highs.append( highs[i] )
                        c_base.append(values[0])
                        c_width.append(width)
                        c_y.append(start-1)
                        c_x.append(temp+width/2)
                        c_names.append(names[i])
                        temp+= width
                        param_colors.append(colors[x])
                start -= 3

            # data source for graph
            source = ColumnDataSource(
                data=dict(
                    x=c_x,
                    y=c_y,
                    width=c_width,
                    colors=param_colors,
                    lows=c_lows,
                    highs=c_highs,
                    base=c_base,
                    names=c_names))

            # adds rectangle glyphs
            fig.rect(x='x', y='y', width='width', height=2,
                       color='colors', source=source)

            # implement hover tool
            hover = fig.select(dict(type=HoverTool))
            hover.tooltips = OrderedDict([
                ("Parameter", "@names"),
                ("decreasing parameter results in this %s:" %outputName , "@lows" ),
                ("base %s:" %outputName, "@base"),
                ("increasing parameter value results in this %s:" %outputName, "@highs")

            ])

            # add Arrow pointers
            start = numVars * 3
            for i in range(numVars):
                fig.add_layout(Arrow(end=VeeHead(size=17), line_color="black",
                    x_start=lows[i], y_start=start, x_end=lows[i], y_end=start-2))
                fig.add_layout(Arrow(end=VeeHead(size=17), line_color="black",
                    x_start=highs[i], y_start=start-2, x_end=highs[i], y_end=start))
                start -= 3

            # add baseline
            fig.line([values[0], values[0]],[numVars*3, start+.5], line_width=1.5, line_color="black")
            fig.yaxis.visible = None
            mtext(values[0], start-.5, prettyNum(values[0]))
            mtext(values[0], start, "Baseline")

        except:
            # create a new plot with a title and axis labels
            fig = figure(title="Parameter Sensitivity", x_axis_label=None , y_axis_label='Parameters')
        return fig



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
            if len(myDict['desc'])>0:
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

