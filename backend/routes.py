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


@app.route("/song", methods=["GET", "POST"])
def songs():
    """Return all songs from the database or create a new song"""
    if request.method == "GET":
        # Handle GET request to fetch all songs
        try:
            # Fetch all documents from the 'songs' collection
            all_songs = list(collection.find({}))

            # Prepare the response in the required format
            response_data = {"songs": all_songs}

            # Return the data as a JSON response with HTTP OK (200) status code
            return jsonify(response_data), 200

        except Exception as e:
            # If there's an error, log it and return an error response
            app.logger.error(f"Error occurred while fetching songs: {str(e)}")
            return jsonify({"error": "Internal Server Error"}), 500

    elif request.method == "POST":
        # Handle POST request to create a new song
        try:
            # Extract song data from the request body
            song_data = request.get_json()

            # Check if a song with the given ID already exists in the 'songs' collection
            existing_song = collection.find_one({"id": song_data["id"]})

            # If a song with the given ID already exists, return 302 FOUND with a message
            if existing_song:
                return jsonify({"Message": f"Song with id {song_data['id']} already present"}), 302

            # Append the new song data to the 'songs' collection
            insert_result = collection.insert_one(song_data)

            # Return the ID of the inserted song as JSON with HTTP CREATED (201) status code
            return jsonify({"inserted id": str(insert_result.inserted_id)}), 201

        except Exception as e:
            # If there's an error, log it and return an error response
            app.logger.error(f"Error occurred while creating song: {str(e)}")
            return jsonify({"error": "Internal Server Error"}), 500

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



