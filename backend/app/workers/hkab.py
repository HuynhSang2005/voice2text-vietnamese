import os
import sys
import time
import numpy as np

from app.workers.base import BaseWorker
from app.core.config import settings

# Constants for HKAB model
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
N_MELS = 80
RNNT_BLANK = 1024
ATTENTION_CONTEXT_SIZE = [80, 3]
N_STATE = 768
TOKENIZER_MODEL_PATH = "utils/tokenizer_spe_bpe_v1024_pad/tokenizer.model"


class HKABWorker(BaseWorker):
    """Worker for HKAB RNN-Transducer model using ONNX Runtime.
    
    HKAB is a streaming RNN-T model that produces incremental results.
    To avoid flooding the client with duplicate results, we only send updates
    when the transcription text actually changes.
    """
    
    def load_model(self):
        import sentencepiece as spm
        import onnxruntime as ort
        
        self.logger.info("Loading HKAB ONNX models...")
        
        # Get model directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        hkab_repo_path = os.path.join(base_dir, settings.MODEL_STORAGE_PATH, "hkab")
        
        # Add to path for imports if needed
        if hkab_repo_path not in sys.path:
            sys.path.insert(0, hkab_repo_path)
        
        onnx_dir = os.path.join(hkab_repo_path, "onnx")
        encoder_path = os.path.join(onnx_dir, "encoder-infer.quant.onnx")
        decoder_path = os.path.join(onnx_dir, "decoder-infer.quant.onnx")
        jointer_path = os.path.join(onnx_dir, "jointer-infer.quant.onnx")
        
        if not os.path.exists(encoder_path):
            raise FileNotFoundError(f"ONNX models not found at {onnx_dir}")
            
        # Configure ONNX Runtime
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 2
        sess_options.inter_op_num_threads = 1
        
        self.encoder_sess = ort.InferenceSession(encoder_path, sess_options)
        self.decoder_sess = ort.InferenceSession(decoder_path, sess_options)
        self.jointer_sess = ort.InferenceSession(jointer_path, sess_options)
        
        # Load tokenizer
        tok_path = os.path.join(hkab_repo_path, TOKENIZER_MODEL_PATH)
        self.tokenizer = spm.SentencePieceProcessor(model_file=tok_path)
        
        # Cache input names
        self.enc_input_names = [i.name for i in self.encoder_sess.get_inputs()]
        self.dec_input_names = [i.name for i in self.decoder_sess.get_inputs()]
        self.joint_input_names = [i.name for i in self.jointer_sess.get_inputs()]
        
        # Initialize state
        self._reset_state()
        
        self.logger.info("HKAB ONNX models loaded successfully")

    def _reset_state(self):
        """Reset model state for new session."""
        self.audio_cache = np.zeros((1, N_FFT - HOP_LENGTH), dtype=np.float32)
        self.conv1_cache = np.zeros((1, 80, 1), dtype=np.float32)
        self.conv2_cache = np.zeros((1, 768, 1), dtype=np.float32)
        self.conv3_cache = np.zeros((1, 768, 1), dtype=np.float32)
        
        self.k_cache = np.zeros((12, 1, ATTENTION_CONTEXT_SIZE[0], 768), dtype=np.float32)
        self.v_cache = np.zeros((12, 1, ATTENTION_CONTEXT_SIZE[0], 768), dtype=np.float32)
        self.cache_len = np.zeros((1,), dtype=np.int32)
        
        self.h_n = np.zeros((1, 1, 768), dtype=np.float32)
        self.token = np.array([[RNNT_BLANK]], dtype=np.int64)
        
        self.seq_ids = []
        self.input_buffer = np.array([], dtype=np.float32)
        self.last_text = ""  # Track last sent text for deduplication

    def _get_input_name(self, names: list, base: str) -> str:
        """Find matching input name (handles ONNX name suffixes)."""
        for n in names:
            if n == base or n.startswith(base + "."):
                return n
        return base

    def process(self, item):
        if not hasattr(self, 'encoder_sess'):
            return

        force_output = False
        
        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                self.logger.debug("Resetting state for new session")
                self._reset_state()
                if not audio_data:
                    return
            if item.get("flush"):
                # Force output remaining result and reset state
                self.logger.info("Flush signal received - outputting final result")
                force_output = True
        else:
            audio_data = item

        if audio_data:
            # Start timing for latency measurement
            start_time = time.perf_counter()
            
            # Convert bytes to float32
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            self.input_buffer = np.concatenate((self.input_buffer, samples))
            
            # Process in chunks of stride (5120 samples)
            stride = HOP_LENGTH * 32  # 5120
            
            while len(self.input_buffer) >= stride:
                chunk = self.input_buffer[:stride]
                self.input_buffer = self.input_buffer[stride:]
                
                audio_chunk_in = np.expand_dims(chunk, 0)
                
                # Run Encoder
                enc_inputs = {
                    self._get_input_name(self.enc_input_names, "audio_chunk"): audio_chunk_in,
                    self._get_input_name(self.enc_input_names, "audio_cache"): self.audio_cache,
                    self._get_input_name(self.enc_input_names, "conv1_cache"): self.conv1_cache,
                    self._get_input_name(self.enc_input_names, "conv2_cache"): self.conv2_cache,
                    self._get_input_name(self.enc_input_names, "conv3_cache"): self.conv3_cache,
                    self._get_input_name(self.enc_input_names, "k_cache"): self.k_cache,
                    self._get_input_name(self.enc_input_names, "v_cache"): self.v_cache,
                    self._get_input_name(self.enc_input_names, "cache_len"): self.cache_len
                }
                
                enc_out_list = self.encoder_sess.run(None, enc_inputs)
                
                # Update caches
                self.enc_out = enc_out_list[0]
                self.audio_cache = enc_out_list[1]
                self.conv1_cache = enc_out_list[2]
                self.conv2_cache = enc_out_list[3]
                self.conv3_cache = enc_out_list[4]
                self.k_cache = enc_out_list[5]
                self.v_cache = enc_out_list[6]
                self.cache_len = enc_out_list[7]
                
                # Run Decoder/Jointer (Greedy Search)
                for time_idx in range(self.enc_out.shape[1]):
                    current_seq_enc_out = self.enc_out[:, time_idx, :].reshape(1, 1, N_STATE)
                    
                    not_blank = True
                    symbols_added = 0
                    
                    while not_blank and symbols_added < 3:
                        # Decoder
                        dec_inputs = {
                            self._get_input_name(self.dec_input_names, "token"): self.token,
                            self._get_input_name(self.dec_input_names, "h_n"): self.h_n
                        }
                        
                        dec_out_list = self.decoder_sess.run(None, dec_inputs)
                        dec = dec_out_list[0]
                        new_h_n = dec_out_list[1]
                        
                        # Jointer
                        joint_inputs = {
                            self._get_input_name(self.joint_input_names, "enc"): current_seq_enc_out,
                            self._get_input_name(self.joint_input_names, "dec"): dec
                        }
                        
                        logits = self.jointer_sess.run(None, joint_inputs)[0]
                        new_token = int(logits.argmax())
                        
                        if new_token == RNNT_BLANK:
                            not_blank = False
                        else:
                            symbols_added += 1
                            self.token = np.array([[new_token]], dtype=np.int64)
                            self.h_n = new_h_n
                            self.seq_ids.append(new_token)
                            
            # Send partial result only if text has changed (deduplication)
            if self.seq_ids:
                current_text = self.tokenizer.decode(self.seq_ids)
                if current_text and current_text != self.last_text:
                    self.last_text = current_text
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    self.output_queue.put({
                        "text": current_text,
                        "is_final": False,
                        "model": "hkab",
                        "workflow_type": "streaming",  # Streaming = text contains full transcription
                        "latency_ms": round(latency_ms, 2)
                    })
        
        # Handle flush: output final result and reset state
        if force_output and self.seq_ids:
            current_text = self.tokenizer.decode(self.seq_ids)
            self.output_queue.put({
                "text": current_text,
                "is_final": True,  # Mark as final on flush
                "model": "hkab",
                "workflow_type": "streaming",  # Streaming = text contains full transcription
                "latency_ms": 0
            })
            self.logger.info(f"Flush output: '{current_text[:50]}...'")
            
            # Reset state to prevent accumulation in next session
            self._reset_state()
            self.logger.debug("State reset after flush")
