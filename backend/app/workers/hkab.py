import os
import sys
import numpy as np
import sentencepiece as spm
import onnxruntime as ort
from app.workers.base import BaseWorker

# Add HKAB repo to sys.path to import constants if needed (for N_FFT etc)
hkab_repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models_storage/hkab"))
if hkab_repo_path not in sys.path:
    sys.path.insert(0, hkab_repo_path)

# Constants (Hardcoded to avoid import issues and match export script)
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
N_MELS = 80
RNNT_BLANK = 1024 # Corrected from constants.py
ATTENTION_CONTEXT_SIZE = [80, 3] # Corrected from constants.py
N_STATE = 768 # Corrected based on runtime shape (768)
# TOKENIZER_MODEL_PATH = "bpe.model" # OLD
TOKENIZER_MODEL_PATH = "utils/tokenizer_spe_bpe_v1024_pad/tokenizer.model" # Correct path from constants.py

class HKABWorker(BaseWorker):
    def load_model(self):
        print("[HKABWorker] Loading ONNX models...")
        self.device = "cpu"
        
        onnx_dir = os.path.join(hkab_repo_path, "onnx")
        encoder_path = os.path.join(onnx_dir, "encoder-infer.quant.onnx")
        decoder_path = os.path.join(onnx_dir, "decoder-infer.quant.onnx")
        jointer_path = os.path.join(onnx_dir, "jointer-infer.quant.onnx")
        
        if not os.path.exists(encoder_path):
            raise FileNotFoundError(f"ONNX models not found at {onnx_dir}. Please run export_hkab_onnx.py first.")
            
        # Load ONNX Sessions
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 1 # Optimize for latency
        sess_options.inter_op_num_threads = 1
        
        self.encoder_sess = ort.InferenceSession(encoder_path, sess_options)
        self.decoder_sess = ort.InferenceSession(decoder_path, sess_options)
        self.jointer_sess = ort.InferenceSession(jointer_path, sess_options)
        
        # Tokenizer
        tok_path = os.path.join(hkab_repo_path, TOKENIZER_MODEL_PATH)
        self.tokenizer = spm.SentencePieceProcessor(model_file=tok_path)
        
        # Initialize State
        self._reset_state()
        
        # Input Buffer for accumulating chunks to match stride
        self.input_buffer = np.array([], dtype=np.float32)
        
        print("[HKABWorker] ONNX models loaded successfully.")

    def _reset_state(self):
        # Initialize caches (numpy)
        self.audio_cache = np.zeros((1, N_FFT - HOP_LENGTH), dtype=np.float32)
        self.conv1_cache = np.zeros((1, 80, 1), dtype=np.float32)
        self.conv2_cache = np.zeros((1, 768, 1), dtype=np.float32)
        self.conv3_cache = np.zeros((1, 768, 1), dtype=np.float32)
        
        self.k_cache = np.zeros((12, 1, ATTENTION_CONTEXT_SIZE[0], 768), dtype=np.float32)
        self.v_cache = np.zeros((12, 1, ATTENTION_CONTEXT_SIZE[0], 768), dtype=np.float32)
        self.cache_len = np.zeros((1,), dtype=np.int32) # int32 for ONNX
        
        # Decoder state
        self.h_n = np.zeros((1, 1, 768), dtype=np.float32)
        self.token = np.array([[RNNT_BLANK]], dtype=np.int64)
        
        self.seq_ids = []
        self.input_buffer = np.array([], dtype=np.float32)

    def process(self, item):
        if not hasattr(self, 'encoder_sess'):
            return

        if isinstance(item, dict):
            audio_data = item.get("audio")
            if item.get("reset"):
                print("[HKABWorker] Resetting state")
                self._reset_state()
                if not audio_data:
                    return
        else:
            audio_data = item

        if audio_data:
            # Convert bytes to float32
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Append to input buffer
            self.input_buffer = np.concatenate((self.input_buffer, samples))
            
            # Stride logic from export.ipynb
            # stride = HOP_LENGTH * 31 + N_FFT - (N_FFT - HOP_LENGTH) = 160*31 + 400 - 240 = 4960 + 160 = 5120?
            # Wait, N_FFT - (N_FFT - HOP_LENGTH) = HOP_LENGTH.
            # So stride = HOP_LENGTH * 31 + HOP_LENGTH = HOP_LENGTH * 32 = 160 * 32 = 5120.
            stride = 5120
            
            # We process in chunks of `stride`
            # But we need to handle the case where we have enough data
            
            # Note: The notebook logic:
            # audio_chunk = audio[:, i:i+stride]
            # if audio_chunk < stride: pad...
            
            # Here we want to process ONLY if we have enough data to fill a stride, 
            # OR if we want to force process (but we don't know if it's end).
            # For streaming, we usually wait for stride.
            
            while len(self.input_buffer) >= stride:
                chunk = self.input_buffer[:stride]
                self.input_buffer = self.input_buffer[stride:]
                
                # Prepare input for ONNX
                # Shape: (1, stride)
                audio_chunk_in = np.expand_dims(chunk, 0)
                
                # Run Encoder
                enc_inputs = {
                    "audio_chunk": audio_chunk_in,
                    "audio_cache": self.audio_cache,
                    "conv1_cache": self.conv1_cache,
                    "conv2_cache": self.conv2_cache,
                    "conv3_cache": self.conv3_cache,
                    "k_cache": self.k_cache,
                    "v_cache": self.v_cache,
                    "cache_len": self.cache_len
                }
                
                # ONNX Runtime expects specific input names matching export
                # In export.ipynb: input_names=["audio_chunk", "audio_cache", ...]
                # But in inference cell: "audio_cache.1", "conv1_cache.1" etc.
                # This is because ONNX export might rename inputs if they are not unique or something.
                # BUT I specified input_names in export call!
                # So they SHOULD be "audio_cache", etc.
                # The notebook inference cell uses "audio_cache.1" which is suspicious.
                # Maybe because it loaded "encoder-infer.onnx" which was preprocessed?
                # I should check the input names from the session.
                
                # Let's inspect session input names dynamically to be safe.
                if not hasattr(self, 'enc_input_names'):
                    self.enc_input_names = [i.name for i in self.encoder_sess.get_inputs()]
                    # print(f"Encoder inputs: {self.enc_input_names}")
                    
                # Map inputs based on order or name
                # The order in export was: audio_chunk, audio_cache, conv1, conv2, conv3, k, v, cache_len
                # Let's assume names match what I passed to export, OR I map by order.
                # Mapping by name is safer if names are preserved.
                # If names have suffix like ".1", I need to handle it.
                
                # Construct dict
                ort_inputs = {}
                # Helper to find matching input name
                def get_name(base):
                    for n in self.enc_input_names:
                        if n == base or n.startswith(base + "."):
                            return n
                    return base # Fallback
                
                ort_inputs[get_name("audio_chunk")] = audio_chunk_in
                ort_inputs[get_name("audio_cache")] = self.audio_cache
                ort_inputs[get_name("conv1_cache")] = self.conv1_cache
                ort_inputs[get_name("conv2_cache")] = self.conv2_cache
                ort_inputs[get_name("conv3_cache")] = self.conv3_cache
                ort_inputs[get_name("k_cache")] = self.k_cache
                ort_inputs[get_name("v_cache")] = self.v_cache
                ort_inputs[get_name("cache_len")] = self.cache_len
                
                enc_out_list = self.encoder_sess.run(None, ort_inputs)
                
                # Unpack outputs
                # Order: enc_out, audio_cache, conv1, conv2, conv3, k, v, cache_len
                self.enc_out = enc_out_list[0]
                self.audio_cache = enc_out_list[1]
                self.conv1_cache = enc_out_list[2]
                self.conv2_cache = enc_out_list[3]
                self.conv3_cache = enc_out_list[4]
                self.k_cache = enc_out_list[5]
                self.v_cache = enc_out_list[6]
                self.cache_len = enc_out_list[7]
                
                # Run Decoder/Jointer (Greedy Search)
                # enc_out shape: (1, T, D)
                
                for time_idx in range(self.enc_out.shape[1]):
                    current_seq_enc_out = self.enc_out[:, time_idx, :].reshape(1, 1, N_STATE) # Use N_STATE (768)
                    
                    not_blank = True
                    # In notebook it says 512.
                    # Let's trust the shape returned.
                    
                    not_blank = True
                    symbols_added = 0
                    
                    while not_blank and symbols_added < 3: # max_symbols=3
                        # Decoder
                        if not hasattr(self, 'dec_input_names'):
                            self.dec_input_names = [i.name for i in self.decoder_sess.get_inputs()]
                            
                        dec_inputs = {}
                        def get_dec_name(base):
                            for n in self.dec_input_names:
                                if n == base or n.startswith(base + "."): return n
                            return base
                            
                        dec_inputs[get_dec_name("token")] = self.token
                        dec_inputs[get_dec_name("h_n")] = self.h_n
                        
                        dec_out_list = self.decoder_sess.run(None, dec_inputs)
                        dec = dec_out_list[0]
                        new_h_n = dec_out_list[1]
                        
                        # Jointer
                        if not hasattr(self, 'joint_input_names'):
                            self.joint_input_names = [i.name for i in self.jointer_sess.get_inputs()]
                            
                        joint_inputs = {}
                        def get_joint_name(base):
                            for n in self.joint_input_names:
                                if n == base or n.startswith(base + "."): return n
                            return base
                            
                        joint_inputs[get_joint_name("enc")] = current_seq_enc_out
                        joint_inputs[get_joint_name("dec")] = dec
                        
                        logits = self.jointer_sess.run(None, joint_inputs)[0]
                        
                        new_token = int(logits.argmax())
                        
                        if new_token == RNNT_BLANK:
                            not_blank = False
                        else:
                            symbols_added += 1
                            self.token = np.array([[new_token]], dtype=np.int64)
                            self.h_n = new_h_n
                            self.seq_ids.append(new_token)
                            
            # Send partial result
            if self.seq_ids:
                current_text = self.tokenizer.decode(self.seq_ids)
                self.output_queue.put({
                    "text": current_text,
                    "is_final": False,
                    "model": "hkab"
                })
