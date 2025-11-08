from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.dates import days_ago

#Standard arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

with DAG(
    dag_id='github_events_producer',
    default_args=default_args,
    description='Coleta eventos do GitHub e envia para o Kafka a cada 5 minutos.',
    schedule_interval='*/5 * * * *',  #5 minutes
    start_date=days_ago(0),
    catchup=False, #Don't try to run "lost jobs" from the past
    tags=['github', 'kafka', 'producer'],
) as dag:

    #This is our only task
    run_producer_task = DockerOperator(
        task_id='run_github_producer',
        image='github_producer:latest', 
        command='python producer.py',    
        docker_url='tcp://host.docker.internal:2375',
        network_mode='github_pulse1_data_pulse_net', 
        environment={
            'GITHUB_TOKEN': '{{ var.value.GITHUB_TOKEN }}'
        },
        auto_remove=True,
    )