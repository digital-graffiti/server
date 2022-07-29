#!/usr/bin/env python3

import asyncio
from utils import *

async def main():

    my_id, my_token = owner_id_and_token()
    async with websocket_connect(my_token) as ws:
        for request in valid_requests(my_id):
            await send(ws, request)
            response = await recv(ws)
            while response["type"] in ["updates", "deletes"]:
                response = await recv(ws)
            if response["type"] == "error":
                assert response["reason"] != "validation"
        print("All valid requests passed, as expected")
        for request in invalid_requests(my_id):
            await send(ws, request)
            response = await recv(ws)
            while response["type"] in ["updates", "deletes"]:
                response = await recv(ws)
            assert response["type"] == "error"
            assert response["reason"] == "validation"
        print("All invalid requests failed, as expected")

def valid_requests(my_id):
    base_object = object_base(my_id)
    return [{
    "messageID": random_id(),
    "type": "update",
    "object": base_object,
}, {
    "messageID": "alkjd$$\~934820fk",
    "type": "update",
    "object": base_object,
}, {
    "messageID": "a"*64,
    "type": "delete",
    "objectID": base_object['_id']
}, {
    "messageID": "iueiruwoeiurowiwf1293  -e 👍",
    "type": "subscribe",
    "query": {},
    "since": None,
    "queryID": random_id()
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "query": {},
    "since": "666f6f2d6261722d71757578",
    "queryID": random_id()
}, {
    "messageID": random_id(),
    "type": "unsubscribe",
    "queryID": random_id()
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "foo": True
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "foo": None
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "foo": 123.4
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "foo": 1234
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": []
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": [ 'a' ],
            "_queryPassesWithout":  [ 'b' ]
        }]
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_to": [my_id, random_sha(), random_sha()],
        "foo": {
            "blah": False,
            "bar": {
                "asdf": [ 1234.14 ]
            }
        },
        "_inContextIf": [{
            "_queryFailsWithout": [
                "foo.blah",
                "foo.bar.asdf.0",
                [ 'adsf', '1234' ]
            ]
        }, {
            "_queryPassesWithout": [
                [ 'asdf.ieu', 'diufi.192384' ]
            ]
        }]
    }
}, {
    # Weird fields
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "~a": "b",
    }
}, {
    # To myself
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "_to": my_id 
    },
    "since": None,
    "queryID": random_id()
}, {
    # To myself nested
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "foo": {
            "_to": my_id
        }
    },
    "since": None,
    "queryID": random_id()
}, {
    # Weird fields
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "~a": "b",
    },
    "since": None,
    "queryID": random_id()
}, {
    # Valid args
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "x": { "$exists": True },
        "$and": [
            { "y": "a" },
            { "z": "b" }
        ]
    },
    "since": None,
    "queryID": random_id()
}, {
    # Valid args
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "x": { 
            "y": {
                "$gt": 100
            }
        },
        "q": { "$size": 100 },
        "asdf": { "$eq": "adsfhdkf" },
        "qwer": { "$in": [1, 2, "3", None] },
        "zxcv": { "$elemMatch": { "x": { "$ne": "asdf" } } },
        "wert": { "$type": "double" }
    },
    "since": None,
    "queryID": random_id()
}]

