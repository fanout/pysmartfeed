import sys
import json
import smartfeed.django

base = sys.argv[1]
command = sys.argv[2]

db = smartfeed.django.get_default_model()

if command == 'add':
	data = json.loads(sys.argv[3])
	id = sys.argv[4] if len(sys.argv) >= 5 else None
	db.add(base, data, id=id)
elif command == 'del':
	id = sys.argv[3]
	db.delete(base, id)
elif command == 'exp':
	ttl = int(sys.argv[3])
	db.clear_expired(base, ttl)
elif command == 'expany':
	ttl = int(sys.argv[3])
	db.clear_expired(base, ttl, deleted=False)
else:
	raise ValueError('unsupported command')
