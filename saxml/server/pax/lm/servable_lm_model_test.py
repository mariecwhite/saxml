# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for servable_lm_model."""

import os

from absl import flags
from absl import logging
from absl.testing import absltest
import jax
import numpy as np
from paxml import checkpoints
from paxml.tasks.lm.params import lm_cloud
from praxis import decoder_hparams
from praxis import pax_fiddle
from praxis import py_utils
from saxml.server.pax.lm import lm_tokenizer
from saxml.server.pax.lm import servable_lm_common
from saxml.server.pax.lm import servable_lm_model
from saxml.server.pax.lm.params.lm_cloud import BaseLLaMA


class LmCloudSpmdSmall(
    lm_cloud.LmCloudSpmd, servable_lm_model.ServableLMModelParams
):
  """SPMD model with small params."""

  NUM_LAYERS = 3
  MODEL_DIMS = 128
  DIMS_PER_HEAD = 32
  HIDDEN_DIMS = MODEL_DIMS * 4

  ICI_MESH_SHAPE = [1, 1, 1]

  @classmethod
  def serving_mesh_shape(cls):
    return cls.ICI_MESH_SHAPE

  def serving_tokenizer(self):
    spm_model = os.path.join(
        flags.FLAGS.test_srcdir,
        'google3/third_party/py/saxml/server/pax/lm/test_data',
        'test_model.model',
    )
    return pax_fiddle.Config(
        lm_tokenizer.LMTokenizer,
        spm_model=spm_model,
        target_sos_id=0,
        target_eos_id=1,
    )

  def score(self):
    return servable_lm_model.ScoreHParams(
        batch_size=4, max_input_seq_len=8, max_suffix_seq_len=8
    )

  def input_for_model_init(self):
    batch_size, seq_len = 4, 16
    targets = np.ones([batch_size, seq_len], dtype=np.int32)
    input_batch = py_utils.NestedMap()
    input_batch.ids = targets
    input_batch.paddings = np.zeros_like(targets)
    input_batch.weights = np.ones_like(targets)
    input_batch.labels = targets
    input_batch.segment_ids = targets
    input_batch.segment_pos = np.tile(
        np.arange(0, seq_len)[np.newaxis, :], [batch_size, 1]
    )
    return input_batch

  def task(self):
    task_p = super().task()
    task_p.model.lm_tpl.packed_input = False
    return task_p


class ServableLMModelTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self._prng_key = jax.random.PRNGKey(1234)

  def test_load_model_score(self):
    model = servable_lm_model.ServableLMModel(
        LmCloudSpmdSmall(),
        primary_process_id=0,
        ckpt_type=checkpoints.CheckpointType.GDA,
        test_mode=True,
    )
    model.load(checkpoint_path=None, prng_key=self._prng_key)
    score_result = model.method(servable_lm_model.LMMethodName.SCORE).compute(
        [('k', ['a b']), ('k', ['b d e'])]
    )
    logging.info('score_result: %s', score_result)
    self.assertLen(score_result, 2)
    score_result = model.method(servable_lm_model.LMMethodName.SCORE).compute(
        [('p', ['a b c']), ('p', ['d e f']), ('p', ['g h i'])]
    )
    logging.info('score_result: %s', score_result)
    self.assertLen(score_result, 3)


class LLaMASmall(BaseLLaMA, servable_lm_model.ServableLMModelParams):
  """LLaMA model with small params."""

  NUM_LAYERS = 2
  VOCAB_SIZE = 64
  DIMS_PER_HEAD = 4
  NUM_HEADS = 2
  MODEL_DIMS = 8
  HIDDEN_DIMS = MODEL_DIMS * 4

  ICI_MESH_SHAPE = [1, 1, 1]

  BATCH_SIZE = 3

  def serving_tokenizer(self):
    spm_model = '/cns/mf-d/home/huangyp/ulm/pax-llama/tokenizer.model'
    return pax_fiddle.Config(
        lm_tokenizer.LMTokenizer,
        spm_model=spm_model,
        target_sos_id=0,
        target_eos_id=1,
    )

  def input_for_model_init(self):
    batch_size, seq_len = 3, 16
    targets = np.ones([batch_size, seq_len], dtype=np.int32)
    input_batch = py_utils.NestedMap()
    input_batch.ids = targets
    input_batch.paddings = np.zeros_like(targets)
    input_batch.weights = np.ones_like(targets)
    input_batch.labels = targets
    input_batch.segment_ids = targets
    input_batch.segment_pos = np.tile(
        np.arange(0, seq_len)[np.newaxis, :], [batch_size, 1]
    )
    return input_batch

  def generate(self):
    params = servable_lm_model.DecodeHParams(
        max_input_seq_len=8, batch_size=self.BATCH_SIZE
    )
    decoder_params = decoder_hparams.GreedyDecoderHParams()
    decoder_params.max_decode_steps = 3
    # seqlen = max_input_seq_len + max_decode_steps
    decoder_params.seqlen = 11
    decoder_params.fprop_for_prefix = True
    params.decoder = decoder_params
    return params

  def score(self):
    """Returns the params for the score method."""
    return None

  def generate_stream(self):
    """Returns the params for the decode method."""
    return None

  def task(self):
    task_p = super().task()
    task_p.model.lm_tpl.packed_input = False
    task_p.model.lm_tpl.stacked_transformer_tpl.transformer_layer_params_tpl.tr_atten_tpl.consolidate_rope_key_state = (
        True
    )
    return task_p