def invalid_requests(my_id):
    base_object = object_base(my_id)
    return [{}, # Empty
{
    # no message ID
    "type": "update",
    "object": base_object,
}, {
    # Invalid message type
    "messageID": random_id(),
    "type": "dupdate",
    "object": base_object,
}, {
    # Added extra field
    "messageID": random_id(),
    "type": "update",
    "object": base_object,
    "foo": "bar"
}, {
    "messageID": random_id(),
    "type": "delete",
    "objectID": base_object['_id'],
    "bloo": {}
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "query": {},
    "since": None,
    "queryID": random_id(),
    "bug": 1
}, {
    # Missing required field
    "messageID": random_id(),
    "type": "update",
}, {
    "messageID": random_id(),
    "type": "update",
    "object": {}
}, {
    "messageID": random_id(),
    "type": "update",
    "object": {
        '_to': base_object['_to'],
        '_by': base_object['_by'],
        '_inContextIf': base_object['_inContextIf']
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": {
        '_id': base_object['_id'],
        '_by': base_object['_by'],
        '_inContextIf': base_object['_inContextIf']
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": {
        '_id': base_object['_id'],
        '_to': base_object['_to'],
        '_inContextIf': base_object['_inContextIf']
    }
}, {
    "messageID": random_id(),
    "type": "update",
    "object": {
        '_id': base_object['_id'],
        '_to': base_object['_to'],
        '_by': base_object['_by'],
    }
}, {
    "messageID": random_id(),
    "type": "delete"
}, {
    "messageID": random_id(),
    "type": "subscribe"
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "query": {}
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "since": None
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "queryID": random_id()
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "query": {},
    "queryID": random_id()
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "since": None,
    "queryID": random_id()
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "query": {},
    "since": None
}, {
    "messageID": random_id(),
    "type": "unsubscribe"
}, {
    # only special fields can start with _
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_notright": 12345
    },
}, {
    # no fields can start with $
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "$something": 12345
    },
}, {
    # _id should be an string
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_id": 12345,
    }
}, {
    # _id should be < length 64
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_id": "z"*65
    }
}, {
    # messageID too long
    "messageID": "q"*65,
    "type": "update",
    "object": base_object
}, {
    # _to should be an array
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_to": random_sha()
    }
}, {
    # _to should by UUIDs
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_to": ["12345"]
    }
}, {
    # _to should always include my ID
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_to": [random_sha()]
    }
}, {
    # no repeated IDs
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_to": [my_id] + [random_sha()]*2
    }
}, {
    # by can only be my id
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_by": random_sha()
    }
}, {
    # _inContextIf is an array
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": {}
    }
}, {
    # _inContextIf only includes objects
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": ["asdf"]
    }
}, {
    # objects only have relevant fields
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "foo": [ '0' ]
        }]
    }
}, {
    # queryFailsWithout is an array
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": {}
        }]
    }
}, {
    # queryFailsWithout must include at least one element
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": []
        }]
    }
}, {
    # queryFailsWithout must include at least one element
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": ['asdf', []]
        }]
    }
}, {
    # queryFailsWithout must include at least one element
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": ['asdf', ['asdfdf']]
        }]
    }
}, {
    # nearmisses can only include strings
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": [ 1 ]
        }]
    }
}, {
    # contexts must be unique
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": [ 'asdf', 'asdf' ]
        }]
    }
}, {
    # contexts must be unique
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [{
            "_queryFailsWithout": [ [ 'asdf', 'qwer' ], [ 'asdf', 'qwer' ] ]
        }]
    }
}, {
    # contexts must be unique
    "messageID": random_id(),
    "type": "update",
    "object": base_object | {
        "_inContextIf": [
            { "_queryFailsWithout": [ 'asdf' ] },
            { "_queryFailsWithout": [ 'asdf' ] }
        ]
    }
}, {
    "messageID": random_id(),
    "type": "subscribe",
    "query": {},
    "since": "asdf",
    "queryID": random_id()
}, {
    # Invalid operators
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "$asdf": "wassup"
    },
    "since": None,
    "queryID": random_id()
}, {
    # Invalid operators nested
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "foo": {
            "$asdf": "wassup"
        }
    },
    "since": None,
    "queryID": random_id()
}, {
    # To is not sha
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "_to": "asdf"
    },
    "since": None,
    "queryID": random_id()
}, {
    # To is not sha
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "_to": { "x": "y" }
    },
    "since": None,
    "queryID": random_id()
}, {
    # To someone else
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "_to": random_sha()
    },
    "since": None,
    "queryID": random_id()
}, {
    # To someone else nested
    "messageID": random_id(),
    "type": "subscribe",
    "query": {
        "foo": {
            "_to": random_sha()
        }
    },
    "since": None,
    "queryID": random_id()
}]

if __name__ == "__main__":
    asyncio.run(main())
