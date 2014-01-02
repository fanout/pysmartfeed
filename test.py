import smartfeed

db = smartfeed.django.get_model()
db.append('myfeed', {'foo': 'bar'})
