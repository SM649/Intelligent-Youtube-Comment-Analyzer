from datetime import datetime, timezone
from firebase_admin import firestore
from firebase_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter
from werkzeug.security import generate_password_hash, check_password_hash


class Database:
    def __init__(self):
        self.db = get_firestore_client()
        self.users = self.db.collection('users_data')
        self.video_analysis = self.db.collection('video_analysis')

    def register_user(self, username: str, email: str, password: str, profile_image_b64: str = None) -> tuple[bool, str]:
        if self.users.document(username).get().exists:
            return False, "Username already taken"
        if list(self.users.where(filter=FieldFilter('email', '==', email)).limit(1).stream()):
            return False, "Email already registered"

        user_doc = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
        }
        if profile_image_b64:
            user_doc['profile_image_b64'] = profile_image_b64

        self.users.document(username).set(user_doc)
        return True, "Registration successful"

    def verify_user(self, email, password):
        matches = list(self.users.where(filter=FieldFilter('email', '==', email)).limit(1).stream())
        if not matches:
            return False, None
        user = matches[0].to_dict()
        if check_password_hash(user['password'], password):
            return True, user
        return False, None

    def get_user_video_ids(self, username):
        docs = [d.to_dict() for d in self.video_analysis.where(filter=FieldFilter('username', '==', username)).select(['video_id', 'Video_Title']).stream()]
        video_ids = [d["video_id"] for d in docs]
        video_titles = [d.get("Video_Title", "No Title Found") for d in docs]
        return video_ids, video_titles

    def save_analysis(self, username, video_id, analysis_data, bar_chart, emoji_chart):
        """Save analysis results in Firestore along with chart images (as base64 strings)."""
        analysis_data.update({
            "username": username,
            "video_id": video_id,
            "bar_chart_id": bar_chart,
            "emoji_chart_id": emoji_chart,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        })
        self.video_analysis.add(analysis_data)

    def get_user_analysis_history(self, username):
        return [d.to_dict() for d in self.video_analysis.where(filter=FieldFilter('username', '==', username)).stream()]

    def get_recent_analyses(self, username, limit=3):
        """Returns the user's most recently analyzed videos, newest first.

        Entries saved before the `analyzed_at` field existed are excluded by
        Firestore's order_by (a doc missing the ordered field never matches),
        which is an accepted limitation, not a bug.
        """
        query = (
            self.video_analysis
                .where(filter=FieldFilter('username', '==', username))
                .order_by('analyzed_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .select(['video_id', 'Video_Title'])
        )
        return [d.to_dict() for d in query.stream()]

    def delete_analysis(self, username, video_id):
        docs = list(
            self.video_analysis
                .where(filter=FieldFilter('username', '==', username))
                .where(filter=FieldFilter('video_id', '==', video_id))
                .stream()
        )
        for d in docs:
            d.reference.delete()
        return len(docs) > 0

    def get_user_profile_image(self, username: str) -> str | None:
        doc = self.users.document(username).get()
        if doc.exists:
            return doc.to_dict().get('profile_image_b64')
        return None

    def update_user_profile(self,
                        old_username: str,
                        new_username: str,
                        new_password: str = None,
                        profile_image_b64: str = None
                        ) -> tuple[bool, str]:
        old_ref = self.users.document(old_username)
        old_doc = old_ref.get()
        if not old_doc.exists:
            return False, "User not found"

        if new_username != old_username and self.users.document(new_username).get().exists:
            return False, "Username already taken"

        update_fields = {}
        if new_password:
            update_fields['password'] = generate_password_hash(new_password)
        if profile_image_b64:
            update_fields['profile_image_b64'] = profile_image_b64

        if not update_fields and new_username == old_username:
            return True, "No changes made"

        if new_username != old_username:
            # Document ID is the username, so a rename is copy-then-delete, not an update.
            user_data = old_doc.to_dict()
            user_data.update(update_fields)
            user_data['username'] = new_username
            self.users.document(new_username).set(user_data)
            old_ref.delete()
        else:
            old_ref.update(update_fields)

        return True, "Profile updated successfully"

    def get_analysis_by_video_id(self, video_id):
        matches = list(self.video_analysis.where(filter=FieldFilter('video_id', '==', video_id)).limit(1).stream())
        return matches[0].to_dict() if matches else None

    def get_analysis_for_user(self, username, video_id):
        matches = list(
            self.video_analysis
                .where(filter=FieldFilter('username', '==', username))
                .where(filter=FieldFilter('video_id', '==', video_id))
                .limit(1)
                .stream()
        )
        return matches[0].to_dict() if matches else None
