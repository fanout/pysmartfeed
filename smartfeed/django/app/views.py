from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed
import gripcontrol
import smartfeed
import smartfeed.django

def items(req, **kwargs):
	if req.method == 'GET':
		mapper_class = kwargs.get('mapper_class')
		if mapper_class:
			mapper = smartfeed.django.get_class(mapper_class)
		else:
			mapper = smartfeed.django.get_default_mapper()

		model_class = kwargs.get('model_class')
		if not model_class:
			model_class = mapper.get_model_class(req, kwargs)
		if model_class:
			model = smartfeed.django.get_class(model_class)
		else:
			model = smartfeed.django.get_default_model()

		feed_id = mapper.get_feed_id(req, kwargs)

		max_count = req.GET.get('max')
		if max_count:
			try:
				max_count = int(max_count)
				if max_count < 1:
					raise ValueError('max too small')
			except ValueError as e:
				return HttpResponseBadRequest('Bad Request: Invalid max value: %s\n' % e.message)

		if not max_count or max_count > 50:
			max_count = 50

		since = req.GET.get('since')
		if since:
			try:
				since = smartfeed.parse_spec(since)
			except ValueError as e:
				return HttpResponseBadRequest('Bad Request: Invalid since value: %s\n' % e.message)

		until = req.GET.get('until')
		if until:
			try:
				until = smartfeed.parse_spec(until)
			except ValueError as e:
				return HttpResponseBadRequest('Bad Request: Invalid until value: %s\n' % e.message)

		wait = req.GET.get('wait')
		if wait is not None:
			if wait in ('true', 'false'):
				wait = (wait == 'true')
			else:
				return HttpResponseBadRequest('Bad Request: Invalid wait value\n')
		else:
			wait = False

		rformat = 'json'
		accept = req.META.get('HTTP_ACCEPT')
		if accept:
			try:
				rformat = smartfeed.get_accept_format(accept)
			except:
				pass

		try:
			result = model.get_items(feed_id, since, until, max_count)
		except NotImplementedError as e:
			return HttpResponse('Not Implemented: %s\n' % e.message, status=501)
		except smartfeed.UnsupportedSpecError as e:
			return HttpResponseBadRequest('Bad Request: %s' % e.message)
		except smartfeed.InvalidSpecError:
			return HttpResponseBadRequest('Bad Request: Invalid spec\n')
		except smartfeed.SpecMismatchError as e:
			return HttpResponseBadRequest('Bad Request: %s' % e.message)
		except smartfeed.FeedDoesNotExist as e:
			return HttpResponseNotFound('Not Found: %s\n' % e.message)
		except smartfeed.ItemDoesNotExist as e:
			return HttpResponseNotFound('Not Found: %s\n' % e.message)

		if not wait or result.last_cursor is None or not since or len(result.items) > 0:
			content_type, body = smartfeed.create_items_body(rformat, result.items, total=result.total, last_cursor=result.last_cursor, formatter=mapper.get_formatter(req, kwargs))
			return HttpResponse(body, content_type=content_type)

		if not smartfeed.django.check_grip_sig(req):
			return HttpResponse('Error: Realtime endpoint not supported. Set up Pushpin or Fanout.io\n', status=501)

		grip_prefix = mapper.get_grip_prefix(req, kwargs)

		channel = gripcontrol.Channel(grip_prefix + smartfeed.encode_id_part(feed_id) + '-' + smartfeed.encode_id_part(rformat), result.last_cursor)
		theaders = dict()
		content_type, tbody = smartfeed.create_items_body(rformat, [], last_cursor=result.last_cursor)
		theaders['Content-Type'] = content_type
		tresponse = gripcontrol.Response(headers=theaders, body=tbody)
		instruct = gripcontrol.create_hold_response(channel, tresponse)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])

def stream(req, **kwargs):
	if req.method == 'GET':
		mapper_class = kwargs.get('mapper_class')
		if mapper_class:
			mapper = smartfeed.django.get_class(mapper_class)
		else:
			mapper = smartfeed.django.get_default_mapper()

		feed_id = mapper.get_feed_id(req, kwargs)

		rformat = 'json'
		accept = req.META.get('HTTP_ACCEPT')
		if accept:
			try:
				rformat = smartfeed.get_accept_format(accept)
			except:
				pass

		if not smartfeed.django.check_grip_sig(req):
			return HttpResponse('Error: Realtime endpoint not supported. Set up Pushpin or Fanout.io\n', status=501)

		grip_prefix = mapper.get_grip_prefix(req, kwargs)

		channel = gripcontrol.Channel(grip_prefix + smartfeed.encode_id_part(feed_id) + '-' + smartfeed.encode_id_part(rformat))
		iheaders = dict()
		iheaders['Content-Type'] = 'text/plain'
		iresponse = gripcontrol.Response(headers=iheaders)
		instruct = gripcontrol.create_hold_stream(channel, iresponse)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])

def subscriptions(req, **kwargs):
	# TODO
	return HttpResponse('Not Implemented: %s\n' % 'Persistent subscriptions not implemented', status=501)
