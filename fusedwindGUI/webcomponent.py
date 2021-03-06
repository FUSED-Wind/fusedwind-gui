from openmdao.main.api import Component, Container, Assembly
from openmdao.lib.datatypes.api import *
from numpy import array
from requests import get, post
import json
from flask import Flask, request
from flask_wtf import Form, RecaptchaField
from flask.ext.mail import Message, Mail
from wtforms import TextField, HiddenField, FloatField, ValidationError, RadioField,\
    BooleanField, SubmitField, IntegerField, FormField, validators, PasswordField, TextAreaField,\
    SelectField
from wtforms.validators import Required
from flask import Flask, request, render_template, flash
import yaml
from werkzeug.datastructures import MultiDict


json2omdao = {
    'Float': Float,
    'Int': Int,
    'Array': Array,
    'Str': Str,
    'Enum': Enum,
    'Bool': Bool
    }

json2type = {
    'Float': float,
    'Int': int,
    'Array': array,
    'Str': str,
    'Enum': str,
    'Bool': bool
    }


def prep_field(dic):
    """Helpful function that translate the FUSED I/O definition into something
    consumable by the wtform field classes
    """
    out = {}
    if 'desc' in dic:
        # capitalize first word of description
        if len(dic['desc'])>0:
            dic['desc'] = dic['desc'][0].upper()+dic['desc'][1:]
        out['description'] = dic['desc']
    if 'default' in dic:
        out['default'] = dic['default']
    if 'values' in dic:
        out['choices'] = [(val, val) for val in dic['values']]
    return out

# A rosetta dictionary to transform between FUSED types into WTForm field types
type_fields = {
    'Float':FloatField,
    'Int':IntegerField,
    'Str':TextField,
    'Array':TextField,
    'Enum': SelectField,
    'Bool': BooleanField
}

def traits2jsondict(cpnt):
    """Get the traits information about the component and return a json dictionary"""
    out = {'inputs':{}, 'outputs':{}}
    for ty, se in zip(['inputs', 'outputs'],
                    [set(cpnt.list_inputs()).difference(Assembly().list_inputs()),
                     set(cpnt.list_outputs()).difference(Assembly().list_outputs())]):
        for s in se:
            t = cpnt.get_trait(s)
            out[ty][s] = {}
            out[ty][s]['type'] = t.trait_type.__class__.__name__
            for d in ['desc', 'default', 'units', 'high', 'low','values','group']:
                val = getattr(t, d)
                if not val == None:
                    out[ty][s][d] = val
            out[ty][s]['state'] = getattr(cpnt, s)

    return out


def start_app(name):
    app = Flask(name)

    @app.route("/")
    def get_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            # To show how to do it, we are going to filter what type of
            # request are we going to show, for example here we are only
            # going to use GET requests
            if "GET" in rule.methods:
                url = rule.rule
                routes.append(url)
        return json.dumps(routes)

    return app



def register_Component(cpnt, app=None):
    if app == None:
        app = start_app(cpnt.__class__.__name__)

    def myflask():
        if request.method == 'POST':
            inputs =  request.form.to_dict()

            ### TODO: make the right format instead of float
            io = traits2json(cpnt)

            for k in io['inputs'].keys():
                setattr(cpnt, k, json2type(io['inputs'][k]['type'])(inputs[k]))
            cpnt.run()
            outputs = {k:getattr(cpnt,k) for k in io['outputs'].keys()}

            return json.dumps(outputs)
        # Publish the interface definition of the class
        return json.dumps(traits2json(cpnt))
    myflask.__name__ = cpnt.__class__.__name__
    app.route('/'+cpnt.__class__.__name__, methods=['GET', 'POST'])(myflask)
    return app


def deploy(cpnt):
    app = start_app(cpnt.__class__.__name__)
    register_Component(cpnt, app)
    app.run()


def convert2omdao(dic, **kwargs):
    type_ = dic['type']
    combined_dict = dict(filter(lambda x: x[0] != 'type', dic.items())
                         + kwargs.items())
    #print combined_dict
    return json2omdao[type_](**combined_dict)


class RESTComponent(Component):
    def __init__(self, url, **kwargs):
        super(RESTComponent, self).__init__(**kwargs)
        self.url = url
        self.fused_io = get(url).json()
        inputs = self.fused_io['inputs']
        outputs = self.fused_io['outputs']

        for k, v in inputs.iteritems():
            self.add(k, convert2omdao(v, iotype='in'))

        for k, v in outputs.iteritems():
            self.add(k, convert2omdao(v, iotype='out'))

        self.set_inputs(**kwargs)

        self.add_io(inputs, outputs)

    def add_io(self, inp, out):
        if not hasattr(self, 'fused_io'):
            self.fused_io = {'inputs':{}, 'outputs':{}}

        self.fused_io['inputs'] = dict(self.fused_io['inputs'].items() +
                                       inp.items())

        self.fused_io['outputs'] = dict(self.fused_io['outputs'].items() +
                                       out.items())

    def get_io(self):
        return traits2json(self)

    def set_inputs(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k in self.list_inputs():
                setattr(self, k, v)

    def __call__(self, **kwargs):
        self.set_inputs(**kwargs)
        self.run()
        return self

    def execute(self):
        inputs = {i:getattr(self, i) for i in self.get_io()['inputs'].keys()}
        outputs = post(self.url, data=inputs).json()
        for o in self.get_io()['outputs'].keys():
            setattr(self, o, outputs[o])





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
    skeys = sorted(dic.keys())

    for k in skeys:
        v = dic[k]
        setattr(MyForm, k, make_field(k, v))


    if sens_flag:
        for k in skeys:
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
