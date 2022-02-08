from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import time
import json
from uuid import UUID
from .auth import token_to_user

router = APIRouter()

# Connect to the database
client = AsyncIOMotorClient('mongo')
client.get_io_loop = asyncio.get_running_loop
db = client.test

@router.put('/put')
async def put(
        activity:    Optional[str] = None,
        near_misses: Optional[List[str]] = [],
        access:      Optional[List[UUID]] = None,
        user:        UUID = Depends(token_to_user)):

    # Sign and date the activity
    activity = parse_activity(activity)
    activity['signed'] = str(user)
    activity['created'] = time.time_ns()

    # Combine it into one big document
    data = {
        "activity": [activity],
        "near_misses": [parse_activity(nm) for nm in near_misses],
        "access": access
    }

    # Insert it into the database
    output = await db.activities.insert_one(data)

    return 'OK'

def parse_activity(activity):
    try:
        activity = json.loads(activity)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {activity}")
    if not isinstance(activity, dict):
        raise HTTPException(status_code=400, detail=f"JSON root is not a dictionary: {activity}")
    return activity
