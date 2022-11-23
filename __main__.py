from rabbitmq_sync import start


if __name__ == '__main__':
    start('amqp://guest:guest@localhost:5672//')