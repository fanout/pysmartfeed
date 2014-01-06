PySmartFeed
===========
Date: January 5th, 2014

Author: Justin Karneges <justin@fanout.io>

Mailing List: http://lists.fanout.io/listinfo.cgi/fanout-users-fanout.io

PySmartFeed is a Python library for implementing Smart Feeds, a protocol that simplifies synchronization of item lists in realtime. Smart Feeds are very similar to RSS/Atom feeds, with support for multiple transport protocols (HTTP and XMPP) as well as a variety of mechanisms for receiving updates (HTTP long-polling, PubSubHubbub, XMPP). For more information about Smart Feeds, see the spec: https://fanout.io/docs/smartfeeds.html

This library contains abstract classes for handling queries and publishing updates of item data in any format. It also includes a Redis-based model implementation that may suit many kinds of applications, as well as conveniences for Django projects such as configuration and an app with views.

License
-------

PySmartFeed is offered under the MIT license. See the COPYING file.

Requirements
------------

  * python django
  * redis
  * python gripcontrol
  * pushpin (or fanout.io)
  * a web server

Setup
-----

The easiest way to get started is to use the built-in Django App and Redis model. Create a Django project, and add `smartfeed.django.app` to `INSTALLED_APPS`. Then set some other things in settings.py:

  * `REDIS_HOST` - The Redis host to use. Defaults to localhost.
  * `REDIS_PORT` - The Redis port to use. Defaults to 6379.
  * `REDIS_DB` - The Redis DB number to use. Defaults to 0.
  * `GRIP_PROXES` - List of GRIP proxies to use for client-initiated realtime push. If omitted, then long-polling/streaming will be disabled.
  * `SMARTFEED_MODEL_CLASS` - The default SmartFeed model class to use. Set this to `smartfeed.django.RedisModel`.

Please note you must at least set `SMARTFEED_MODEL_CLASS` for anything to work.

For `GRIP_PROXES`, you can install Pushpin and set something like this:

```python
# pushpin and/or fanout.io is used for sending realtime data to clients
GRIP_PROXIES = [
    # pushpin
    {
        'key': 'changeme',
        'control_uri': 'http://localhost:5561'
    }
    # fanout.io
    #{
    #    'key': b64decode('your-realm-key'),
    #    'control_uri': 'http://api.fanout.io/realm/your-realm',
    #    'control_iss': 'your-realm'
    #}
]
```

If Pushpin is used, you'll want to ensure it is set to route to the Django app. From this point on, we'll assume Pushpin is running on port 7999 and forwarding to the app.

Next, edit urls.py to map feeds to the app. For example:

```python
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    ...
    url(r'^myfeed/', include('smartfeed.django.app.urls'), {'base': 'myfeed'}),
    ...
)
```

The above configuration maps the `/myfeed/` path to a base feed id "myfeed". The default mapping behavior (which can be overridden if you choose) understands two feeds: items sorted by created time ascending and items sorted by modified time ascending. These feed ids are created by concatenated the base id with the type of ordering. For example, in this case, the id of our feed that represents our data in modified time ascending order is "myfeed-modified". The `RedisModel` class understands these id formats in order to expose a single model via multiple feeds. The Smart Feed URL paths are `/myfeed/items/` and `/myfeed/items/?order=modified`.

You can then run the Django project and start hitting the HTTP endpoints. E.g.:

```
curl http://localhost:7999/myfeed/items/
```

Returns:

```json
{
    "items": [], 
    "last_cursor": ""
}
```

No items yet. Let's add an item:

```python
import smartfeed.django
model = smartfeed.django.get_default_model()
model.add('myfeed', 'hello')
```

Note that you'll need to run the above within a Django context. Now let's query for items again:

```json
{
    "items": [
        {
            "modified": "2014-01-06T10:18:47", 
            "id": "c859e306-38fb-49bb-b3c4-44ef02b6e7c5", 
            "value": "hello", 
            "created": "2014-01-06T10:18:47"
        }
    ], 
    "last_cursor": "1389003527_0_3678689003"
}
```

The `last_cursor` is the Smart Feed magic stuff. You can query for any items in the feed after this one by supplying this opaque cursor value in a follow-up request:

```
curl http://localhost:7999/myfeed/items/?since=cursor:1389003527_0_3678689003
```

Since there are no items after this one yet, the request will hang open as an HTTP long-poll. If we then add another item to the model again, it will be immediately pushed to the client:

```json
{
    "items": [
        {
            "modified": "2014-01-06T10:26:39", 
            "id": "00a8cc44-a1e8-4c21-9071-267af1d72179", 
            "value": "hello", 
            "created": "2014-01-06T10:26:39"
        }
    ], 
    "last_cursor": "1389003999_0_2040335985"
}
```

If you query for items from the start again, you can see that both items are present:

```
curl http://localhost:7999/myfeed/items/
```

Response:

```json
{
    "items": [
        {
            "modified": "2014-01-06T10:18:47", 
            "id": "c859e306-38fb-49bb-b3c4-44ef02b6e7c5", 
            "value": "hello", 
            "created": "2014-01-06T10:18:47"
        }, 
        {
            "modified": "2014-01-06T10:26:39", 
            "id": "00a8cc44-a1e8-4c21-9071-267af1d72179", 
            "value": "hello", 
            "created": "2014-01-06T10:26:39"
        }
    ], 
    "last_cursor": "1389003999_0_2040335985"
}
```

The way the items are formatted is completely customizable via a `Formatter` class. You can also override the `Mapper` to support alternative orderings or more advanced url->feed conversions.
