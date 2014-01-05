from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('smartfeed.django.app.views',
	url(r'^items/$', 'items'),
	url(r'^subscriptions/$', 'subscriptions'),
)
