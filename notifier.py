import MySQLdb
from pushbullet import API

class Notifier:
    def __init__(self):
        self.api = API()
        self.api.set_token('o.gdEYBUeDZHbKmBCIwkgt81OlnjhrKzMd')

    @staticmethod
    def get_users_for_sport(sport_name):
        # Connect to MySQL database
        conn = MySQLdb.connect(
            host="localhost",
            user="max",
            password="Brzozowa15",
            database="sports_sniper"
        )
        cursor = conn.cursor()
        # Fetch users interested in the given sport
        cursor.execute("""
            SELECT u.username, u.api_token
            FROM users u
            JOIN user_sports us ON u.user_id = us.user_id
            JOIN sports s ON us.sport_id = s.sport_id
            WHERE s.sport_name = %s
        """, (sport_name,))
        
        # Fetch all rows and map to dictionaries manually
        users = []
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            users.append(dict(zip(columns, row)))
        
        conn.close()
        return users

    def notify_users(self, sport_name, message):
        # Get users interested in the specific sport
        users = self.get_users_for_sport(sport_name)
        for user in users:
            print(f"Sending notification to {user['username']} with token {user['api_token']}")
            # Send notification using each user's API token
            self.api.set_token = user['api_token']
            self.api.send_note(
                "Spot Available!",
                message
            )
