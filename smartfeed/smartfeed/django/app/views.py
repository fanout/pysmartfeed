from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseNotAllowed
import gripcontrol
import smartfeed

def items(req, feed_id):
	if req.method == 'GET':
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
				return HttpResponseBadRequest('Bad Request: Invalid since value: %s\n')

		until = req.GET.get('until')
		if until:
			try:
				until = smartfeed.parse_spec(until)
			except ValueError as e:
				return HttpResponseBadRequest('Bad Request: Invalid until value: %s\n')

		format = 'json'
		accept = req.META.get('HTTP_ACCEPT')
		if accept:
			try:
				format = smartfeed.get_accept_format(accept)
			except:
				pass

		try:
			result = smartfeed.django.get_model().get_items(feed_id, since, until, max_count)
		except smartfeed.FeedDoesNotExist:
			return HttpResponseNotFound('Not Found: No such feed\n')
		except smartfeed.ItemDoesNotExist as e:
			return HttpResponseNotFound('Not Found: %s\n' % e.message)

		if not since or len(result.items) > 0:
			content_type, body = smartfeed.create_items_body(format, result.items, total=result.total, last_cursor=result.last_cursor)
			return HttpResponse(body, content_type=content_type)

		if not smartfeed.django.check_grip_sig(req):
			return HttpResponse('Error: Realtime endpoint not supported. Set up Pushpin or Fanout.io\n', status=501)

		channel = gripcontrol.Channel(smartfeed.django.get_grip_prefix() + smartfeed.encode_id_part(feed_id) + '-' + smartfeed.encode_id_part(format), result.last_cursor)
		theaders = dict()
		content_type, tbody = smartfeed.create_items_body(format, [], last_cursor=result.last_cursor)
		theaders['Content-Type'] = content_type
		tresponse = gripcontrol.Response(headers=theaders, body=tbody)
		instruct = gripcontrol.create_hold_response(channel, tresponse)
		return HttpResponse(instruct, content_type='application/grip-instruct')
	else:
		return HttpResponseNotAllowed(['GET'])

def subscriptions(req, feed_id):
	# TODO
	return HttpResponse('Not Implemented\n', status=501)
