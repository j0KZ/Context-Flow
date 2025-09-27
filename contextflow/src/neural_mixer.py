"""
Lightweight neural mixer for context predictions
Fast 2-layer network with on-the-fly training
"""

import numpy as np
from typing import List, Tuple, Optional
from collections import deque

class FastNeuralMixer:
    """
    Lightweight neural network for mixing context predictions
    Optimized for speed with minimal parameters (KB not GB)
    """

    def __init__(self, input_size: int = 16, hidden_size: int = 32, output_size: int = 256):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        self.w1 = np.random.randn(hidden_size, input_size).astype(np.float32) * 0.1
        self.b1 = np.zeros(hidden_size, dtype=np.float32)
        self.w2 = np.random.randn(output_size, hidden_size).astype(np.float32) * 0.1
        self.b2 = np.zeros(output_size, dtype=np.float32)

        self.learning_rate = 0.001
        self.momentum = 0.9

        self.v_w1 = np.zeros_like(self.w1)
        self.v_b1 = np.zeros_like(self.b1)
        self.v_w2 = np.zeros_like(self.w2)
        self.v_b2 = np.zeros_like(self.b2)

        self.history = deque(maxlen=100)
        self.cache = {}
        self.training_enabled = True

    def forward(self, inputs: np.ndarray) -> np.ndarray:
        """
        Fast forward pass with caching

        Args:
            inputs: Context features (input_size,)

        Returns:
            Probability distribution (256,)
        """
        cache_key = inputs.tobytes()
        if cache_key in self.cache:
            return self.cache[cache_key]

        z1 = np.dot(self.w1, inputs) + self.b1
        a1 = self._fast_relu(z1)

        z2 = np.dot(self.w2, a1) + self.b2

        output = self._fast_softmax(z2)

        self.cache[cache_key] = output

        if len(self.cache) > 10000:
            self.cache.clear()

        return output

    def _fast_relu(self, x: np.ndarray) -> np.ndarray:
        """Fast ReLU activation"""
        return np.maximum(0, x)

    def _fast_softmax(self, x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax"""
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    def train_step(self, inputs: np.ndarray, target: int, prediction: np.ndarray):
        """
        Single training step with backpropagation

        Args:
            inputs: Context features
            target: Actual next byte
            prediction: Current prediction
        """
        if not self.training_enabled:
            return

        error = -np.log(np.maximum(prediction[target], 1e-10))
        self.history.append(error)

        if len(self.history) < 10:
            return

        y = np.zeros(self.output_size, dtype=np.float32)
        y[target] = 1.0

        z1 = np.dot(self.w1, inputs) + self.b1
        a1 = self._fast_relu(z1)
        z2 = np.dot(self.w2, a1) + self.b2
        a2 = self._fast_softmax(z2)

        d2 = (a2 - y) * self.learning_rate
        dw2 = np.outer(d2, a1)
        db2 = d2

        d1 = np.dot(self.w2.T, d2)
        d1[z1 <= 0] = 0
        dw1 = np.outer(d1, inputs)
        db1 = d1

        self.v_w2 = self.momentum * self.v_w2 - dw2
        self.v_b2 = self.momentum * self.v_b2 - db2
        self.v_w1 = self.momentum * self.v_w1 - dw1
        self.v_b1 = self.momentum * self.v_b1 - db1

        self.w2 += self.v_w2
        self.b2 += self.v_b2
        self.w1 += self.v_w1
        self.b1 += self.v_b1

        self.cache.clear()

    def adapt_learning_rate(self):
        """Adapt learning rate based on recent performance"""
        if len(self.history) >= 50:
            recent_errors = list(self.history)[-50:]
            if np.mean(recent_errors[-10:]) > np.mean(recent_errors[-50:-40]):
                self.learning_rate *= 0.95
            else:
                self.learning_rate = min(self.learning_rate * 1.01, 0.01)

    def reset_if_needed(self):
        """Reset network if performance degrades significantly"""
        if len(self.history) >= 100:
            recent = np.mean(list(self.history)[-20:])
            older = np.mean(list(self.history)[-100:-80])

            if recent > older * 2:
                self.__init__(self.input_size, self.hidden_size, self.output_size)


class ContextMixer:
    """
    Mix multiple context predictions using neural network
    """

    def __init__(self, num_contexts: int = 8, fast_mode: bool = False):
        self.num_contexts = num_contexts
        self.fast_mode = fast_mode

        if not fast_mode:
            self.neural_mixer = FastNeuralMixer(
                input_size=num_contexts * 2,
                hidden_size=32,
                output_size=256
            )
        else:
            self.neural_mixer = None

        self.context_weights = np.ones(num_contexts) / num_contexts
        self.context_errors = deque(maxlen=1000)

    def mix_predictions(self,
                       context_predictions: List[np.ndarray],
                       context_confidences: List[float]) -> np.ndarray:
        """
        Mix multiple context predictions

        Args:
            context_predictions: List of probability distributions from contexts
            context_confidences: Confidence scores for each context

        Returns:
            Mixed probability distribution
        """
        if self.fast_mode or self.neural_mixer is None:
            return self._weighted_mix(context_predictions, context_confidences)

        features = self._prepare_features(context_predictions, context_confidences)
        mixed = self.neural_mixer.forward(features)

        mixed = 0.7 * mixed + 0.3 * self._weighted_mix(context_predictions, context_confidences)

        return mixed

    def _prepare_features(self,
                         predictions: List[np.ndarray],
                         confidences: List[float]) -> np.ndarray:
        """Prepare input features for neural mixer"""
        features = []

        for i, (pred, conf) in enumerate(zip(predictions, confidences)):
            if i >= self.num_contexts:
                break

            top_prob = np.max(pred)
            entropy = -np.sum(pred * np.log2(np.maximum(pred, 1e-10)))

            features.extend([top_prob, entropy])

        while len(features) < self.num_contexts * 2:
            features.extend([0.0, 0.0])

        return np.array(features[:self.num_contexts * 2], dtype=np.float32)

    def _weighted_mix(self,
                     predictions: List[np.ndarray],
                     confidences: List[float]) -> np.ndarray:
        """Simple weighted mixing fallback"""
        mixed = np.zeros(256, dtype=np.float32)

        total_weight = 0.0
        for i, (pred, conf) in enumerate(zip(predictions, confidences)):
            if i >= len(self.context_weights):
                break

            weight = self.context_weights[i] * (conf + 0.01)
            mixed += pred * weight
            total_weight += weight

        if total_weight > 0:
            mixed /= total_weight
        else:
            mixed = np.ones(256) / 256

        return mixed

    def update(self,
              predictions: List[np.ndarray],
              confidences: List[float],
              actual_byte: int):
        """Update mixer with actual outcome"""
        if self.neural_mixer and not self.fast_mode:
            features = self._prepare_features(predictions, confidences)
            mixed = self.neural_mixer.forward(features)
            self.neural_mixer.train_step(features, actual_byte, mixed)

        for i, pred in enumerate(predictions[:len(self.context_weights)]):
            error = -np.log(np.maximum(pred[actual_byte], 1e-10))
            self.context_errors.append((i, error))

        if len(self.context_errors) >= 100:
            self._update_weights()

    def _update_weights(self):
        """Update context weights based on performance"""
        errors_by_context = [[] for _ in range(len(self.context_weights))]

        for ctx_idx, error in list(self.context_errors)[-100:]:
            if ctx_idx < len(errors_by_context):
                errors_by_context[ctx_idx].append(error)

        for i, errors in enumerate(errors_by_context):
            if errors:
                avg_error = np.mean(errors)
                self.context_weights[i] *= np.exp(-avg_error * 0.1)

        self.context_weights /= np.sum(self.context_weights)
        self.context_weights = np.clip(self.context_weights, 0.01, 1.0)

        if self.neural_mixer:
            self.neural_mixer.adapt_learning_rate()


class AdaptiveMixer:
    """
    Adaptive mixer that adjusts strategy based on data type
    """

    def __init__(self):
        self.text_mixer = ContextMixer(num_contexts=6, fast_mode=False)
        self.code_mixer = ContextMixer(num_contexts=8, fast_mode=False)
        self.binary_mixer = ContextMixer(num_contexts=4, fast_mode=True)
        self.json_mixer = ContextMixer(num_contexts=6, fast_mode=False)

    def get_mixer(self, data_type: str) -> ContextMixer:
        """Get appropriate mixer for data type"""
        if data_type == 'text':
            return self.text_mixer
        elif data_type == 'code':
            return self.code_mixer
        elif data_type in ['json', 'xml', 'csv']:
            return self.json_mixer
        elif data_type == 'binary':
            return self.binary_mixer
        else:
            return self.binary_mixer

    def mix(self,
           predictions: List[np.ndarray],
           confidences: List[float],
           data_type: str) -> np.ndarray:
        """Mix predictions using appropriate mixer"""
        mixer = self.get_mixer(data_type)
        return mixer.mix_predictions(predictions, confidences)

    def update(self,
              predictions: List[np.ndarray],
              confidences: List[float],
              actual_byte: int,
              data_type: str):
        """Update appropriate mixer"""
        mixer = self.get_mixer(data_type)
        mixer.update(predictions, confidences, actual_byte)