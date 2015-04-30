# DTU Wind Energy Systems Engineering Analysis Model (SEAM)


## Prerequisites

SEAM is written primarily in Python and uses [OpenMDAO](http://openmdao.org/) as the underlying framework for connecting its sub-models.
Before installing SEAM, you therefore need to install OpenMDAO according to the [installation instructions](http://openmdao.org/docs/getting-started/index.html).

## Installation

SEAM can be installed using the ``SEAM_installer.py`` script, which will install the main SEAM package and all of the sub-models of SEAM.

    $ python SEAM_installer.py

If you do not already have FUSED-Wind installed, this will also be installed automatically.

## Tests

Once installed you should be able to import SEAM in Python:

    $ python
    >>> import SEAM

To test that SEAM and all its sub-models were installed correctly run the ``SEAM_tests.py`` file:

    $ python SEAM_tests.py

If all tests passed you should see an "OK".

## Documentation

SEAM is documented with Sphinx, and you can build the complete documentation for SEAM and all its sum-models by typing make from this directory:

    $ make
    
To view it in a web-browser, open the file ``_build/html/index.html`` or on Linux and Mac type:

    $ open _build/html/index.html


## Examples

Examples of how to run SEAM can be found in XX