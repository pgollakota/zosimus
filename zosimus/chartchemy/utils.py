import simplejson
from django.utils.html import escape


def render_highcharts_options(render_to, categories, series, title, x_axis_title, y_axis_title, series_name):
    """Accepts the parameters to render a chart and returns a JSON serialized Highcharts options object."""

    # Escape all the character strings to make them HTML safe.
    render_to = escape(render_to) if render_to else render_to
    title = escape(title) if title else title
    x_axis_title = escape(x_axis_title) if x_axis_title else x_axis_title
    y_axis_title = escape(y_axis_title) if y_axis_title else y_axis_title
    # Categories (dimensions) come from the use. Escape them too.
    categories = [escape(c) for c in categories]

    hco = {
        "chart": {
            "renderTo": render_to,
            "type": 'column'
        },
        "title": {
            "text": title
        },
        "xAxis": {
            "title": {
                "text": x_axis_title
            },
            "categories": categories
        },
        "yAxis": {
            "title": {
                "text": y_axis_title,
            }
        },
        "series": [{
            "name": series_name,
            "data": series,
        }]
    }

    return simplejson.dumps(hco, use_decimal=True)
