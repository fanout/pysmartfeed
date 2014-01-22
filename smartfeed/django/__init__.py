import threading
import importlib
from django.conf import settings
import smartfeed

tlocal = threading.local()

def load_class(name):
	at = name.rfind('.')
	if at == -1:
		raise ValueError('class name contains no \'.\'')
	module_name = name[0:at]
	class_name = name[at + 1:]
	return getattr(importlib.import_module(module_name), class_name)()

# load and keep in thread local storage
def get_class(name):
	if not hasattr(tlocal, 'loaded'):
		tlocal.loaded = dict()
	c = tlocal.loaded.get(name)
	if c is None:
		c = load_class(name)
		tlocal.loaded[name] = c
	return c

def get_class_from_setting(setting_name, default=None):
	if hasattr(settings, setting_name):
		return get_class(getattr(settings, setting_name))
	elif default:
		return get_class(default)
	else:
		raise ValueError('%s not specified, and default not provided' % setting_name)

class Mapper(object):
	def get_model_class(self, request, params):
		return None

	def get_feed_id(self, request, params):
		raise NotImplementedError()

	def get_formatter(self, request, params):
		# call the global method by default
		return get_default_formatter()

	def get_grip_prefix(self, request, params):
		# call the global method by default
		return get_grip_prefix()

class DefaultMapper(Mapper):
	def get_feed_id(self, request, params):
		base = params['base']
		order = request.GET.get('order')
		if order is None:
			order = 'created'
		return smartfeed.encode_id_part(base) + '-' + smartfeed.encode_id_part(order)

class EpcpPublisher(smartfeed.EpcpPublisher):
	def __init__(self):
		pcs = smartfeed.PubControlSet()
		if hasattr(settings, 'PUBLISH_SERVERS'):
			pcs.apply_config(settings.PUBLISH_SERVERS)
		if hasattr(settings, 'GRIP_PROXIES'):
			pcs.apply_grip_config(settings.GRIP_PROXIES)
		super(EpcpPublisher, self).__init__(pcs, prefix=get_grip_prefix(), formatter=get_default_formatter())

class RedisModel(smartfeed.RedisModel):
	def __init__(self):
		host = getattr(settings, 'REDIS_HOST', 'localhost')
		port = getattr(settings, 'REDIS_PORT', 6379)
		db = getattr(settings, 'REDIS_DB', 0)
		super(RedisModel, self).__init__(host=host, port=port, db=db, prefix=get_redis_prefix(), publisher=get_default_publisher())

def get_default_mapper():
	return get_class_from_setting('SMARTFEED_MAPPER_CLASS', 'smartfeed.django.DefaultMapper')

def get_default_formatter():
	return get_class_from_setting('SMARTFEED_FORMATTER_CLASS', 'smartfeed.DefaultFormatter')

def get_default_publisher():
	return get_class_from_setting('SMARTFEED_PUBLISHER_CLASS', 'smartfeed.django.EpcpPublisher')

def get_default_model():
	return get_class_from_setting('SMARTFEED_MODEL_CLASS')

def get_redis_prefix():
	return getattr(settings, 'SMARTFEED_REDIS_PREFIX', 'smartfeed-')

def get_grip_prefix():
	return getattr(settings, 'SMARTFEED_GRIP_PREFIX', 'smartfeed-')

def check_grip_sig(request):
	if not hasattr(settings, 'GRIP_PROXIES'):
		return False
	grip_sig = request.META.get('HTTP_GRIP_SIG')
	if not grip_sig:
		return False
	return smartfeed.check_grip_sig(grip_sig, settings.GRIP_PROXIES)
