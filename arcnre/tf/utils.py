# -*- coding: utf-8 -*-

import os
import errno

import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

from . import layers # , losses, metrics
from .data import DataHandler


def auto_select_gpu(top_n=1, cuda_visible_devices=None):
    cmd = 'nvidia-smi -q -d Memory |grep -A4 GPU|grep Free'
    gpu_memory = [int(x.split()[2]) for x in os.popen(cmd).readlines()]
    if not cuda_visible_devices:
        cuda_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES")
    if cuda_visible_devices:
        gpu_memory = [gpu_memory[int(x)]
                      for x in cuda_visible_devices.split(",")]
    gpu_devices = np.argsort(gpu_memory) if gpu_memory else []
    return ','.join(map(str, gpu_devices[-top_n:]))


def config_tf_gpu(allow_soft_placement: bool = True,
                  cuda_visible_devices: str = None,
                  top_n_gpus: int = 1,
                  per_process_gpu_memory_fraction: float = 1.0,
                  gpu_allow_growth: bool = True):
    if int(tf.__version__.split('.')[0]) == 1:
        config_tf_v1_gpu(allow_soft_placement,
                         cuda_visible_devices,
                         top_n_gpus,
                         per_process_gpu_memory_fraction,
                         gpu_allow_growth)
    else:
        config_tf_v2_gpu(allow_soft_placement,
                         cuda_visible_devices,
                         top_n_gpus,
                         per_process_gpu_memory_fraction,
                         gpu_allow_growth)


def config_tf_v1_gpu(allow_soft_placement: bool = True,
                     cuda_visible_devices: str = None,
                     top_n_gpus: int = 1,
                     per_process_gpu_memory_fraction: float = 1.0,
                     gpu_allow_growth: bool = True):
    config = tf.ConfigProto()
    config.allow_soft_placement = allow_soft_placement
    config.gpu_options.visible_device_list = \
        cuda_visible_devices or auto_select_gpu(top_n_gpus)
    config.gpu_options.per_process_gpu_memory_fraction = \
        per_process_gpu_memory_fraction
    config.gpu_options.allow_growth = gpu_allow_growth
    tf.keras.backend.set_session(tf.Session(config=config))


def config_tf_v2_gpu(allow_soft_placement: bool = True,
                     cuda_visible_devices: str = None,
                     top_n_gpus: int = 1,
                     per_process_gpu_memory_fraction: float = 1.0,
                     gpu_allow_growth: bool = True):
    tf.config.set_soft_device_placement(allow_soft_placement)
    cuda_visible_devices = cuda_visible_devices or auto_select_gpu(top_n_gpus)
    if not cuda_visible_devices:
        return
    visible_device_ids = [int(x) for x in cuda_visible_devices.split(',')]
    gpus = tf.config.experimental.list_physical_devices('GPU')
    for i in visible_device_ids:
        tf.config.experimental.set_visible_devices(gpus[i], 'GPU')
        tf.config.experimental.set_memory_growth(gpus[0], gpu_allow_growth)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as ex:
        if ex.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def get_spacy_model(model_name: str, pos_tags: bool, parse: bool, ner: bool):
    import spacy
    disable = ['vectors', 'textcat']
    if not pos_tags:
        disable.append('tagger')
    if not parse:
        disable.append('parser')
    if not ner:
        disable.append('ner')
    return spacy.load(model_name, disable=disable)


def create_span(text, start, end, label):
    return {'text': text, 'start': start, 'end': end, 'label': label}


def bioes_to_spans(text, tags):
    res = []
    cur_label, start = None, None
    for idx, (ch, tag) in enumerate(zip(text, tags)):
        if tag == 'O':
            continue
        prefix, label = tag.split('-', 1)
        if prefix == 'S':
            res.append(create_span(text[idx:idx+1], idx, idx+1, label))
            cur_label, start = None, None
        elif prefix == 'B':
            if cur_label is not None and start is not None:
                res.append(create_span(text[start:idx], start, idx, cur_label))
            cur_label, start = label, idx
        elif prefix == 'I':
            continue
        elif prefix == 'E':
            if cur_label is not None and start is not None:
                res.append(create_span(
                    text[start:idx+1], start, idx+1, cur_label))
            cur_label, start = None, None
    if cur_label is not None and start is not None:
        res.append(create_span(text[start:], start, len(text), cur_label))
    return res


def get_custom_objects():
    custom_objects = {}
    custom_objects.update(layers.get_module_objects())
    # custom_objects.update(losses.get_module_objects())
    # custom_objects.update(metrics.get_module_objects())
    return custom_objects


# def create_train_test_datasets(data_handler: DataHandler,
#                                train_path: str,
#                                test_path: str = None, test_size: float = 0.1):
#     if not test_path and not test_size:
#         raise ValueError("test_path and test_size cannot both be None")
#     if test_path:
#         train_dataset = data_handler.create_dataset_from_path(train_path)
#         test_dataset = data_handler.create_dataset_from_path(test_path)
#     else:
#         dataset = data_handler.create_dataset_from_path(train_path)
#         train_examples, test_examples = train_test_split(
#             dataset.examples, test_size=test_size)
#         train_dataset = Dataset(train_examples, dataset.fields)
#         test_dataset = Dataset(test_examples, dataset.fields)
#     return train_dataset, test_dataset
