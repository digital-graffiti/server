import asyncio
from .rewrite import query_rewrite

"""
Listens to changes in the database and
pushes those to appropriate sockets.
"""

class QueryBroker:

    def __init__(self, db):
        self.db = db
        self.query_lock = asyncio.Lock()
        self.queries = {}
        self.sockets = {}
        self.latest_time = 0

        asyncio.create_task(self.watch())

    async def watch(self):
        # Listen to all changes to the database
        watcher = self.db.watch(
                [{ "$match": {} }],
                full_document='updateLookup'
                )

        # For each new change to the database
        async with watcher as change_stream:
            async for change in change_stream:
                obj = change['fullDocument']['object'][0]

                # Freeze updates to the queries
                async with self.query_lock:

                    # Update the latest time seen
                    self.latest_time = max(self.latest_time, obj['created'])

                    # See if the changed object matches any of the open queries
                    await self.match_object_to_open_queries(obj['uuid'])

    async def match_object_to_open_queries(self, object_id):

        # For all open queries
        for socket_id in self.queries:
            for query_id in self.queries[socket_id]:

                # Check to see if the query matches
                # the document containing the changed object.
                try:
                    query = self.queries[socket_id][query_id]
                    # Only run the query on the object that is changing
                    query["object.uuid"] = object_id
                    doc = await self.db.find_one(query)
                except Exception as e:
                    # There's an error with the query!
                    await self.remove_queries(socket_id, [query_id], self.sockets[socket_id].user)
                    await self.sockets[socket_id].error(query_id, str(e))
                    continue

                # If there's a match, send it to the relevant socket
                if doc is not None:
                    await self.sockets[socket_id].match(query_id, doc)

    async def add_socket(self, socket):
        async with self.query_lock:
            self.sockets[socket.id] = socket
            self.queries[socket.id] = {}

    async def remove_socket(self, socket):
        async with self.query_lock:
            del self.sockets[socket.id]
            del self.queries[socket.id]

    async def add_queries(self, socket_id, queries, user):
        async with self.query_lock:
            self.validate_socket(socket_id, user)
            for query_id in queries:
                self.queries[socket_id][query_id] = query_rewrite(queries[query_id], user)
            return self.latest_time

    async def remove_queries(self, socket_id, query_ids, user):
        async with self.query_lock:
            self.validate_socket(socket_id, user)
            for query_id in query_ids:
                del self.queries[socket_id][query_id]
            return self.latest_time

    def validate_socket(self, socket_id, user):
        if self.sockets[socket_id].user != user:
            raise RuntimeError(f'socket_id, "{socket_id}", is not owner by user "{user}"')
