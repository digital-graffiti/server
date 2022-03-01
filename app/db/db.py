import time
from uuid import uuid4
from os import getenv
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import APIRouter, Depends, WebSocket, HTTPException, Body
from ..token import token_to_user
from .broker import QueryBroker
from .socket import QuerySocket
from .rewrite import object_rewrite, query_rewrite

max_limit = float(getenv('QUERY_LIMIT'))

router = APIRouter()

class QueryObjects(BaseModel):
    db: object
    qb: object
qo = QueryObjects()

@router.on_event("startup")
async def start_query_sockets():
    # Connect to the database
    client = AsyncIOMotorClient('mongo')
    qo.db = client.test3.objects

    # Create indexes if they don't already exist
    await qo.db.create_index('obj.uuid')
    await qo.db.create_index('obj.created')
    await qo.db.create_index('obj.signed')

    # Create a broker and listen
    # to messages forever
    qo.qb = QueryBroker(qo.db)

@router.post('/insert')
async def insert(
        obj: dict,
        near_misses: list[dict],
        access: list[str]|None=None,
        user: str=Depends(token_to_user)):

    # Date and sign the object
    obj['created'] = time.time_ns()
    obj['uuid'] = str(uuid4())
    data = object_rewrite(obj, near_misses, access, user)

    # Insert it into the database
    await qo.db.insert_one(data)
    return {'type': 'Accept', 'uuid': obj['uuid'], 'created': obj['created']}

@router.post("/query_many")
async def query_many(
        query: dict,
        time: int = Body(default=0, ge=0),
        limit: int = Body(default=max_limit, gt=0, le=max_limit),
        skip: int = Body(default=0, ge=0),
        user: str = Depends(token_to_user)):

    # If no time specified, use the latest time
    if not time:
        time = qo.qb.latest_time

    # Do rewriting for near misses and access control
    query = query_rewrite(query, user)

    # Only find queries that happened before the time
    query["object.created"] = { "$lte": time }

    # Perform the query
    cursor = qo.db.find(
            query,
            limit=limit,
            sort=[('object.created', -1)],
            skip=skip)
    results = await cursor.to_list(length=limit)
    await cursor.close()

    results = [{
        'object': r['object'][0],
        'near_misses': r['near_misses'],
        'access': r['access']
        } for r in results]

    return results

@router.post("/query_one")
async def query_one(
        query: dict,
        time: int = Body(default=0, ge=0),
        skip: int = Body(default=0, ge=0),
        user: str = Depends(token_to_user)):

    results = await query_many(query, time, 1, skip, user)

    if results:
        return results[0]
    else:
        return None

@router.post('/replace')
async def replace(
        obj: dict,
        near_misses: list[dict],
        access: list[str]|None=None,
        obj_id: str = Body(...),
        user: str=Depends(token_to_user)):

    # First check that the object that already exists
    # and that it is owned by the user
    old_data = await query_one({
        "uuid": obj_id,
        "signed": user},
        time=0,
        skip=0,
        user=user)
    if not old_data:
        raise HTTPException(status_code=400)

    # Making sure the date and object are preserved
    obj["created"] = old_data["object"]["created"]

    # Rewrite the new data
    new_data = object_rewrite(obj, near_misses, access, user)

    # Replace the old data with the new
    await qo.db.replace_one({"object.uuid": obj_id}, new_data)
    return {'type': 'Accept', 'uuid': obj['uuid'], 'created': obj['created']}

@router.post('/delete')
async def delete(
        obj_id: str = Body(...),
        user: str=Depends(token_to_user)):

    result = await qo.db.delete_one({
        "object.uuid": obj_id,
        "object.signed": user})

    return result

@router.websocket("/query_socket")
async def query_socket(ws: WebSocket, token: str):
    # Validate and convert the token to a user id
    user = token_to_user(token)

    # Open a query socket
    qs = QuerySocket(user, ws, qo.qb)

    # Wait until it dies
    await qs.heartbeat()

@router.post('/query_socket_add')
async def query_socket_add(
        query: dict,
        query_id: str = Body(...),
        socket_id: str = Body(...),
        user: str = Depends(token_to_user)):

    try:
        # Add the query and return the time that happens
        time = await qo.qb.add_query(socket_id, query_id, query, user)
        # The time is quite large so make it a string for JS
        return str(time)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post('/query_socket_remove')
async def query_socket_remove(
        query_id: str = Body(...),
        socket_id: str = Body(...),
        user: str = Depends(token_to_user)):

    try:
        # Remove the query and return the time that happens
        time = await qo.qb.remove_queries(socket_id, query_id, user)
        # The time is quite large so make it a string for JS
        return str(time)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
