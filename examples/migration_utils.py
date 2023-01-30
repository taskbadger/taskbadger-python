import random
import time


def prepare_migration():
    return {}


def get_total(context):
    context['total'] = random.randint(100, 1000)
    return context['total']


def get_data_chunks(context):
    chunks = random.randint(5, 10)
    chunk_size = context['total'] // chunks
    remainder = context['total'] - (chunks * chunk_size)
    for i in range(chunks):
        yield [1] * chunk_size

    if remainder > 0:
        yield [1] * remainder


def process_chunk(context, chunk):
    time.sleep(max(0.1, len(chunk) / 200))
