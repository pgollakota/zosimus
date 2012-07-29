import simplejson


def render_highcharts_options(render_to, categories, series, title, x_axis_title, y_axis_title, series_name):

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
