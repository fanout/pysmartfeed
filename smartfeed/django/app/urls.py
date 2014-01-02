from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('smartfeed.django.views',
	url(r'^items/$', 'items'),
	url(r'^subscriptions/$', 'subscriptions'),
)
