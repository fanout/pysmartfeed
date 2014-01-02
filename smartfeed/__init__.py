import threading
import json
import pubcontrol
import gripcontrol

class PubControlSet(object):
	def __init__(self):
		self.pubs = list()

	def clear(self):
		self.pubs = list()

	def add(self, pub):
		self.pubs.append(pub)

	def apply_config(self, config):
		for entry in config:
			if 'control_uri' not in entry:
				continue

			pub = PubControl(entry['control_uri'])
			if 'control_iss' in entry:
				pub.set_auth_jwt({'iss': entry['control_iss']}, entry['key'])

			self.pubs.append(pub)

	def publish(self, channel, item):
		for pub in self.pubs:
			pub.publish_async(channel, item)

def check_grip_sig(grip_sig_header, config):
	for entry in config:
		if 'key' not in entry:
			continue
		if gripcontrol.validate_sig(grip_sig_header, entry['key']):
			return True
	return False

class PositionSpec(object):
	def __init__(self, type, value):
		self.type = type
		self.value = value

class ItemsResult(object):
	def __init__(self):
		self.items = list()
		self.total = None
		self.last_cursor = None

class Formatter(object):
	def is_supported(self, format):
		pass

	def to_format(self, item, format):
		pass

class Publisher(object):
	def psh_sub_set(self, feed_id, uri):
		pass

	def psh_sub_remove(self, feed_id, uri):
		pass

	def xmpp_sub_set(self, feed_id, jid):
		pass

	def xmpp_sub_remove(self, feed_id, jid):
		pass

	def publish(self, feed_id, item, cursor, prev_cursor):
		pass

class Model(object):
	def __init__(self, publisher=None):
		self.publisher = publisher

	def psh_sub_set(self, feed_id, uri):
		self.db_psh_sub_set(feed_id, uri)
		self.publisher.psh_sub_set(feed_id, uri)

	def psh_sub_remove(self, feed_id, uri):
		self.db_psh_sub_remove(feed_id, uri)
		self.publisher.psh_sub_remove(feed_id, uri)

	def xmpp_sub_set(self, feed_id, jid):
		self.db_xmpp_sub_set(feed_id, uri)
		self.publisher.xmpp_sub_set(feed_id, uri)

	def xmpp_sub_remove(self, feed_id, jid):
		self.db_xmpp_sub_remove(feed_id, uri)
		self.publisher.xmpp_sub_remove(feed_id, uri)

	def notify(self, feed_id, item, cursor, prev_cursor):
		self.publisher.publish(feed_id, item, cursor, prev_cursor)

	def get_items(self, feed_id, since_spec, until_spec, max_count):
		raise NotImplementedError('get_items not implemented')

	def db_psh_sub_set(self, feed_id, uri):
		raise NotImplementedError('PubSubHubbub subscriptions not implemented')

	def db_psh_sub_remove(self, feed_id, uri):
		raise NotImplementedError('PubSubHubbub subscriptions not implemented')

	def db_xmpp_sub_set(self, feed_id, uri):
		raise NotImplementedError('XMPP subscriptions not implemented')

	def db_xmpp_sub_remove(self, feed_id, uri):
		raise NotImplementedError('XMPP subscriptions not implemented')

class EpcpPublisher(Publisher):
	def __init__(self, config, formatter=None):
		# TODO: parse config and create publisherset object
		self.pub = None
		self.formatter = formatter

	def psh_sub_set(self, feed_id, uri):
		# TODO
		pass

	def psh_sub_remove(self, feed_id, uri):
		# TODO
		pass

	def xmpp_sub_set(self, feed_id, jid):
		# TODO
		pass

	def xmpp_sub_remove(self, feed_id, jid):
		# TODO
		pass

	def publish(self, feed_id, item, cursor, prev_cursor):
		for format in ('atom', 'json'):
			self._publish(feed_id, item, format, cursor, prev_cursor)

	def _make_item(self, item, item_format, cursor, prev_cursor):
		hr_headers = dict()

		if item_format == 'atom':
			hr_headers['Content-Type'] = 'application/atom+xml'
			# TODO
			#hr_body =
			#hs_content =
			#hrq_body =
			#xs_content =
		elif item_format == 'json':
			if self.formatter:
				item_json = self.formatter.to_format(item, 'json')
			else:
				item_json = item # assume json ready
			hr_headers['Content-Type'] = 'application/json'
			hr_body = json.dumps([item_json])
			# TODO
			#hs_content =
			#hrq_body =
			#xs_content =

		pub_formats = list()
		pub_formats.append(gripcontrol.HttpResponseFormat(headers=hr_headers, body=hr_body))
		pub_formats.append(gripcontrol.HttpStreamFormat(hs_content))

		return pubcontrol.Item(pub_formats, cursor, prev_cursor)

	def _publish(self, feed_id, item, format, cursor, prev_cursor):
		self.pub.publish_async(pub_prefix + encode_id_part(feed_id) + '-' + encode_id_part(format), self._make_item(item, format, cursor, prev_cursor))

class RedisQueueModel(Model):
	def __init__(self, host=None, port=None, db=None, prefix=None, publisher=None):
		super(RedisQueueModel, self).__init__(publisher)
		self.prefix = prefix
		self.redis = redis.Redis(host=host, port=port, db=db)

	def get_items(self, feed_id, since_spec, until_spec, max_count):
		# TODO
		# read items, return as ItemsResult
		pass

	def append(self, feed_id, item):
		# TODO
		# save item
		# self.notify(feed_id, item, cursor, prev_cursor)
		pass

class ZrpcModel(Model):
	pass

def encode_id_part(s):
	out = ''
	for c in s:
		if c in '\\-_':
			out += '\\x%02x' % ord(c)
		else:
			out += c
	return out

def parse_spec(spec):
	at = spec.find(':')
	if at < 1: # index 0 or not found
		raise ValueError('missing type')
	return PositionSpec(since[:at], since[at + 1:])

def get_accept_format(accept_header):
	accept_types = accept_header.split(',')
	if 'application/atom+xml' in accept_types:
		return 'atom'
	elif 'application/json' in accept_types:
		return 'json'
	else:
		raise ValueError('no supported accept value')

# return (content type, body)
def create_items_body(format, items, total=None, prev_cursor=None, last_cursor=None):
	if format == 'atom':
		# TODO
		raise NotImplementedError()
	elif format == 'json':
		out = dict()
		out['items'] = items
		if total is not None:
			out['total'] = total
		if prev_cursor is not None:
			out['prev_cursor'] = prev_cursor
		if last_cursor is not None:
			out['last_cursor'] = last_cursor
		return ('application/json', json.dumps(out) + '\n')
	else:
		raise ValueError('Unsupported format: %s' % format)
