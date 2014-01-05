import copy
from datetime import datetime
import calendar
import json
import uuid
from binascii import crc32
import redis
import pubcontrol
import gripcontrol

def check_grip_sig(grip_sig_header, config):
	for entry in config:
		if 'key' not in entry:
			continue
		if gripcontrol.validate_sig(grip_sig_header, entry['key']):
			return True
	return False

def encode_id_part(s):
	out = ''
	for c in s:
		if c in '\\-_':
			out += '\\x%02x' % ord(c)
		else:
			out += c
	return out

def decode_id_part(s):
	out = ''
	n = 0
	while n < len(s):
		if s[n] == '\\':
			if n + 3 >= len(s) or s[n + 1] != 'x':
				raise ValueError('bad format of encoded id')
			out += chr(int(s[n + 2:n + 4], 16))
			n += 3
		else:
			out += s[n]
		n += 1
	return out

def parse_spec(spec):
	at = spec.find(':')
	if at < 1: # index 0 or not found
		raise ValueError('missing type')
	return PositionSpec(spec[:at], spec[at + 1:])

def get_accept_format(accept_header):
	accept_types = accept_header.split(',')
	if 'application/atom+xml' in accept_types:
		return 'atom'
	elif 'application/json' in accept_types:
		return 'json'
	else:
		raise ValueError('no supported accept value')

# return (content type, body)
def create_items_body(bformat, items, total=None, prev_cursor=None, last_cursor=None, formatter=None):
	if bformat == 'atom':
		# TODO: atom format
		raise NotImplementedError()
	elif bformat == 'json':
		out = dict()
		out_items = list()
		for i in items:
			if formatter:
				out_items.append(formatter.to_format(i, bformat))
			else:
				out_items.append(i) # assume json ready
		out['items'] = out_items
		if total is not None:
			out['total'] = total
		if prev_cursor is not None:
			out['prev_cursor'] = prev_cursor
		if last_cursor is not None:
			out['last_cursor'] = last_cursor
		return ('application/json', json.dumps(out, indent=4) + '\n')
	else:
		raise ValueError('Unsupported format: %s' % bformat)

def calc_toc_checksum(item_ids):
	ids = list()
	for i in item_ids:
		if isinstance(i, unicode):
			i = i.encode('utf-8')
		ids.append(i)
	return str(crc32('_'.join(ids)) & 0xffffffff)

def make_toc_cursor(timestamp, offset, item_ids):
	return str(timestamp) + '_' + str(offset) + '_' + calc_toc_checksum(item_ids)

class UnsupportedSpecError(Exception):
	pass

class InvalidSpecError(Exception):
	pass

class SpecMismatchError(Exception):
	pass

class FeedDoesNotExist(Exception):
	pass

class ItemDoesNotExist(Exception):
	pass

class PositionSpec(object):
	def __init__(self, type, value):
		self.type = type
		self.value = value

