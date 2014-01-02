import threading
from django.conf import settings
import smartfeed

tlocal = threading.local()

def get_publisher():
	if not hasattr(tlocal, 'publisher'):
		# FIXME: parse settings to create pcs
		tlocal.publisher = smartfeed.EpcpPublisher(pub_control_set=pcs)
	return tlocal.publisher

def get_model():
	if not hasattr(tlocal, 'model'):
		# FIXME: parse settings and pass redis_* fields
		tlocal.model = smartfeed.RedisQueueModel(publisher=get_publisher())
	return tlocal.model

def get_grip_prefix():
	if hasattr(settings, 'SMARTFEED_GRIP_PREFIX'):
		return settings.SMARTFEED_GRIP_PREFIX
	else:
		return 'smartfeed-'

def check_grip_sig(request):
	grip_sig = request.META.get('HTTP_GRIP_SIG')
	if not grip_sig:
		return False
	return smartfeed.check_grip_sig(grip_sig, settings.GRIP_PROXIES)
