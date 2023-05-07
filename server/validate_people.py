import time
import threading
import mysql.connector
import paho.mqtt.client as mqttClient
import db_config
from datetime import datetime

class SensorData:
    def __init__(self):
        self.co2_data = 0
        self.csi_data = 0
        self.ultrasound_data = 0

    def update(self, topic, data):
        if topic == "radar/1/from":
            print(f"CSI: {data}")
            self.csi_data = int(data)
        elif topic == "enc":
            print(f"CO2: {data}")
            self.co2_data = int(data)
        elif topic == "ultrasound":
            print (f"ultra: {data}")
            self.ultrasound_data = int(data)
        else:
            print(f"Unknown topic: {topic}")
            print(f"Data: {data}")

    def determine_room_presence(self):
        co2_presence = min(1.0, max(0.0, float(self.co2_data) / 100.0))
        ultrasound_presence = [0.0, 0.8, 0.9, 1.0][min(3, self.ultrasound_data)]
        csi_presence = None if self.csi_data == 3 else float(self.csi_data - 1)

        if csi_presence is not None:
            presence_score = (0.4 * co2_presence) + (0.5 * ultrasound_presence) + (0.1 * csi_presence)
        else:
            presence_score = (0.4 * co2_presence) + (0.5 * ultrasound_presence)

        return int(presence_score >= 0.5), presence_score


sensor_data = SensorData()
Connected = False


def on_connect(client, userdata, flags, rc):
    global Connected
    if rc == 0:
        print("Connected to broker")
        Connected = True
    else:
        print("Connection failed")


def on_message(client, userdata, message):
    topic = message.topic
    if topic == "radar/1/from":
        # Get the second value directly from the bytes object (message byte for CSI)
        data = message.payload[1]
    else:
        data = message.payload.decode()
    sensor_data.update(topic, data)


client = mqttClient.Client("Python")
client.username_pw_set("test", password="test")
client.on_connect = on_connect
client.on_message = on_message

client.connect("193.40.245.72", port=1883)
client.loop_start()

while not Connected:
    time.sleep(0.1)

client.subscribe("#") # [radar/1/from, ESP.../enc, ESP.../ultrasound]


def save_to_database_thread():
    while True:
        time.sleep(save_interval)

        room_presence, presence_score = sensor_data.determine_room_presence()

        save_to_database(
            sensor_data.co2_data,
            sensor_data.csi_data,
            sensor_data.ultrasound_data,
            presence_score,
            room_presence,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') if room_presence else None,
        )


def save_to_database(co2_data, csi_data, ultrasound_data, presence_score, room_presence, last_presence_timestamp=None):
    try:
        connection = mysql.connector.connect(
            host=db_config.db_host,
            user=db_config.db_user,
            password=db_config.db_password,
            database=db_config.db_name
        )

        cursor = connection.cursor()

        update_query = f"""UPDATE room_presence SET
                           co2_level = {co2_data}, csi_data = {csi_data},
                           ultrasonic_people_count = {ultrasound_data},
                           presence_confidence = {presence_score},
                           presence_bool = {room_presence}"""

        if last_presence_timestamp is not None:
            update_query += f", presence_timestamp = '{last_presence_timestamp}'"

        update_query += " WHERE id = 1;" # Only implement one room in this project

        cursor.execute(update_query)
        connection.commit()

    except mysql.connector.Error as error:
        print(f"Failed to insert/update data:{error}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

save_interval = 5 # Seconds

db_thread = threading.Thread(target=save_to_database_thread)
db_thread.daemon = True
db_thread.start()

while True:
    time.sleep(1)
