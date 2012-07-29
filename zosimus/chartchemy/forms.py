from django import forms
from django.forms import ModelForm, widgets

from models import Datasource, Chart


class DatasourceForm(ModelForm):
    """Form to add a new datasource."""
    class Meta:
        model = Datasource
        fields = ('name', 'dbtype', 'dbname', 'dbusername', 'dbpassword', 'dbhost')
        widgets = {
            'name': widgets.TextInput(attrs={'class': 'span2'}),
            'dbtype': widgets.Select(attrs={'class': 'span2'}),
            'dbname': widgets.TextInput(attrs={'class': 'span2'}),
            'dbusername': widgets.TextInput(attrs={'class': 'span1'}),
            'dbpassword': widgets.PasswordInput(attrs={'class': 'span1'}),
        }


class CreateChartForm(ModelForm):
    """Form to set the datasource for a chart."""
    def __init__(self, *args, **kwargs):
        usr_ = kwargs.pop('usr_', None)
        super(CreateChartForm, self).__init__(*args, **kwargs)
        self.fields['datasource'] = forms.ModelChoiceField(queryset=Datasource.objects.filter(user=usr_))

    class Meta:
        model = Chart
        fields = ('name', 'datasource')


class ChartTableForm(ModelForm):
    """Form to set the table for a chart."""
    table_name = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(ChartTableForm, self).__init__(*args, **kwargs)
        table_names = [n for n, _t in self.instance.datasource.tables.items()]
        self.fields['table_name'].choices = list(zip(table_names, table_names))

    class Meta:
        model = Chart
        fields = ('table_name', )


class ColumnChartAxesForm(ModelForm):
    """Form to set the x and y axes and the aggregation function for y-axis for a chart."""
    CHOICES = (('avg', 'Avg'), ('count', 'Count'), ('max', 'Max'), ('min', 'min'), ('sum', 'Sum'),)
    x_axis = forms.ChoiceField()
    y_axis = forms.ChoiceField()
    aggr_func_name = forms.ChoiceField(choices=CHOICES)

    def __init__(self, *args, **kwargs):
        super(ColumnChartAxesForm, self).__init__(*args, **kwargs)
        measures = self.instance.datasource.measures.get(self.instance.table_name, [])
        dimensions = self.instance.datasource.dimensions.get(self.instance.table_name, [])
        self.fields['x_axis'].choices = list(zip(dimensions, dimensions))
        self.fields['y_axis'].choices = list(zip(measures, measures))

    class Meta:
        model = Chart
        fields = ('x_axis', 'y_axis', 'aggr_func_name')
