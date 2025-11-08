# 🚀 Project: "GitHub" - Real-Time Event Pipeline
**Date:** November 2025  

---

## 🎯 Objective

This project implements an end-to-end streaming data pipeline that captures, processes, and stores public events from the GitHub API in real-time.  
The objective is to demonstrate a robust, scalable, and fault-tolerant architecture built with industry-standard open-source tools, orchestrated with Docker.  

Data is processed and stored in a Data Lake in Parquet format, ready for analysis.

---

## 🏛️ Solution Architecture

This architecture uses a decoupled streaming flow where Kafka acts as a central "buffer" (or queue) to ensure fault tolerance.  
All services are orchestrated via Docker Compose for easy execution and portability.  
The data flows in real-time from the source (GitHub API) to the aggregated Data Lake, ready for analysis.

### The flow works in 6 steps:

1. **Orchestration (Airflow):** An Apache Airflow DAG is scheduled to run every 5 minutes.  
2. **Production (Python):** The DAG executes a script (`producer.py`) that calls the GitHub API and sends the events (JSONs) to Kafka.  
3. **Messaging (Kafka):** Kafka ingests and stores the messages in the `github_events_raw` topic. If the consumer (Spark) fails, Kafka retains the data, ensuring zero data loss.  
4. **Consumption (Spark):** A Spark Structured Streaming job (`consumer.py`) listens to the Kafka topic 24/7.  
5. **Transformation (ETL):** As data arrives, Spark processes it in micro-batches:  
   - It defines and applies a schema to the data.  
   - It "flattens" the nested JSON structures (e.g., `actor.login`, `repo.name`).  
   - It creates partitioning columns (`year`, `month`, `day`).  
6. **Loading (DataLake):** The clean, transformed data is saved in Parquet format to a local volume, partitioned by date.

---

## 📁 Project Structure

```plaintext
github_pulse1/
├── .env                  # Environment config file (Ignored by Git)
├── .gitignore            # Tells Git which files and folders to ignore
├── docker-compose.yml    # The "brain" of Docker, defines and connects all services
├── README.md             # This documentation
│
├── airflow/
│   ├── dags/
│   │   └── github_events_dag.py  # The DAG that orchestrates the producer
│   └── ... (logs, plugins)
│
├── producer/
│   ├── Dockerfile            # Recipe to build the producer image
│   ├── producer.py           # Python script (GitHub API -> Kafka)
│   └── requirements.txt      # Libraries (requests, kafka-python)
│
└── spark/
    ├── app/
    │   └── consumer.py       # PySpark script (Kafka -> Parquet + Console)
    └── data/
        ├── checkpoints/      # (Ignored) Spark Streaming "bookmarks"
        └── processed/        # (Ignored) Where the .parquet files are saved
```

---

## ⚙️ Tech Stack

### 🐳 Docker & Docker Compose  
**Role:** Virtualization & Environment  
**Why:** Containerizes every service, ensuring a portable and reproducible environment.  

---

### 🪶 Apache Airflow  
**Role:** Task Orchestration  
**Why:** Reliably schedules the producer script at regular intervals.  

---

### 💬 Apache Kafka  
**Role:** Message Bus (Buffer)  
**Why:** The heart of fault tolerance. It decouples the producer from the consumer, guaranteeing zero data loss if the consumer fails.  

---

### 🔥 Apache Spark  
**Role:** Streaming Data Processing  
**Why:** A powerful, distributed engine for large-scale ETL. Structured Streaming allows for efficient real-time (micro-batch) processing.  

---

### 🐍 Python  
**Role:** The "glue" of the project  
**Why:** Used to write the Producer (`producer.py`) and Consumer (`consumer.py` via PySpark) scripts.  

---

### 📦 Parquet Format  
**Role:** Optimized Storage (Data Lake)  
**Why:** A highly compressed, columnar format ideal for fast analytical queries.  

---

## ▶️ How to Run This Project

Follow these steps to configure and run the entire pipeline on your local machine.

---

### 1️⃣ Prerequisites
- Docker Desktop (for Windows/Mac)  
- A GitHub Personal Access Token (PAT) with `public_repo` permissions  

---

### 2️⃣ Environment Setup (Windows Only)

This project was debugged to solve specific Windows-Docker issues:

#### Expose the Docker Daemon:
1. Open Docker Desktop Settings > General  
2. CHECK the box: “Expose daemon on tcp://localhost:2375 without TLS”  
3. Click “Apply & Restart”  

#### Verify the Airflow DAG:
The `airflow/dags/github_events_dag.py` file must use  
`docker_url='tcp://host.docker.internal:2375'` in the DockerOperator.  

---

### 3️⃣ Project Setup

First, clone the repository and create the `.env` file for Airflow permissions.

```bash
git clone https://github.com/jovesoncosta/streaming-data-pipeline-kafka-spark-airflow.git
cd your-repository
echo "AIRFLOW_UID=50000" > .env
```

*(The GITHUB_TOKEN will be configured in the Airflow UI for better security.)*


Next, build the Docker image that Airflow will use to run the producer:

```bash
docker build -t github_producer:latest ./producer
```

---

### 4️⃣ Starting the Pipeline (Command Sequence)

#### 1. Start All Services
```bash
docker-compose up -d
```

#### 2. Configure the Airflow Variable
Wait 1–2 minutes for Airflow to start.  
Access the UI: [http://localhost:8081](http://localhost:8081)  
(login: admin / pass: admin).  
Go to “Admin” → “Variables”.  
Add a new variable:  

- **Key:** `GITHUB_TOKEN`  
- **Val:** Paste your GitHub Token (e.g., `ghp_...`)  

Click “Save”.  

#### 3. Create the Kafka Topic
*(The topic must be created manually, as `docker-compose down` deletes it.)*

```bash
docker-compose exec kafka kafka-topics --create --topic github_events_raw --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
```

#### 4. Start the Consumer (Spark)
Open a new terminal (and keep it open).  
Run the Spark job. It will “listen” to the Kafka topic.

```bash
docker-compose exec --user root spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 /opt/spark/work-dir/app/consumer.py
```

#### 5. Start the Producer (Airflow)
With Spark “listening,” go back to the Airflow UI.  
Enable the `github_events_producer` DAG (click the “play” toggle).  
Trigger it manually by clicking the “play” button → “Trigger DAG”.

<img width="1887" height="472" alt="dagss" src="https://github.com/user-attachments/assets/f9fb0b7c-e928-41d3-911c-fe546c6dfbb5" />

---

## 5️⃣ Verify the Results

#### Spark Terminal
You will see the micro-batches being printed to the terminal (from the `format("console")` sink).

<img width="853" height="476" alt="batch" src="https://github.com/user-attachments/assets/40d995ff-e510-42ac-90bc-249eae007826" />

#### Data Lake
Check the `spark/data/processed/events/` folder.  
The `year`, `month`, and `day` folders will be created and will contain your `.parquet` files!
