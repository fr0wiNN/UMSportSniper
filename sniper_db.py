import mysql.connector
import MySQLdb
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from notifier import Notifier
import datetime
import time
import re

def get_sports_from_db():
    conn = MySQLdb.connect(
        host="localhost",
        user="---", 
        password="---", # Nie dla psa...
        database="sports_sniper"
    )
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT sport_name AS str, url FROM sports")
    sports = cursor.fetchall()
    conn.close()
    return sports

# Load sports from database
SPORTS = get_sports_from_db()
print("Loaded sports:", SPORTS)

# Configure Selenium WebDriver
options = webdriver.ChromeOptions()
# options.add_argument("--headless=new")  # Uncomment to run headless
chrome_driver_path = "/usr/local/bin/chromedriver"  # Adjust to your path
service = Service(chrome_driver_path)
browser = webdriver.Chrome(service=service, options=options)
print("Chrome was launched successfully")

notifier = Notifier()

# Function to take a snapshot of the HTML for a specific sport
def take_snapshot(sport):
    browser.get(f"https://myusc.maastrichtuniversity.nl/p/sporten/{sport['url']}")
    time.sleep(5)
    save_html_snapshot(sport['str'])

# Function to save the HTML snapshot for parsing
def save_html_snapshot(name):
    print(f"Saved snapshot for {name} at {datetime.datetime.now()}")
    os.makedirs('snapshots', exist_ok=True)
    with open(f'snapshots/snapshot_{name}.html', 'w', encoding="utf-8") as file:
        file.write(browser.page_source)

# Function to extract classes from the saved HTML file of a specific sport
def extract_classes(sport_name):
    # Read the saved HTML file for the sport
    with open(f"snapshots/snapshot_{sport_name}.html", "r", encoding="utf-8") as file:
        page_html = file.read()
    soup = BeautifulSoup(page_html, "html.parser")

    # Locate all containers with classes starting with "mx-name-container"
    container_pattern = re.compile(r'mx-name-container\d+')
    activities = soup.find_all("div", class_=container_pattern)

    availability_data = []
    unique_entries = set()  # To track unique activity entries

    for activity in activities:
        try:
            name = activity.find("div", class_="mx-name-textBox14").text.strip()
        except AttributeError:
            name = "N/A"

        try:
            location = activity.find("div", class_="mx-name-textBox3").text.strip()
        except AttributeError:
            location = "N/A"

        try:
            date = activity.find("div", class_="mx-name-datePicker14").text.strip()
        except AttributeError:
            date = "N/A"

        try:
            day = activity.find("div", class_="mx-name-datePicker20").text.strip()
        except AttributeError:
            day = "N/A"

        try:
            start_time = activity.find("div", class_="mx-name-datePicker15").text.strip()
        except AttributeError:
            start_time = "N/A"

        try:
            end_time = activity.find("div", class_="mx-name-datePicker16").text.strip()
        except AttributeError:
            end_time = "N/A"

        try:
            availability = activity.find("div", class_="mx-name-textBox20").text.strip()
        except AttributeError:
            availability = "N/A"

        # Check for sign-up button or link
        try:
            sign_up_button = activity.find("button", class_="mx-button mx-name-microflowButton4")
            sign_up_available = sign_up_button is not None and "disabled" not in sign_up_button.get("class", [])
        except AttributeError:
            sign_up_available = False

        # Create a unique key for this entry to avoid duplicates
        entry_key = (name, location, day, date, start_time, end_time)
        if entry_key not in unique_entries and name != "N/A" and location != "N/A" and date != "N/A" and day != "N/A" and start_time != "N/A" and end_time != "N/A" and availability != "N/A":
            unique_entries.add(entry_key)  # Mark entry as seen

            # Add to availability data if it's unique
            availability_data.append({
                "Class Name": name,
                "Location": location,
                "Date": f"{day}, {date}",
                "Time": f"{start_time} - {end_time}",
                "Availability": availability,
                "Sign-Up Available": sign_up_available  # True if sign-up is enabled
            })

    return availability_data

# Tracking function to notify when spots open up for a specific sport
def check_for_open_spots(sport):
    global previous_availability_data

    # Refresh HTML snapshot
    take_snapshot(sport)
    
    # Get current class availability data
    current_data = extract_classes(sport['str'])
    
    for entry in current_data:
        class_id = (sport['str'], entry["Class Name"], entry["Location"], entry["Date"], entry["Time"])  # Unique identifier including sport name
        current_sign_up_available = entry["Sign-Up Available"]
        current_availability = entry["Availability"]

        print(entry)

        # Check if we have previous data for this class
        if class_id in previous_availability_data:
            previous_sign_up_available = previous_availability_data[class_id]["Sign-Up Available"]
            previous_availability = previous_availability_data[class_id]["Availability"]
            
            # Notify if availability increased or sign-up status changed to open
            if (previous_availability == "0" and current_availability != "0") or (not previous_sign_up_available and current_sign_up_available):
                print(f"Spot opened up for {sport['str']} at {entry['Location']} on {entry['Date']} from {entry['Time']}!")
                notifier.notify_users(sport_name=sport['str'] , message=f"===== {sport['str']} =====\\n- {entry['Location']}\\n- {entry['Date']}\\n- {entry['Time']}")

        # Update the previous data for this class
        previous_availability_data[class_id] = {
            "Sign-Up Available": current_sign_up_available,
            "Availability": current_availability
        }


# Store previous availability state of classes for each sport
previous_availability_data = {}

# Periodic check loop
try:
    while True:
        for sport in SPORTS:
            check_for_open_spots(sport)
        time.sleep(60)  # Check every minute

except KeyboardInterrupt:
    print("Stopped monitoring.")
finally:
    browser.quit()
