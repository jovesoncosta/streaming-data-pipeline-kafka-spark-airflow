import os
import requests
import json
import logging
from kafka import KafkaProducer
from time import sleep

#Configure the logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Get the GitHub token from the environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    logger.error("GITHUB_TOKEN was not defined in the environment variables!")
    exit(1) #Exit the script if the token is not present

#GitHub Public Events API URL
API_URL = "https://api.github.com/events"

#Kafka Config
#'kafka:9092' This is the address of our Kafka service within the Docker network
KAFKA_BROKER = 'kafka:9092'
KAFKA_TOPIC = 'github_events_raw'

#Main Functions

def create_kafka_producer():

    #Make 5 attempts
    retries = 5
    while retries > 0:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                #Converts the value into JSON and then into bytes
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info("Kafka connected successfully...")
            return producer
        except Exception as e:
            logger.warning(f"Unable to connect to Kafka: {e}. Trying again in 10s...")
            retries -= 1
            sleep(10)
    logger.error("Unable to connect to Kafka after many attempts...")
    return None

def fetch_github_events():

    #looking for GitHub API events using the authentication token
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    try:
        response = requests.get(API_URL, headers=headers)
        
        #Check if the API has limited
        if response.status_code == 403:
            logger.warning(f"GitHub API rate limit reached! Headers: {response.headers}")
            return None
        
        #Check for errors
        response.raise_for_status() 
        
        return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving data from the GitHub API: {e}")
        return None

def main():

    #1-Producer Kafka
    #2-GitHub events
    #3-Send each event to the Kafka topic.
  
    producer = create_kafka_producer()
    if not producer:
        return 

    events = fetch_github_events()
    
    if events:
        event_count = 0
        for event in events:
            #The event 'id' as the message key
            #Kafka can partition better the data
            event_id = event.get('id') 
            
            #Send the message (the complete event dictionary)
            producer.send(KAFKA_TOPIC, value=event, key=event_id.encode('utf-8'))
            event_count += 1
            
        #Make sure all messages were sent 
        producer.flush()
        logger.info(f"Producer: {event_count} events sent to the topic '{KAFKA_TOPIC}'.")
    else:
        logger.info("Producer: No events were found or there was an error.")

    if producer:
        producer.close()

if __name__ == "__main__":
    main()