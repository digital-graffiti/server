import time
from uuid import uuid4

def object_to_doc(object, id_proof, owner_id):
    # Separate out the contexts
    if '_contexts' in object:
        contexts = object['_contexts']
        del object['_contexts']
    else:
        contexts = []

    # Extract the ID and combine into one big doc
    doc = {
        "_owner_id": owner_id,
        "_object": [object],
        "_contexts": contexts,
        "_tombstone": False,
        "_id_proof": id_proof
    }

    return doc

def doc_to_object(doc):
    object = doc['_object'][0]
    object['_contexts'] = doc['_contexts']
    return object

def query_rewrite(query):
    return {
        # The object must match the query
        "_object": { "$elemMatch": query },
        "$or": [
            # Either there are no contexts
            { "_contexts": { "$size": 0 } },
            # Or the object must match at least one of the contexts
            { "_contexts": { "$elemMatch": {
                # None of the near misses can match the query
                "_nearMisses": {
                    "$not": { "$elemMatch": query }
                },
                # All of the neighbors must match the query
                "_neighbors": {
                    "$not": {
                        # Which is the negation of:
                        # "some neighbor does not match the query"
                        "$elemMatch": { "$nor": [ query ] }
                    }
                }
            }}}
        ]
    }
