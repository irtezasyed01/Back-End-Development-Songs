from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys
import traceback 

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

collection = db.songs

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return jsonify(dict(status="OK")), 200

@app.route("/count")
def count():
    """Return the length of data"""
    count = collection.count_documents({})  # Count all documents in the collection
    return jsonify({"count": count}), 200  # Respond with the count and HTTP OK (200) status code

@app.route("/song", methods=["GET"])
def songs():
    # docker run -d --name mongodb-test -e MONGO_INITDB_ROOT_USERNAME=user
    # -e MONGO_INITDB_ROOT_PASSWORD=password -e MONGO_INITDB_DATABASE=collection mongo
    results = list(db.songs.find({}))
    print(results[0])
    return {"songs": parse_json(results)}, 200

@app.route("/song", methods=["POST"])
def create_song():
    # get data from the json body
    song_in = request.json

    print(song_in["id"])

    # if the id is already there, return 303 with the URL for the resource
    song = db.songs.find_one({"id": song_in["id"]})
    if song:
        return {
            "Message": f"song with id {song_in['id']} already present"
        }, 302

    insert_id: InsertOneResult = db.songs.insert_one(song_in)

    return {"inserted id": parse_json(insert_id.inserted_id)}, 201

    
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update an existing song in the database"""
    try:
        # Extract song data from the request body
        song_data = request.get_json()

        # Find the song in the database using its ID
        existing_song = collection.find_one({"id": id})

        if existing_song:
            # If the song exists, update it with the incoming request data
            update_result = collection.update_one({"id": id}, {"$set": song_data})
            
            # Return the updated song data as JSON with HTTP OK (200) status code
            return jsonify(song_data), 200

        else:
            # If the song does not exist, send back a status of 404 with a message
            return jsonify({"message": "song not found"}), 404

    except Exception as e:
        # If there's an error, log it and return an error response
        app.logger.error(f"Error occurred while updating song: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
    
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete an existing song from the database"""
    try:
        # Delete the song from the database using its ID
        delete_result = collection.delete_one({"id": id})

        # Check the deleted_count attribute of the result
        if delete_result.deleted_count == 0:
            # If the deleted_count is zero, send back a status of 404 with a message
            return jsonify({"message": "song not found"}), 404

        # If the deleted_count is 1, it means the song was successfully deleted
        # Return an empty body with a status of HTTP_204_NO_CONTENT
        return "", 204

    except Exception as e:
        # If there's an error, log it and return an error response
        app.logger.error(f"Error occurred while deleting song: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500



