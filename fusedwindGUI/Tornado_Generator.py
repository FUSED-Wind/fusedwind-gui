""" Tornado_generator plugs into the DOEgenerator socket on a DOEdriver. Sets up a DOE for tornado plots"""

import numpy as np
from numpy import linspace,random
from openmdao.main.datatypes.api import Int
from openmdao.lib.casehandlers.api import ListCaseIterator
from openmdao.main.interfaces import implements, IDOEgenerator
from openmdao.main.api import Container

class Tornado_Generator(Container):
    """ Tornado_generator plugs into the DOEgenerator socket on a DOEdriver. Sets up a DOE for tornado plots"""
    implements(IDOEgenerator)
    
    # pylint: disable-msg=E1101
    num_parameters = Int(0, iotype="in", desc="Number of independent "
                                              "parameters in the DOE.")
    num_samples = Int(3, iotype="in", desc="Number of total samples in "
                                              "the DOE.")
    alpha = None
    
    def __init__(self, alpha=None, *args, **kwargs):
    
        super(Tornado_Generator, self).__init__(*args, **kwargs)
        
        # num_samples defaults to 3 because low, base, high values required for each parameter

        if alpha is not None:
            self.alpha = float(alpha)/100

    
    def __iter__(self):
        """Return an iterator over our sets of input values"""
        if self.num_samples != 3: 
            raise ValueError("Tornado must have 3 samples")
        
        start = 1-self.alpha
        return (np.array([start + x*self.alpha for i in range(self.num_parameters)]) for x in range(self.num_samples+1))    
        # the +1 is necessary at the end because OpenMDAO cuts a number out for some reason ??




# --------------------------------------------------------------------

import csv
import numpy as np

# pylint: disable-msg=E0611,F0401
from openmdao.main.hasparameters import ParameterGroup
from openmdao.main.datatypes.api import Bool, Slot, Float, Str
from openmdao.main.interfaces import IDOEgenerator
from openmdao.lib.drivers.caseiterdriver import CaseIteratorDriver

def check_parameter(parameter):
    try:
        if parameter.vartypename == 'Array':
            if 'float' not in parameter.valtypename:
                msg = "TORdriver cannot add array parameter '{}'" \
                      " because target is not of type 'numpy.float'."
                msg = msg.format(parameter.name)

                raise TypeError(msg)

        elif not parameter.vartypename == 'Float':
            msg = "TORdriver cannot add parameter '{}'" \
                  " because target is not of type 'Float'."
            msg = msg.format(parameter.name)

            raise TypeError(msg)

    except AttributeError as exception:
        print "exception raised in check_parameter"
        if not parameter.typename == 'float':
            msg = "TORdriver cannot add parameter group '{}'" \
                  " because targets are not of type 'float'."

            msg = msg.format(parameter.name)

            raise TypeError(msg)



class TORdriver(CaseIteratorDriver):
    """ Driver for Tornado Design of Experiments. """
    # pylint: disable-msg=E1101
    DOEgenerator = Slot(IDOEgenerator, required=True,
                        desc='Iterator supplying normalized DOE values.')

    record_doe = Bool(True, iotype='in',
                      desc='Record normalized DOE values to CSV file.')

    doe_filename = Str('', iotype='in',
                       desc='Name of CSV file to record to'
                            ' (default is <driver-name>.csv).')

    def add_parameter(self, target, low=None, high=None,
                      scaler=None, adder=None, start=None,
                      fd_step=None, name=None, scope=None):
        super(TORdriver, self).add_parameter(target, low, high, scaler, adder,
            start, fd_step, name, scope)
        parameters = self.get_parameters()

        try:
            parameter = parameters[target]
        except KeyError as exception:
            try:
                parameter = parameters[name]
            except KeyError as exception:
                parameter = target

        try:
            check_parameter(parameter)
        except TypeError as type_error:
            try:
                self.remove_parameter(parameter.name)
            except AttributeError as attr_error:
                self.remove_parameter(tuple(parameter.targets))
                self.raise_exception(type_error.message, type_error.__class__)

    def get_starter(self, dtype='d'):
        result = []
        for param in self.get_parameters().values():
            result.extend([param.start])
        if dtype:
            result = np.array(result, dtype)
        return result

    def execute(self):
        """Generate and evaluate cases."""
        self.set_inputs(self._get_cases())
        self._csv_file = None
        try:
            super(TORdriver, self).execute()
        finally:
            if self._csv_file is not None:
                self._csv_file.close()

    def _get_cases(self):
        """Generate each case."""
        self.DOEgenerator.num_parameters = self.total_parameters()
        record_doe = False
        if record_doe:
            if not self.doe_filename:
                self.doe_filename = '%s.csv' % self.name

            self._csv_file = open(self.doe_filename, 'wb')
            csv_writer = csv.writer(self._csv_file)

        start = self.get_starter()

        for row in self.DOEgenerator:

            yield row * start


