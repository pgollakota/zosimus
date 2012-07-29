Welcome to Zosimus!
===================

    "If you are not embarrassed by the first version of your product, you’ve launched too late." - Reid Hoffman, Founder of LinkedIn

Zosimus is a Django project that lets you introspect a database and plot the charts.

.. warning: This project is not production ready!!! Use at your own risk.

What's the catch?
=================

* This is a proof of concept application and is more unstable than a drunken monkey on Speed.
* If your table names or column names contain spaces or funny characters, this will blow up.
* You can only plot bar charts, that too date and time columns are not supported.
* It's not been tested. Your database may blow up, your server may melt, your eyes may bleed, ... you get the point.
* *Nothing* has been defensively coded.

How to get started?
===================

* Download and install the django project.
* Syncdb and the server.
* Go to the home page.
* Add a data source (click on the top right).
* Create your chart.

License
========

``Zosimus`` is licensed under the BSD license. See the ``LICENSE`` file for more information.

External libraries
==================

``Zosimus`` uses external libraries are licensed differently.

- `Twitter Bootstrap <http://twitter.github.com/bootstrap/>`_ is licensed under
  `Apache License v2.0 <http://twitter.github.com/bootstrap/>_
- `jQuery`` is licensed under both
   `MIT License and GNU General Public License (GPL) Version 2 <http://jquery.org/license/>`_.
- `Highcharts <http://highcharts.com>`_ is licensed under the `Highcharts license
   <http://www.highcharts.com/license>`_
