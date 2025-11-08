import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr, window
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, MapType, LongType

#Logging Config
#Configure logging so we can see what Spark is doing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Data Schema
#Schema for the 'actor' (Who performed the action)
actor_schema = StructType([
    StructField("id", LongType(), True),
    StructField("login", StringType(), True)
])

#Schema for the 'repo' (The repository where the action occurred)
repo_schema = StructType([
    StructField("id", LongType(), True),
    StructField("name", StringType(), True)
])

#Main event schema (the complete JSON that comes from Kafka)
#This is the structure of the message that our Producer sent
event_schema = StructType([
    StructField("id", StringType(), True),
    StructField("type", StringType(), True),
    StructField("actor", actor_schema, True),
    StructField("repo", repo_schema, True),
    StructField("created_at", TimestampType(), True),
    StructField("payload", MapType(StringType(), StringType()), True) 
])

def main():
    logger.info("Iniciando a sessão Spark...")

    #1-Create a Spark Session
    #Build the Spark session. The "master" is 'spark://spark-master:7077'
    #The address of our Spark master on the Docker network
    #We need to tell Spark to include the Kafka packages
    spark = SparkSession.builder \
        .appName("GitHubEventsConsumer") \
        .master("spark://spark-master:7077") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
        .getOrCreate()

    #Set the Spark log level to WARN to reduce noise
    spark.sparkContext.setLogLevel("WARN")
    logger.info("Spark session created successfully...")

    #2-Read Kafka's Stream
    #The topic 'github_events_raw' on broker 'kafka:9092'
    df_kafka = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "github_events_raw") \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load()

    logger.info("Kafka stream Connected!")

    #3-Transforming the Data (ETL)
    #Kafka data comes in 'key' and 'value' columns (in bytes)
    #The 'value' is our JSON! Let's convert it to a String
    #Apply our 'event_schema' to transform it into a structured DataFrame
    df_events = df_kafka.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), event_schema).alias("data")) \
        .select("data.*") #"Flatten" the 'data' structure into columns

    #Columns for 'id', 'type', 'actor', 'repo', and 'created_at'
    #flattening the nested columns 'actor' and 'repo'
    df_flattened = df_events \
        .withColumn("actor_id", col("actor.id")) \
        .withColumn("actor_login", col("actor.login")) \
        .withColumn("repo_id", col("repo.id")) \
        .withColumn("repo_name", col("repo.name")) \
        .drop("actor", "repo", "payload") 

    #Add 'year', 'month', 'day' columns for partitioning
    #Partition the data into folders
    df_final = df_flattened \
        .withColumn("year", expr("year(created_at)")) \
        .withColumn("month", expr("month(created_at)")) \
        .withColumn("day", expr("dayofmonth(created_at)"))

    logger.info("Transformation (Schema and Flatten) Defined.")

    #4-Write the Stream to the Data Lake (Parquet)
    #Defines the output location within the Spark container
    #Mapped this folder in docker-compose to 'spark/data/processed'
    output_path = "/opt/spark/work-dir/data/processed/events"
    
    #Define the location for the checkpoints
    #Spark needs checkpoints to manage the stream state
    checkpoint_path = "/opt/spark/work-dir/data/checkpoints/events_consumer_V3"

    ################ Start the streaming query ################
    query = df_final.writeStream \
        .format("parquet") \
        .outputMode("append") \
        .partitionBy("year", "month", "day") \
        .option("path", output_path) \
        .option("checkpointLocation", checkpoint_path) \
        .start()

    logger.info(f"Streaming started! Writing in {output_path}")
    logger.info(f"Checkpoints in {checkpoint_path}")
    
    #It also writes to the terminal for debugging
    logger.info("A iniciar o stream da consola...")
    query_console = df_final.writeStream \
        .format("console") \
        .outputMode("append") \
        .trigger(processingTime="15 seconds") \
        .start()

    #Keep the script running 
    #The awaitTermination() will NOW wait for BOTH queries!
    query.awaitTermination()

if __name__ == "__main__":
    main()