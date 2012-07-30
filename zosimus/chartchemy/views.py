from collections import OrderedDict

import sqlalchemy

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, HttpResponseRedirect

from forms import DatasourceForm, ChartTableForm, ColumnChartAxesForm, CreateChartForm
from models import Datasource, Chart
from zosimus.chartchemy.exceptions import ChartCreationError


@login_required
def home(request):
    datasources = Datasource.objects.filter(user=request.user)
    charts = Chart.objects.filter(user=request.user)
    return render(request, 'chartchemy/home.html', {
        'datasources': datasources,
        'charts': charts
    })


@login_required
def datasources(request):
    """Lists the datasources and also displays a form to add a new one.
    """
    if request.method == 'POST':
        datasource = Datasource(user=request.user)
        form = DatasourceForm(request.POST, instance=datasource)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/datasources/')
    else:
        form = DatasourceForm()

    datasources = Datasource.objects.filter(user=request.user)
    return render(request, 'chartchemy/datasources.html', {
        'form': form,
        'datasources': datasources
    })


@login_required
def delete_datasource(request, pk):
    """Deletes the datasource identified by the pk."""
    try:
        pk = int(pk)
        ds = request.user.datasource_set.get(pk=pk)
        n = ds.chart_set.count()
        ds.delete()
        messages.add_message(request, messages.INFO, 'Deleted datasoure: %d' % pk)
        if n:
            messages.add_message(request, messages.INFO, 'Deleted %d charts related to the datasource.' % n)

    except (ObjectDoesNotExist, ValueError):
        messages.add_message(request, messages.ERROR, 'Cannot find the datasource: %s to delete!' % pk)
    return HttpResponseRedirect('/datasources/')


@login_required
def datasource_details(request, pk):
    """Displays all the details about the datasource identified by the pk."""
    try:
        pk = int(pk)
        ds = request.user.datasource_set.get(pk=pk)
    except (ObjectDoesNotExist, ValueError):
        messages.add_message(request, messages.ERROR, 'Cannot find the datasource: %s!' % pk)
        return HttpResponseRedirect('/datasources/')

    db_layout = OrderedDict((k, {'measures': ds.measures.get(k, []),
                                 'dimensions': ds.dimensions.get(k, [])})
                             for k in sorted(ds.measures.viewkeys() | ds.dimensions.viewkeys()))

    return render(request, 'chartchemy/datasource_detail.html', {
        'db_layout': db_layout,
        'ds': ds
    })


@login_required
def charts(request):
    """Lists the charts and also displays a form to add a new one."""
    if request.method == 'POST':
        chart = Chart(user=request.user)
        form = CreateChartForm(request.POST, instance=chart, usr_=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/charts/%s/' % chart.id)
    else:
        form = CreateChartForm(usr_=request.user)

    charts = Chart.objects.filter(user=request.user)
    return render(request, 'chartchemy/charts.html', {
        'form': form,
        'charts': charts,
    })


@login_required
def delete_chart(request, pk):
    """Displays all the details about the chart identified by the pk."""
    try:
        pk = int(pk)
        ch = request.user.chart_set.get(pk=pk)
        ch.delete()
        messages.add_message("Deleted chart: %s" % pk)
    except (ObjectDoesNotExist, ValueError):
        messages.add_message(request, messages.ERROR, 'Cannot find the chart: %s to delete!' % pk)
    return HttpResponseRedirect('/charts/')


@login_required
def chart_details(request, pk):
    """Displays all the details about the chart identified by the pk.

    Displays two forms - one to choose the table for which to create the chart and a second form
    to select, the x and y axis columns and the aggregation function.
    """

    column_chart = None
    try:
        pk = int(pk)
        ch = request.user.chart_set.get(pk=pk)
    except (ObjectDoesNotExist, ValueError):
        messages.add_message(request, messages.ERROR, 'Cannot find the chart: %s!' % pk)
        return HttpResponseRedirect('/charts/')

    if request.method == 'POST':
        # If the 'Save' button on ChartTableForm has been clicked.
        if 'save_table' in request.POST:
            table_name_original = ch.table_name
            form_table = ChartTableForm(request.POST, instance=ch)
            if form_table.is_valid():
                # If the table name has been changed. Reset the Axes.
                if ch.table_name != table_name_original:
                    ch.x_axis, ch.y_axis, ch.aggr_func_name = None, None, None
                form_table.save()
                return HttpResponseRedirect('/charts/%s/' % ch.id)
        # If the 'Save' button on ColumnChartAxesForm has been clicked.
        elif 'save_axes' in request.POST:
            form_axes = ColumnChartAxesForm(request.POST, instance=ch)
            if form_axes.is_valid():
                form_axes.save()
                return HttpResponseRedirect('/charts/%s/' % ch.id)
    else:
        form_table = ChartTableForm(instance=ch)
        if ch.table_name:
            form_axes = ColumnChartAxesForm(instance=ch)
            if ch.x_axis and ch.y_axis and ch.aggr_func_name:
                column_chart = ch._plot_column_chart()
                try:
                    column_chart = ch._plot_column_chart()
                except (AttributeError, sqlalchemy.exc.OperationalError, ChartCreationError):
                    column_chart = None
                    messages.add_message(request, messages.ERROR,
                                         'Uh Oh! Error creating chart!')
        else:
            form_axes = None

    display_axes_form = False if ch.table_name is None else True

    return render(request, 'chartchemy/chart_detail.html', {
        'form_table': form_table,
        'display_axes_form': display_axes_form,
        'form_axes': form_axes,
        'column_chart': column_chart
    })
