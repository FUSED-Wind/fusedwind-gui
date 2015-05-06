from openmdao.main.api import Component
from openmdao.lib.datatypes.api import Float
from webcomponent import deploy, start_app, register_Component
import os

class Paraboloid(Component):
    """ Evaluates the equation f(x,y) = (x-3)^2 + xy + (y+4)^2 - 3 """

    # set up interface to the framework
    x = Float(0.0, iotype='in', desc='The variable x')
    y = Float(0.0, iotype='in', desc='The variable y')

    f_xy = Float(0.0, iotype='out', desc='F(x,y)')


    def execute(self):
        """f(x,y) = (x-3)^2 + xy + (y+4)^2 - 3
            Minimum: x = 6.6667; y = -7.3333
        """

        x = self.x
        y = self.y

        self.f_xy = (x-3.0)**2 + x*y + (y+4.0)**2 - 3.0

if __name__ == '__main__':
    cpnt = Paraboloid()
    port = int(os.environ.get('PORT', 5000))
    app = start_app(cpnt.__class__.__name__)
    register_Component(cpnt, app)    
    app.run(host='0.0.0.0', port=port)    