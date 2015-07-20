import os
from webapp import app
from webapp.views import webgui

from openmdao.main.api import set_as_top
try:
    from wisdem.lcoe.lcoe_csm_assembly import lcoe_csm_assembly
    webgui(set_as_top(lcoe_csm_assembly()), app)
except:
    pass
try:
    from wisdem.lcoe.lcoe_se_seam_assembly import create_example_se_assembly
    lcoe_se = create_example_se_assembly('I', 0., True, False, False,False,False, '')
    webgui(lcoe_se, app)
except:
    print 'lcoe_se_seam_assembly could not be loaded!'
try:
    from wisdem.lcoe.lcoe_se_seam_opt import create_example_se_opt
    lcoe_opt = create_example_se_opt('I', 0., True, False, False,False,False, '')
    webgui(lcoe_opt, app)
except:
    print 'lcoe_se_seam_opt could not be loaded!'

try:
    from SEAM.seam_assemblies import SEAMAssembly
    webgui(set_as_top(SEAMAssembly()), app)
except:
    print 'WARNING: SEAM not installed'

port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port, debug=True)
