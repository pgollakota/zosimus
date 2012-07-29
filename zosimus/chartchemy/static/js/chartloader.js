// jQuery function to create a chart for each of the HighCharts Chart Options
// JSON object (_chartchemy_hco) passed to web page from the view.
$(document).ready(function() {
		chart = new Highcharts.Chart(_chartchemy_hco);
});