class ItemsResult(object):
	def __init__(self):
		self.items = list()
		self.total = None
		self.last_cursor = None

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

			pub = pubcontrol.PubControl(entry['control_uri'])
			if 'control_iss' in entry:
				pub.set_auth_jwt({'iss': entry['control_iss']}, entry['key'])

			self.pubs.append(pub)

	def publish(self, channel, item):
		for pub in self.pubs:
			pub.publish_async(channel, item)

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

	# total may be None
	def publish(self, feed_id, item, total, cursor, prev_cursor):
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
		self.db_xmpp_sub_set(feed_id, jid)
		self.publisher.xmpp_sub_set(feed_id, jid)

	def xmpp_sub_remove(self, feed_id, jid):
		self.db_xmpp_sub_remove(feed_id, jid)
		self.publisher.xmpp_sub_remove(feed_id, jid)

	def notify(self, feed_id, item, total, cursor, prev_cursor):
		self.publisher.publish(feed_id, item, total, cursor, prev_cursor)

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
	def __init__(self, pub_control_set, prefix=None, formatter=None):
		self.pub = pub_control_set
		self.prefix = prefix
		if self.prefix is None:
			self.prefix = ''
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

	def publish(self, feed_id, item, total, cursor, prev_cursor):
		for iformat in ('atom', 'json'):
			if (self.formatter and self.formatter.is_supported(iformat)) or (not self.formatter and iformat == 'json'):
				self._publish(feed_id, item, iformat, total, cursor, prev_cursor)

	def _make_item(self, item, item_format, total, cursor, prev_cursor):
		hr_headers = dict()

		if item_format == 'atom':
			hr_headers['Content-Type'] = 'application/atom+xml'
			# TODO: atom format
			#hr_body =
			#hs_content =
			#hrq_body =
			#xs_content =
		elif item_format == 'json':
			content_type, hr_body = create_items_body(item_format, [item], total=total, prev_cursor=prev_cursor, last_cursor=cursor, formatter=self.formatter)
			hr_headers['Content-Type'] = content_type
			# TODO: other epcp formats
			#hs_content =
			#hrq_body =
			#xs_content =

		pub_formats = list()
		pub_formats.append(gripcontrol.HttpResponseFormat(headers=hr_headers, body=hr_body))
		#pub_formats.append(gripcontrol.HttpStreamFormat(hs_content))

		return pubcontrol.Item(pub_formats, cursor, prev_cursor)

	def _publish(self, feed_id, item, iformat, total, cursor, prev_cursor):
		self.pub.publish(self.prefix + encode_id_part(feed_id) + '-' + encode_id_part(iformat), self._make_item(item, iformat, total, cursor, prev_cursor))

class Item(object):
	def __init__(self):
		self.id = None
		self.created = None
		self.modified = None
		self.deleted = False
		self.data = None

class DefaultFormatter(Formatter):
	def is_supported(self, format):
		return (format == 'json')

	def to_format(self, item, format):
		if item.deleted:
			out = dict()
		else:
			if isinstance(item.data, dict):
				out = copy.deepcopy(item.data)
			else:
				out = dict()
				out['value'] = copy.deepcopy(item.data)
		out['id'] = item.id
		out['created'] = item.created.isoformat()
		out['modified'] = item.modified.isoformat()
		if item.deleted:
			out['deleted'] = True
		return out

