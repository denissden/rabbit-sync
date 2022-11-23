from uuid import uuid4
from kombu import Exchange, Queue

client_id = str(uuid4())

main_exchange = Exchange('sync', 'fanout')
empty_exchange = Exchange('empty', 'direct')
negation_exchange = Exchange(
    f'sync-negation-{client_id}',
    'headers',
    auto_delete=True,
    arguments={
        'alternate-exchange': f'sync-client-{client_id}'
    })

client_exchange = Exchange(f'sync-client-{client_id}', 'topic', auto_delete=True)
main_queue = Queue(f'q-sync-{client_id}', exchange=client_exchange, routing_key='#', auto_delete=True)


def create(channel):
    main_exchange.declare(channel=channel)
    empty_exchange.declare(channel=channel)
    negation_exchange.declare(channel=channel)

    empty_exchange.bind_to(exchange=negation_exchange, arguments={'client_id': client_id}, channel=channel)
    negation_exchange.bind_to(main_exchange, channel=channel)


def delete(channel):
    for e in (negation_exchange, client_exchange):
        e.maybe_bind(channel)
        e.delete()

