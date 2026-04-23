import os
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

import config


MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "all-MiniLM-L6-v2")
MAX_TOKENS = 128


def _mean_pool(last_hidden: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    mask = attention_mask.astype(np.float32)[..., None]
    summed = (last_hidden * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
    return summed / counts


def _l2_normalize(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.clip(norm, a_min=1e-12, a_max=None)


class IntentClassifier:
    def __init__(self, model_dir: str = MODEL_DIR):
        tok_path = os.path.join(model_dir, "tokenizer.json")
        onnx_path = os.path.join(model_dir, "model.onnx")
        self._tokenizer = Tokenizer.from_file(tok_path)
        self._tokenizer.enable_truncation(max_length=MAX_TOKENS)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(onnx_path, sess_options=so, providers=["CPUExecutionProvider"])
        self._input_names = {inp.name for inp in self._session.get_inputs()}
        self._cache: dict[str, np.ndarray] = {}

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        encs = self._tokenizer.encode_batch(texts)
        ids = np.array([e.ids for e in encs], dtype=np.int64)
        mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        outputs = self._session.run(None, feeds)
        last_hidden = outputs[0]
        pooled = _mean_pool(last_hidden, mask)
        return _l2_normalize(pooled).astype(np.float32)

    def prime(self, candidates: dict[str, list[str]]) -> None:
        self._cache.clear()
        for cmd_id, phrases in candidates.items():
            if not phrases:
                continue
            self._cache[cmd_id] = self.embed(list(phrases))

    def match(self, utterance: str, candidates: dict[str, list[str]]) -> dict:
        utterance = (utterance or "").strip()
        if not utterance:
            return {"cmd": "", "score": 0.0}
        for cmd_id, phrases in candidates.items():
            if cmd_id not in self._cache and phrases:
                self._cache[cmd_id] = self.embed(list(phrases))
        query = self.embed([utterance])[0]
        best_cmd = ""
        best_score = -1.0
        for cmd_id, mat in self._cache.items():
            sims = mat @ query
            top = float(sims.max()) if sims.size else -1.0
            if top > best_score:
                best_score = top
                best_cmd = cmd_id
        threshold = getattr(config, "INTENT_SIMILARITY_THRESHOLD", 0.45)
        if best_score < threshold:
            return {"cmd": "", "score": max(0.0, best_score)}
        return {"cmd": best_cmd, "score": max(0.0, best_score)}
