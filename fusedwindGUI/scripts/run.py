#! /usr/bin/env python


import os
from fusedwindGUI import app
from fusedwindGUI.views import webgui

from openmdao.main.api import set_as_top

def main():

    webgui(app)

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

if __name__ == '__main__':

    main()
