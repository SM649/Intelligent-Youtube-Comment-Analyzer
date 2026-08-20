from pymongo import MongoClient
import gridfs

from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['YCA']
        self.users = self.db['users_data']
        self.video_analysis = self.db['video_analysis']
        self.fs = gridfs.GridFS(self.db)  # Initialize GridFS

    def register_user(self,username: str,email: str,password: str,profile_image_b64: str = None) -> tuple[bool, str]:
      # 1) check for duplicates
        if self.users.find_one({'email': email}):
            return False, "Email already registered"
        if self.users.find_one({'username': username}):
            return False, "Username already taken"

        # 2) hash password
        hashed_password = generate_password_hash(password)

        # 3) build user doc
        user_doc = {
            'username': username,
            'email':    email,
            'password': hashed_password,
        }
        # 4) include image if provided
        if profile_image_b64:
            user_doc['profile_image_b64'] = profile_image_b64

        # 5) insert into Mongo
        self.users.insert_one(user_doc)

        # 6) success
        return True, "Registration successful"

    def verify_user(self, email, password):
        user = self.users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            return True, user
        return False, None

    def save_image(self, image_data, filename):
        """Save image to MongoDB GridFS and return the file ID."""
        file_id = self.fs.put(image_data, filename=filename)
        return file_id
    
    def get_user_video_ids(self, username):
        # Query the video_analysis collection to get all video data for the given user.
        # We convert the result to a list so we can iterate over it twice.
        video_data = list(self.video_analysis.find({"username": username}))
        
        # Extract the video_id from each entry and store them in a list.
        video_ids = [entry["video_id"] for entry in video_data]

        # Extract the Video_Title from each entry.
        # If a document doesn't have "Video_Title", it will use "No Title Found" as the default.
        video_titles = [entry.get("Video_Title", "No Title Found") for entry in video_data]
        
        # Return both the list of video IDs and video titles.
        return video_ids, video_titles

    def save_analysis(self, username, video_id, analysis_data, bar_chart, emoji_chart):
        """Save analysis results in MongoDB along with chart images."""

        analysis_data.update({
            "username": username,
            "video_id": video_id,
            "bar_chart_id": bar_chart,
            "emoji_chart_id": emoji_chart
        })

        # Insert into MongoDB
        self.video_analysis.insert_one(analysis_data)
    
    def get_user_analysis_history(self, username):
        """Fetches the analysis history for a given user."""
        return list(self.video_analysis.find({"username": username}))
    
    # In your database.py file
    def delete_analysis(self, username, video_id):
        """Deletes a specific video analysis record for a given user."""
        result = self.video_analysis.delete_one({"username": username, "video_id": video_id})
        return result.deleted_count > 0
    
    def get_user_profile_image(self, username: str) -> str | None:
        """
        Returns the Base64 string for the user's profile image,
        or None if not set.
        """
        user = self.users.find_one(
            {'username': username},
            {'_id': 0, 'profile_image_b64': 1}
        )
        if user and user.get('profile_image_b64'):
            return user['profile_image_b64']
        return None
    
    def update_user_profile(self,
                        old_username: str,
                        new_username: str,
                        new_password: str = None,
                        profile_image_b64: str = None
                        ) -> tuple[bool, str]:
        """
        Updates the given user's username, password, and/or profile image.
        Returns (True, message) on success, or (False, error_message).
        """

        # 1) Make sure the user actually exists
        user = self.users.find_one({'username': old_username})
        if not user:
            return False, "User not found"

        # 2) If they changed their username, ensure it's not already taken
        if new_username != old_username:
            if self.users.find_one({'username': new_username}):
                return False, "Username already taken"

        # 3) Build the set of fields to update
        update_fields = {}
        if new_username != old_username:
            update_fields['username'] = new_username
        if new_password:
            # hash the new password
            update_fields['password'] = generate_password_hash(new_password)
        if profile_image_b64:
            update_fields['profile_image_b64'] = profile_image_b64

        # 4) If nothing to update, return early
        if not update_fields:
            return True, "No changes made"

        # 5) Perform the update
        result = self.users.update_one(
            {'username': old_username},
            {'$set': update_fields}
        )

        if result.matched_count == 0:
            return False, "Failed to update profile"
        else:
            return True, "Profile updated successfully"


