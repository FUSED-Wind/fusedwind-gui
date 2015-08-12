#! /usr/bin/env python


import os
from fusedwindGUI import app
from fusedwindGUI.views import webgui

from openmdao.main.api import set_as_top

def main():
    '''try:
        desc = "The NREL Cost and Scaling Model (CSM) is an empirical model for wind plant cost analysis based on the NREL cost and scaling model."
        from wisdem.lcoe.lcoe_csm_assembly import lcoe_csm_assembly
        webgui(set_as_top(lcoe_csm_assembly()), app, desc)
    except:
        pass
    try:
        desc = "The NREL WISDEM / DTU SEAM integrated model uses components across both model sets to size turbine components and perform cost of energy analysis."
        from wisdem.lcoe.lcoe_se_seam_assembly import create_example_se_assembly
        lcoe_se = create_example_se_assembly('I', 0., True, False, False,False,False, '')
        webgui(lcoe_se, app, desc)
    except:
        print 'lcoe_se_seam_assembly could not be loaded!'''

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':

    main()