class RedisModel(Model):
	def __init__(self, host=None, port=None, db=None, prefix=None, ttl=None, publisher=None):
		super(RedisModel, self).__init__(publisher)
		self.prefix = prefix
		if not self.prefix:
			self.prefix = ''
		self.redis = redis.Redis(host=host, port=port, db=db)
		self.ttl = ttl
		if not self.ttl:
			self.ttl = 1000 * 60 * 2

	# return (timestamp, offset, checksum)
	def _get_spec_parts(self, redis, key_index, spec):
		if spec.type == 'id':
			return (int(redis.zscore(key_index, spec.value)), None, None)
		elif spec.type == 'time':
			return (calendar.timegm(datetime.strptime(spec.value, '%Y-%m-%dT%H:%M:%S').utctimetuple()), None, None)
		else: # cursor
			if not spec.value:
				return (0, None, None)
			try:
				ts, offset, cs = spec.value.split('_')
				ts = int(ts)
				offset = int(offset)
			except:
				raise ValueError('bad cursor format')
			return (ts, offset, cs)

	def _item_serialize(self, item):
		out = dict()
		out['data'] = item.data
		meta = dict()
		meta['id'] = item.id
		meta['created'] = calendar.timegm(item.created.utctimetuple())
		meta['modified'] = calendar.timegm(item.modified.utctimetuple())
		if item.deleted:
			meta['deleted'] = True
		out['meta'] = meta
		return json.dumps(out)

	def _item_deserialize(self, data):
		data = json.loads(data)
		item = Item()
		item.data = data['data']
		meta = data['meta']
		item.id = meta['id']
		item.created = datetime.utcfromtimestamp(meta['created'])
		item.modified = datetime.utcfromtimestamp(meta['modified'])
		if meta.get('deleted'):
			item.deleted = True
		return item

	def _ref_find(self, refs, id, score):
		for n, i in enumerate(refs):
			if i[0] == id and i[1] == score:
				return n
		return -1

	def _ref_rfind(self, refs, id, score):
		for n, i in enumerate(reversed(refs)):
			if i[0] == id and i[1] == score:
				return len(refs) - n - 1
		return -1

	def _ref_rfind_first_score(self, refs, score):
		found = False
		for n, i in enumerate(reversed(refs)):
			if i[1] == score:
				found = True
			elif found:
				return len(refs) - n
		if found:
			return 0
		return -1

	def _get_ids(self, refs):
		out = list()
		for i in refs:
			out.append(i[0])
		return out

	def get_items(self, feed_id, since_spec, until_spec, max_count):
		parts = feed_id.split('-')
		base = decode_id_part(parts[0])
		index = decode_id_part(parts[1])

		if since_spec and since_spec.type not in ('id', 'time', 'cursor'):
			raise UnsupportedSpecError('Position spec not supported: %s' % since_spec.type)

		if until_spec and until_spec.type not in ('id', 'time', 'cursor'):
			raise UnsupportedSpecError('Position spec not supported: %s' % until_spec.type)

		enc_base = encode_id_part(base)
		key_items = '%s%s-items' % (self.prefix, enc_base)
		key_index = '%s%s-index-%s' % (self.prefix, enc_base, index)
		while True:
			with self.redis.pipeline() as pipe:
				try:
					pipe.watch(key_items)
					pipe.watch(key_index)

					try:
						if since_spec:
							since_ts, since_offset, since_cs = self._get_spec_parts(pipe, key_index, since_spec)
						if until_spec:
							until_ts, until_offset, until_cs = self._get_spec_parts(pipe, key_index, until_spec)
					except:
						raise InvalidSpecError()

					# this is a loop so we can fallback from cursor to time
					retry = False
					while True:
						smin = since_ts if since_spec else '-inf'
						smax = until_ts if until_spec else '+inf'

						refs = pipe.zrangebyscore(key_index, smin, smax, start=0, num=max_count, withscores=True)

						tmp = list()
						for ref in refs:
							tmp.append((ref[0], int(ref[1])))
						refs = tmp
						del tmp

						start = 0
						end = len(refs)

						if since_spec:
							if since_spec.type == 'id':
								# trim
								at = self._ref_find(refs, since_spec.value, since_ts)
								if at == -1:
									retry = True
									break
								start = at + 1
							elif since_spec.type == 'cursor':
								if len(refs) > 0 and refs[0][1] == since_ts:
									# ensure integrity
									if calc_toc_checksum(self._get_ids(refs[0:since_offset + 1])) != since_cs:
										# fallback to a time query
										since_spec.type = 'time'
										since_offset = None
										since_cs = None
										continue
									# trim
									start = since_offset + 1

						if until_spec:
							if until_spec.type == 'id':
								# trim
								at = self._ref_rfind(refs, until_spec.value, until_ts)
								if at == -1:
									retry = True
									break
								end = at
							elif until_spec.type == 'cursor':
								if len(refs) > 0 and refs[-1][1] == until_ts:
									# ensure integrity
									at = self._ref_rfind_first_score(refs, until_ts)
									assert(at != -1)
									if calc_toc_checksum(self._get_ids(refs[at:at + until_offset + 1])) != until_cs:
										# fallback to a time query
										until_spec.type = 'time'
										until_offset = None
										until_cs = None
										continue
									# trim
									end = at + until_offset

						# query succeeded, break out
						break
					if retry:
						continue

					if end - start <= 0:
						out = ItemsResult()
						if since_spec:
							if since_spec.type == 'id':
								# if we got this far on an id spec, then the original item is just previous
								assert(start > 0)
								out.last_cursor = make_toc_cursor(since_ts, start - 1, self._get_ids(refs[:start]))
							elif since_spec.type == 'time':
								if since_ts > 0:
									# search for the first item before this time
									refs = pipe.zrevrangebyscore(key_index, since_ts - 1, '-inf', start=0, num=1, withscores=True)
									if refs:
										# now fetch all items within this timestamp and return a cursor for the last one
										ts = refs[0][1]
										item_ids = pipe.zrangebyscore(key_index, ts, ts)
										if not refs:
											# inconsistent, retry
											continue
										out.last_cursor = make_toc_cursor(ts, len(item_ids) - 1, item_ids)
									else:
										out.last_cursor = ''
								else:
									out.last_cursor = ''
							else: # cursor
								# just echo back the input. note that in a cursor->time fallback, this value
								#   will still contain the original cursor value
								out.last_cursor = since_spec.value
						else:
							out.last_cursor = ''
						return out

					pipe.multi()
					for n in range(start, end):
						pipe.hget(key_items, refs[n][0])
					ret = pipe.execute()

					out = ItemsResult()
					for data_raw in ret:
						if not data_raw:
							# item went missing. restart operation
							retry = True
							break
						item = self._item_deserialize(data_raw)
						out.items.append(item)
					if retry:
						continue

					at = self._ref_rfind_first_score(refs, refs[end - 1][1])
					assert(at != -1)
					out.last_cursor = make_toc_cursor(refs[at][1], end - at - 1, self._get_ids(refs[at:end]))
					return out
				except redis.WatchError:
					continue

	# insert/update and return item
	def add(self, base, data, id=None, notify=True):
		enc_base = encode_id_part(base)
		key_items = '%s%s-items' % (self.prefix, enc_base)
		key_index_created = '%s%s-index-created' % (self.prefix, enc_base)
		key_index_modified = '%s%s-index-modified' % (self.prefix, enc_base)
		key_lastpub_created = '%s%s-lastpub-created' % (self.prefix, enc_base)
		key_lastpub_modified = '%s%s-lastpub-modified' % (self.prefix, enc_base)
		while True:
			with self.redis.pipeline() as pipe:
				try:
					pipe.watch(key_items)
					pipe.watch(key_index_created)
					pipe.watch(key_index_modified)
					pipe.watch(key_lastpub_created)
					pipe.watch(key_lastpub_modified)

					now = datetime.utcnow()

					# round to seconds
					now = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second)

					item = Item()
					is_new = False
					if id:
						item.id = id

						# look up existing item
						cur_item_raw = pipe.hget(key_items, id)
						if cur_item_raw:
							cur_item = self._item_deserialize(cur_item_raw)
							item.created = cur_item.created
							item.modified = cur_item.modified
							item.deleted = cur_item.deleted
						else:
							is_new = True
					else:
						while True:
							new_id = str(uuid.uuid4())
							if not pipe.hexists(key_items, new_id):
								break
						item.id = new_id
						is_new = True

					if is_new:
						item.created = now
						notify_created = True
					else:
						notify_created = False

					notify_modified = True
					item.modified = now

					item.data = data

					if notify:
						lastpub_created = pipe.get(key_lastpub_created)
						lastpub_modified = pipe.get(key_lastpub_modified)

					ts_created = calendar.timegm(item.created.utctimetuple())
					ts_modified = calendar.timegm(item.modified.utctimetuple())

					# save and retrieve position info in one shot
					pipe.multi()
					pipe.hset(key_items, item.id, self._item_serialize(item))
					pipe.zadd(key_index_created, item.id, ts_created)
					pipe.zadd(key_index_modified, item.id, ts_modified)
					pipe.zrangebyscore(key_index_created, ts_created, ts_created)
					pipe.zrangebyscore(key_index_modified, ts_modified, ts_modified)
					ret = pipe.execute()
					items_created = ret[3]
					items_modified = ret[4]
					break
				except redis.WatchError:
					continue

		if notify:
			created_offset = items_created.index(item.id)
			modified_offset = items_modified.index(item.id)
			lastcursor_created = make_toc_cursor(ts_created, created_offset, items_created[0:created_offset + 1])
			lastcursor_modified = make_toc_cursor(ts_modified, modified_offset, items_modified[0:modified_offset + 1])

			# FIXME: race condition. another write could set this before we do
			self.redis.set(key_lastpub_created, lastcursor_created)
			self.redis.set(key_lastpub_modified, lastcursor_modified)

			if notify_created:
				self.notify(enc_base + '-created', item, None, lastcursor_created, lastpub_created)
			if notify_modified:
				self.notify(enc_base + '-modified', item, None, lastcursor_modified, lastpub_modified)

		return item

	def delete(self, base, id, notify=True):
		enc_base = encode_id_part(base)
		key_items = '%s%s-items' % (self.prefix, enc_base)
		key_index_modified = '%s%s-index-modified' % (self.prefix, enc_base)
		key_index_deleted = '%s%s-index-deleted' % (self.prefix, enc_base)
		key_lastpub_modified = '%s%s-lastpub-modified' % (self.prefix, enc_base)
		while True:
			with self.redis.pipeline() as pipe:
				try:
					pipe.watch(key_items)
					pipe.watch(key_index_modified)
					pipe.watch(key_index_deleted)
					pipe.watch(key_lastpub_modified)

					now = datetime.utcnow()

					# round to seconds
					now = datetime(now.year, now.month, now.day, now.hour, now.minute, now.second)

					item_raw = pipe.hget(key_items, id)
					if not item_raw:
						raise ItemDoesNotExist()

					item = self._item_deserialize(item_raw)

					if item.deleted:
						raise ItemDoesNotExist()

					item.deleted = True
					item.modified = now

					if notify:
						lastpub_modified = pipe.get(key_lastpub_modified)

					ts_modified = calendar.timegm(item.modified.utctimetuple())

					# save and retrieve position info in one shot
					pipe.multi()
					pipe.hset(key_items, item.id, self._item_serialize(item))
					pipe.zadd(key_index_modified, item.id, ts_modified)
					pipe.zadd(key_index_deleted, item.id, ts_modified)
					pipe.zrangebyscore(key_index_modified, ts_modified, ts_modified)
					ret = pipe.execute()
					items_modified = ret[3]
					break
				except redis.WatchError:
					continue

		if notify:
			modified_offset = items_modified.index(item.id)
			lastcursor_modified = make_toc_cursor(ts_modified, modified_offset, items_modified[0:modified_offset + 1])

			# FIXME: race condition. another write could set this before we do
			self.redis.set(key_lastpub_modified, lastcursor_modified)

			self.notify(enc_base + '-modified', item, None, lastcursor_modified, lastpub_modified)

	# ttl is in seconds
	# return total cleared
	def clear_expired(self, base, ttl, deleted=True):
		ts_exp = calendar.timegm(datetime.utcnow().utctimetuple()) - ttl - 1
		enc_base = encode_id_part(base)
		key_items = '%s%s-items' % (self.prefix, enc_base)
		key_index_created = '%s%s-index-created' % (self.prefix, enc_base)
		key_index_modified = '%s%s-index-modified' % (self.prefix, enc_base)
		key_index_deleted = '%s%s-index-deleted' % (self.prefix, enc_base)
		total = 0
		while True:
			with self.redis.pipeline() as pipe:
				try:
					pipe.watch(key_items)
					pipe.watch(key_index_created)
					pipe.watch(key_index_modified)
					pipe.watch(key_index_deleted)

					if deleted:
						key_index = key_index_deleted
					else:
						key_index = key_index_modified

					items = pipe.zrangebyscore(key_index, '-inf', ts_exp)
					if not items:
						break

					item_id = items[0]

					pipe.multi()
					pipe.hdel(key_items, item_id)
					pipe.zrem(key_index_created, item_id)
					pipe.zrem(key_index_modified, item_id)
					pipe.zrem(key_index_deleted, item_id)
					pipe.execute()

					total += 1

					# note: don't break on success
				except redis.WatchError:
					continue
		return total

class ZrpcModel(Model):
	# TODO
	pass
