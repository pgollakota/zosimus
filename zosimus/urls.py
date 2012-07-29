from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('zosimus.chartchemy.views',
    url(r'^$', 'home', name='home'),
    url(r'^datasources/$', 'datasources'),
    url(r'^datasources/(?P<pk>\d+)/$', 'datasource_details'),
    url(r'^datasources/(?P<pk>\d+)/delete/$', 'delete_datasource'),
    url(r'^charts/$', 'charts'),
    url(r'^charts/(?P<pk>\d+)/$', 'chart_details'),
    url(r'^charts/(?P<pk>\d+)/delete/$', 'delete_chart'),

    (r'^accounts/', include('django.contrib.auth.urls')),
)
