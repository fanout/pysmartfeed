PySmartFeed
===========
Date: January 5th, 2014

Author: Justin Karneges <justin@fanout.io>

Mailing List: http://lists.fanout.io/listinfo.cgi/fanout-users-fanout.io

PySmartFeed is a Python library for implementing Smart Feeds, a protocol that simplifies synchronization of item lists in realtime. Smart Feeds are very similar to RSS/Atom feeds, with support for multiple transport protocols (HTTP and XMPP) as well as a variety of mechanisms for receiving updates (HTTP long-polling, PubSubHubbub, XMPP). For more information about Smart Feeds, see the spec: https://fanout.io/docs/smartfeeds.html

This library contains abstract classes for handling queries and publishing updates of item data in any format. It includes a Redis-based model implementation that may suit many kinds of applications as well as a Django app.

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

Quickstart
----------

The easiest way to get started is to use the built-in Django App and Redis model. Create a Django project, and make the following changes in your settings.py:

  * Append `smartfeed.django.app` to `INSTALLED_APPS`.
  * Set `SMARTFEED_MODEL_CLASS` to `smartfeed.django.RedisModel`.

Next, edit urls.py to map feeds to the app. For example:

```python
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    ...
    url(r'^myfeed/', include('smartfeed.django.app.urls'), {'base': 'myfeed'}),
    ...
)
```

You can then run the Django project and start hitting the HTTP endpoints. E.g.:

```
curl http://localhost:8000/myfeed/items/
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

Note that you'll need to run the above code within a Django context.

Now let's query for items again:

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

You can see the item has been added. This demonstrates basic appending and retrieval of items.

Models, Feeds, URLs
-------------------

At the core of the library is the `Model` class, which handles queries for items as well as publish-subscribe management for change notifications. Feeds are facets to a model, and it is not uncommon for a single data source to have multiple feed representations. For example, a newsfeed application might store news items in a database, and expose the news items as a feed ordered by created time (for display purposes) as well as a feed ordered by modified time (for synchronization). These are considered separate feeds even though they refer to the same underlying data. Finally, URLs map to feeds.

The `Model` interface operates at the feed level, not the data source level. If a data source exposes multiple feeds, then a convention must be established between the model implementation and the user of the model in order to communicate the proper data source and feed. The `RedisModel` class stores lists of items, and each list is exposed over multiple feeds using different orderings. It uses a feed naming convention of {base}-{order}, where {base} is the name of a list, and {order} is the ordering to view. The `DefaultMapper` class understands this convention when handling incoming HTTP requests, pairing the `base` value set in the urls.py routing table with the `order` parameter in the query string. Thus, a request against `/myfeed/items/?order=modified` would mean to access a feed named "myfeed-modified". You are free to use this convention yourself, or not at all. It is entirely up to the model and mapper to agree on.

While this library includes a convenient model for Redis, it has been designed so that a model implementation could be backed by any kind of database, including SQL.

Position Specs
--------------

It's up to the model implementation to support whatever position specs it needs. The `RedisModel` class supports the ones defined in the Smart Feeds specification, namely `id`, `time`, and `cursor`. This allows fetching ranges of items bounded by item ids, ISO timestamps, or opaque cursor values.

For example, a query for all items with created time equal to or later than January 6th, 2014 at noon could look like this:

```
curl http://localhost:8000/myfeed/items/?since=time:2014-01-06T12:00:00
```

Realtime
--------

Models are able to publish notifications when their data changes. The model class must be set up with an appropriate `Publisher` for this. By default, `EpcpPublisher` is used, which knows how to publish data through Pushpin and Fanout.io.

For example, you could set up Pushpin on your machine and configure it to forward to your Django project. Then, set `GRIP_PROXIES` appropriately in settings.py:

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

Any requests to the feeds that pass through Pushpin would then become realtime capable, enabling HTTP long-polling and HTTP streaming delivery.

Assuming Pushpin is listening on 7999 and forwarding to the Django app, let's try testing realtime. Query for items as described earlier:

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

Formatters
----------

When items are retrieved or published, they must be exported in a format suitable for the receiver. The `DefaultFormatter` class supports JSON formatting of smartfeed.Item objects containing JSON-ready data, munging it with associated metadata such as the item id and timestamps. For reference, here is its code:

```python
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
```

Alternatively, you can create your own formatters that understand different formats (such as Atom) or process more complex items.

Configuration
-------------

Here is a list of the various Django settings. Almost all are optional.

  * `REDIS_HOST` - The Redis host to use. Defaults to localhost.
  * `REDIS_PORT` - The Redis port to use. Defaults to 6379.
  * `REDIS_DB` - The Redis DB number to use. Defaults to 0.
  * `GRIP_PROXES` - List of GRIP proxies to use for client-initiated realtime push. If omitted, then long-polling/streaming will be disabled.
  * `SMARTFEED_MODEL_CLASS` - The default SmartFeed model class to use. Set this to `smartfeed.django.RedisModel`.
  * `SMARTFEED_MAPPER_CLASS` - The default mapper class to use. Defaults to `smartfeed.django.DefaultMapper`.
  * `SMARTFEED_FORMATTER_CLASS` - The default formatter class to use. Defaults to `smartfeed.DefaultFormatter`.
  * `SMARTFEED_PUBLISHER_CLASS` - The default publisher class to use. Defaults to `smartfeed.django.EpcpPublisher`.
  * `SMARTFEED_REDIS_PREFIX` - The prefix to use on keys with the Redis model. Defaults to "smartfeed-".
  * `SMARTFEED_GRIP_PREFIX` - The prefix to use on publish-subscribe channels with EpcpPublisher. Defaults to "smartfeed-".
