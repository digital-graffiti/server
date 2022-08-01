import json
import asyncio
from hashlib import sha256
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager

from .rewrite import query_rewrite, object_to_doc

class Rest:

    def __init__(self, db, redis):
        self.db = db
        self.redis = redis

    async def update(self, object, query, owner_id):
        self.validate_owner_id(owner_id)

        # Lock so that the delete and insert can be done together
        lock = self.redis.lock(object['_id'] + owner_id)
        await lock.acquire()

        # Try deleting the old document if there is one
        delete_id = None
        try:
            delete_id = await self.delete(object['_id'], owner_id)
        except Exception as e:
            # Nothing to worry about, this is just a new object
            pass

        result = None
        try:
            # Make a new document out of the object
            doc = object_to_doc(object)

            # Then insert the new one into the database
            result = await self.db.insert_one(doc)

            # Once inserted, try querying for it
            # with the supplied query
            query = query_rewrite(query)
            query["_id"] = result.inserted_id
            refetched_doc = await self.db.find_one(query)
            if not refetched_doc:
                raise Exception("the updated object does not match the supplied query")

        except Exception as e:

            # Delete the object if it was inserted
            if result:
                await self.db.delete_one({ "_id": result.inserted_id })

            # Un-delete the original object if it exists
            if delete_id:
                result = await self.db.find_one_and_update({
                    "_id": delete_id
                }, {
                    "$set": { "_tombstone": False }
                })

            # Propagate the exception up
            raise e

        finally:
            await lock.release()

        # Send the change to the broker
        if delete_id:
            await self.redis.publish("replaces", json.dumps(
                (str(delete_id), str(result.inserted_id))
            ))
        else:
            await self.redis.publish("inserts", str(result.inserted_id))

    async def remove(self, object_id, owner_id):
        self.validate_owner_id(owner_id)

        lock = self.redis.lock(object_id + owner_id)
        await lock.acquire()

        # Delete the object
        try:
            delete_id = await self.delete(object_id, owner_id)
        finally:
            await lock.release()

        # And publish the change to the broker
        await self.redis.publish("deletes", str(delete_id))

    async def delete(self, object_id, owner_id):
        # Check that the object that already exists
        # that it is owned by the owner_id,
        # and that it is not scheduled for deletion
        # If so, schedule it for deletion
        doc = await self.db.find_one_and_update({
            "_externalID": object_id,
            "_object._by": owner_id,
            "_tombstone": False
        }, {
            "$set": { "_tombstone": True }
        })

        if not doc:
            raise Exception("""\
the object you're trying to modify either \
doesn't exist or you don't have permission \
to modify it.""")

        return doc['_id']

    def validate_owner_id(self, owner_id):
        if not owner_id:
            raise Exception("you can't modify objects without logging in.")
