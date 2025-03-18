"""
MongoDB Modul für den Discord Ticket Bot.
Es wird ein globaler Client verwendet, der intern Connection-Pooling nutzt.
"""

import configparser
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Lese Konfiguration
_config = configparser.ConfigParser()
_config.read("config.ini")
mongodb_uri = _config["KEYS"]["mongodb_connection_string"]

# Globaler Motor-Client (verwendet intern einen Connection-Pool)
client = AsyncIOMotorClient(mongodb_uri)
db = client["TicketSystem"]


async def insert_new_ticket(
    ticket_id, user_id, ticket_type, last_message, channel_id, status, embed_message
):
    collection = db["tickets"]
    data = {
        "_id": ticket_id,
        "user_id": user_id,
        "created_at": datetime.datetime.now(),
        "ticket_type": ticket_type,
        "last_message": last_message,
        "channel_id": channel_id,
        "embed_message": embed_message,
        "status": status,
    }
    await collection.insert_one(data)


async def update_ticket_data(collection_name, finding_id, data):
    collection = db[collection_name]
    await collection.update_one({"_id": finding_id}, {"$set": data})


async def new_config(finding_id, data):
    collection = db["config"]
    if await collection.find_one({"_id": finding_id}):
        await collection.update_one({"_id": finding_id}, {"$set": data})
        return
    data["_id"] = finding_id
    data["counting_id"] = 0
    await collection.insert_one(data)


async def get_new_ticket_id():
    collection = db["config"]
    document = await collection.find_one({"_id": 2104})
    new_count = document["counting_id"] + 1
    await collection.update_one({"_id": 2104}, {"$set": {"counting_id": new_count}})
    return new_count


async def get_data(collection_name, data_id, field):
    collection = db[collection_name]
    document = await collection.find_one({"_id": data_id})
    return document[field]


async def get_all_tickets():
    collection = db["tickets"]
    ids = []
    async for document in collection.find():
        ids.append(document["_id"])
    return ids


async def delete_ticket(_id):
    collection = db["tickets"]
    document = await collection.find_one({"_id": _id})
    await collection.delete_one(document)
