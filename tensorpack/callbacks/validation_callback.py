#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# File: validation_callback.py
# Author: Yuxin Wu <ppwwyyxx@gmail.com>

import tensorflow as tf
import itertools
from tqdm import tqdm

from ..utils import *
from ..utils.stat import *
from ..utils.summary import *
from .base import PeriodicCallback, Callback

__all__ = ['ValidationError']

class ValidationError(PeriodicCallback):
    running_graph = 'test'
    """
    Validate the accuracy for the given wrong and cost variable
    Use under the following setup:
        wrong_var: integer, number of failed samples in this batch
        ds: batched dataset
    """
    def __init__(self, ds, prefix,
                 period=1,
                 wrong_var_name='wrong:0',
                 cost_var_name='cost:0'):
        super(ValidationError, self).__init__(period)
        self.ds = ds
        self.prefix = prefix

        self.wrong_var_name = wrong_var_name
        self.cost_var_name = cost_var_name

    def get_tensor(self, name):
        return self.graph.get_tensor_by_name(name)

    def _before_train(self):
        self.input_vars = tf.get_collection(INPUT_VARS_KEY)
        self.wrong_var = self.get_tensor(self.wrong_var_name)
        self.cost_var = self.get_tensor(self.cost_var_name)
        self.writer = tf.get_collection(SUMMARY_WRITER_COLLECTION_KEY)[0]

    def _trigger(self):
        cnt = 0
        err_stat = Accuracy()
        cost_sum = 0
        with tqdm(total=self.ds.size()) as pbar:
            for dp in self.ds.get_data():
                feed = dict(itertools.izip(self.input_vars, dp))

                batch_size = dp[0].shape[0]   # assume batched input

                cnt += batch_size
                wrong, cost = self.sess.run(
                    [self.wrong_var, self.cost_var], feed_dict=feed)
                err_stat.feed(wrong, batch_size)
                # each batch might not have the same size in validation
                cost_sum += cost * batch_size
                pbar.update()

        cost_avg = cost_sum / cnt
        self.writer.add_summary(create_summary(
            '{}_error'.format(self.prefix), err_stat.accuracy), self.global_step)
        self.writer.add_summary(create_summary(
            '{}_cost'.format(self.prefix), cost_avg), self.global_step)
        logger.info("{}_cost: {:.4f}".format(self.prefix, cost_avg))
        logger.info("{}_error: {:.4f}".format(self.prefix, err_stat.accuracy))