class LLaMASmallWithContinuousBatching(
    LLaMASmall, servable_lm_model.ServableLMModelParams
):
  """LLaMA model with small params and Continuous Batching enabled."""

  NUM_CACHE_SLOTS = 2

  @classmethod
  def serving_mesh_shape(cls):
    return cls.ICI_MESH_SHAPE

  def generate(self):
    params = servable_lm_model.DecodeHParams(max_input_seq_len=8)
    decoder_params = decoder_hparams.GreedyDecoderHParams()
    decoder_params.num_cache_slots = 2
    decoder_params.max_decode_steps = 3
    # seqlen = max_input_seq_len + max_decode_steps
    decoder_params.seqlen = 11
    decoder_params.fprop_for_prefix = True
    params.decoder = decoder_params
    return params


class ServableLMModelContinuousBatchingTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self._prng_key = jax.random.PRNGKey(1234)

  def _run_prefill(self, method, slots_in_use, steps, inputs):
    slot = np.argmin(slots_in_use)
    slots_in_use[slot] = 1
    steps[slot] = 1

    _, token, prefix_state = method.prefill(inputs)
    return token, prefix_state, slot

  def _run_generate(
      self, times, method, decoded_tokens, steps, slots_in_use, max_steps
  ):
    num_slots = len(slots_in_use)
    done = None
    logging.info('decoded_tokens before generate: %s', decoded_tokens)
    logging.info('current generate steps: %s', steps)
    logging.info('slots_in_use: %s', slots_in_use)
    for _ in range(times):
      token_batch = (
          decoded_tokens[np.arange(num_slots), steps - 1] * slots_in_use
      )
      token_batch = method.input_to_device_for_continuous_batching(
          token_batch,
          servable_lm_common.InputShapeInfo(batch_size=num_slots),
      )
      logging.info('token_batch for generate: %s', token_batch)
      scores, tokens, done = method.generate(token_batch)
      scores, tokens, done = method.output_to_host(
          (scores, tokens, done), unpadded_batch_size=num_slots
      )
      self.assertSequenceEqual(scores.shape, (num_slots,))
      self.assertSequenceEqual(tokens.shape, (num_slots,))
      self.assertSequenceEqual(done.shape, (num_slots,))

      decoded_tokens[np.arange(num_slots), steps] = tokens

      steps += slots_in_use
      done = np.logical_or(done * slots_in_use, steps >= max_steps)

    logging.info('done after generation: %s', done)
    logging.info('decoded_tokens after generation: %s', decoded_tokens)
    return decoded_tokens, done, steps

  # @TODO(@zhihaoshan): Enable the accuracy check after bug fixing.
  def test_continuous_batching(self):
    model = servable_lm_model.ServableLMModel(
        LLaMASmall(),
        primary_process_id=0,
        ckpt_type=checkpoints.CheckpointType.GDA,
        test_mode=True,
    )

    model_with_continuous_batching = servable_lm_model.ServableLMModel(
        LLaMASmallWithContinuousBatching(),
        primary_process_id=0,
        ckpt_type=checkpoints.CheckpointType.GDA,
        test_mode=True,
    )

    model.load(checkpoint_path=None, prng_key=self._prng_key)

    model_with_continuous_batching.load(
        checkpoint_path=None, prng_key=self._prng_key
    )

    method = model.method(servable_lm_model.LMMethodName.GENERATE)
    method_with_continuous_batching = model_with_continuous_batching.method(
        servable_lm_model.LMMethodName.GENERATE
    )
    num_devices = jax.device_count()
    input1 = ['Hello World']
    input2 = ['Today is a good day']
    input3 = ['My dog is cute']
    inputs = input1 + input2 + input3

    input1 = method.pre_processing(input1)
    input2 = method.pre_processing(input2)
    input3 = method.pre_processing(input3)
    inputs = method.pre_processing(inputs)
    inputs_unpadded_shape = servable_lm_common.InputShapeInfo(batch_size=3)
    inputs_padded_shape = servable_lm_common.InputShapeInfo(batch_size=3)

    # Run device_compute with static batching and inputs to get the expected
    # result.
    inputs = method.input_to_device(
        inputs, inputs_unpadded_shape, inputs_padded_shape
    )
    expected_outputs = method.device_compute(inputs, inputs_padded_shape)
    logging.info('expected_output from static batching: %s', expected_outputs)

    # Run continuous batching to verify the result.
    # The order will be (max decode step is 3 and max slots is 2):
    #   1. Run prefill for input1 and insert the KV Cache.
    #   2. Run generate for input1 for 1 more token.
    #   3. Run prefill for input2 and insert the KV Cache.
    #   4. Run generate for the input1 and input2 inside the slots.
    #   5. input1 is completed with 3 decode steps and the slot for it will be
    #   free.
    #   6. Run prefill for input3, insert the KV cache and run generate until
    #   input2 and input3 complete.
    #   There are total 3 prefill calls and 4 generate calls.
    input1 = (
        method_with_continuous_batching.input_to_device_for_continuous_batching(
            input1, servable_lm_common.InputShapeInfo(batch_size=1)
        )
    )
    self.assertSequenceEqual(
        input1.ids.shape,
        (num_devices, 1, method_with_continuous_batching.input_sequence_len),
    )

    num_slots = method_with_continuous_batching.num_cache_slots
    max_steps = method_with_continuous_batching.max_decode_steps
    decoded_tokens = np.zeros((num_slots, max_steps), dtype=np.int32)
    slots_in_use = np.zeros((num_slots), dtype=np.int32)
    steps = np.zeros((num_slots,), dtype=np.int32)

    # Run prefill for input1.
    token, prefix_state, slot = self._run_prefill(
        method_with_continuous_batching, slots_in_use, steps, input1
    )

    # Insert input1 KV cache.
    method_with_continuous_batching.insert(prefix_state, slot)
    decoded_tokens[slot][0] = np.array(token.addressable_data(0))

    # Run one time generate for input1.
    logging.info('1st generate for input1')
    decoded_tokens, done, steps = self._run_generate(
        1,
        method_with_continuous_batching,
        decoded_tokens,
        steps,
        slots_in_use,
        max_steps,
    )

    # Run prefill for input2.
    input2 = (
        method_with_continuous_batching.input_to_device_for_continuous_batching(
            input2, servable_lm_common.InputShapeInfo(batch_size=1)
        )
    )
    token, prefix_state, slot = self._run_prefill(
        method_with_continuous_batching, slots_in_use, steps, input2
    )
    logging.info('slots_in_use after prefill for input2: %s', slots_in_use)

    # Insert input2 KV cache.
    method_with_continuous_batching.insert(prefix_state, slot)
    decoded_tokens[slot][0] = np.array(token.addressable_data(0))

    # Run one time generate for input1 and input2.
    logging.info('2st generate for input1 and input2')
    decoded_tokens, done, steps = self._run_generate(
        1,
        method_with_continuous_batching,
        decoded_tokens,
        steps,
        slots_in_use,
        max_steps,
    )
    self.assertTrue(done[0])
    got_input1_res = np.array(decoded_tokens[0], copy=True)

    # Free up slot 0 used by the input1.
    logging.info('free up slot 0 for input1')
    decoded_tokens[done] = 0
    steps[done] = 0
    slots_in_use[done] = 0

    # Run prefill for input3.
    input3 = (
        method_with_continuous_batching.input_to_device_for_continuous_batching(
            input3, servable_lm_common.InputShapeInfo(batch_size=1)
        )
    )
    token, prefix_state, slot = self._run_prefill(
        method_with_continuous_batching, slots_in_use, steps, input3
    )
    logging.info('slots_in_use after prefill for input3: %s', slots_in_use)

    # Insert input3 KV cache.
    method_with_continuous_batching.insert(prefix_state, slot)
    decoded_tokens[slot][0] = np.array(token.addressable_data(0))

    # Run one time generate for input2 and input3.
    logging.info('3st generate for input2 and input3')
    decoded_tokens, done, steps = self._run_generate(
        1,
        method_with_continuous_batching,
        decoded_tokens,
        steps,
        slots_in_use,
        max_steps,
    )
    # Free up slot 1 used by the input2.
    logging.info('free up slot 1 for input2')
    self.assertTrue(done[1])
    got_input2_res = np.array(decoded_tokens[1], copy=True)
    decoded_tokens[done] = 0
    steps[done] = 0
    slots_in_use[done] = 0

    # Run one time generate for input3.
    logging.info('4th generate for and input3')
    decoded_tokens, done, steps = self._run_generate(
        1,
        method_with_continuous_batching,
        decoded_tokens,
        steps,
        slots_in_use,
        max_steps,
    )
    # Free up slot 0 used by the input3.
    self.assertTrue(done[0])
    got_input3_res = np.array(decoded_tokens[0], copy=True)
    decoded_tokens[done] = 0
    steps[done] = 0
    slots_in_use[done] = 0
    logging.info('expected output with prefix: %s', expected_outputs)
    logging.info('got decode res for input1: %s', got_input1_res)
    logging.info('got decode res for input2: %s', got_input2_res)
    logging.info('got decode res for input3: %s', got_input3_res)


if __name__ == '__main__':
  absltest.main()
