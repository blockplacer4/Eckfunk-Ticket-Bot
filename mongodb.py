# mongodb.py
"""
MongoDB Modul fÃ¼r den Discord Ticket Bot.
Es wird ein globaler Client verwendet, der intern Connection-Pooling nutzt.
"""

import configparser
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Lese Konfiguration
_config = configparser.ConfigParser()
_config.read("config.ini")
mongodb_uri = _config["KEYS"]["mongodb_connection_string"]

# Globaler Motor-Client
client = AsyncIOMotorClient(mongodb_uri)
db = client["TicketSystem"]


async def insert_new_ticket(
    ticket_id,
    user_id,
    ticket_type,
    last_message,
    channel_id,
    status,
    embed_message,
    opening_context=None, # Added
):
    """Fügt ein neues Ticket mit optionalem Öffnungskontext hinzu."""
    collection = db["tickets"]
    data = {
        "_id": ticket_id,
        "user_id": user_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc), # Store as UTC
        "ticket_type": ticket_type,
        "last_message": last_message,
        "channel_id": channel_id,
        "embed_message": embed_message,
        "status": status,
        "transcript_thread_id": None,
        "opening_context": opening_context, # Added
    }
    await collection.insert_one(data)


async def update_ticket_data(collection_name, finding_id, data):
    """Aktualisiert spezifische Felder eines Dokuments."""
    collection = db[collection_name]
    await collection.update_one({"_id": finding_id}, {"$set": data})


async def new_config(finding_id, data):
    """Erstellt oder aktualisiert die Bot-Konfiguration."""
    collection = db["config"]
    if await collection.find_one({"_id": finding_id}):
        await collection.update_one({"_id": finding_id}, {"$set": data})
        return
    data["_id"] = finding_id
    data["counting_id"] = 0 # Initialize counter if new
    await collection.insert_one(data)


async def get_new_ticket_id():
    """Holt die nächste Ticket-ID und inkrementiert den Zähler."""
    collection = db["config"]
    config_doc_id = 2104 # Assuming this is the intended config ID
    # Use find_one_and_update for atomic increment
    result = await collection.find_one_and_update(
        {"_id": config_doc_id},
        {"$inc": {"counting_id": 1}},
        upsert=True, # Create if doesn't exist
        return_document=True # Return the *updated* document
    )
    if not result:
         # Should not happen with upsert=True, but handle defensively
         await new_config(config_doc_id, {"counting_id": 1}) # Initialize if somehow missed
         return 1
    return result["counting_id"]


async def get_data(collection_name, data_id, field):
    """Holt einen spezifischen Feldwert aus einem Dokument."""
    collection = db[collection_name]
    document = await collection.find_one({"_id": data_id})
    # Use .get() for safer access
    return document.get(field) if document else None


async def get_all_tickets():
    """Holt die IDs aller Tickets (potenziell speicherintensiv)."""
    collection = db["tickets"]
    ids = [doc["_id"] async for doc in collection.find({}, {"_id": 1})]
    return ids


async def find_ticket_by_id(ticket_id):
    """Findet ein Ticket anhand seiner numerischen ID."""
    collection = db["tickets"]
    try:
        numeric_id = int(ticket_id)
    except ValueError:
        return None
    return await collection.find_one({"_id": numeric_id})


async def find_ticket_by_channel_id(channel_id):
    """Findet ein Ticket anhand der Kanal-ID."""
    collection = db["tickets"]
    return await collection.find_one({"channel_id": channel_id})

