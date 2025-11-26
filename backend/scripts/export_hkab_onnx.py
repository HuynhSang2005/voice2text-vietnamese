import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import sentencepiece as spm
from huggingface_hub import hf_hub_download
from torch.fft import rfft as fft
from scipy.signal import check_COLA, get_window
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType
import subprocess

# Add HKAB repo to sys.path
hkab_repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models_storage/hkab"))
if hkab_repo_path not in sys.path:
    sys.path.insert(0, hkab_repo_path) # Insert at beginning to prioritize local modules

try:
    from models.encoder import AudioEncoder
    from models.decoder import Decoder
    from models.jointer import Jointer
    from constants import (
        SAMPLE_RATE, N_FFT, HOP_LENGTH, N_MELS, RNNT_BLANK, 
        VOCAB_SIZE, TOKENIZER_MODEL_PATH, ATTENTION_CONTEXT_SIZE,
        N_STATE, N_LAYER, N_HEAD
    )
except ImportError as e:
    print(f"Error importing HKAB modules: {e}")
    sys.exit(1)

DEVICE = 'cpu' # Export on CPU

# --- Helper Classes from export.ipynb ---

support_clp_op = True

class STFT(torch.nn.Module):
    def __init__(self, win_len=1024, win_hop=512, fft_len=1024,
                 enframe_mode='continue', win_type='hann',
                 win_sqrt=False, pad_center=True):
        super(STFT, self).__init__()
        self.win_len = win_len
        self.win_hop = win_hop
        self.fft_len = fft_len
        self.mode = enframe_mode
        self.win_type = win_type
        self.win_sqrt = win_sqrt
        self.pad_center = pad_center
        self.pad_amount = self.fft_len // 2

        en_k, fft_k, ifft_k, ola_k = self.__init_kernel__()
        self.register_buffer('en_k', en_k)
        self.register_buffer('fft_k', fft_k)
        self.register_buffer('ifft_k', ifft_k)
        self.register_buffer('ola_k', ola_k)

    def __init_kernel__(self):
        enframed_kernel = torch.eye(self.fft_len)[:, None, :]
        if support_clp_op:
            tmp = fft(torch.eye(self.fft_len))
            fft_kernel = torch.stack([tmp.real, tmp.imag], dim=2)
        else:
            fft_kernel = fft(torch.eye(self.fft_len), 1)
        if self.mode == 'break':
            enframed_kernel = torch.eye(self.win_len)[:, None, :]
            fft_kernel = fft_kernel[:self.win_len]
        fft_kernel = torch.cat(
            (fft_kernel[:, :, 0], fft_kernel[:, :, 1]), dim=1)
        ifft_kernel = torch.pinverse(fft_kernel)[:, None, :]
        window = get_window(self.win_type, self.win_len, fftbins=False)

        self.perfect_reconstruct = check_COLA(
            window,
            self.win_len,
            self.win_len-self.win_hop)
        window = torch.FloatTensor(window)
        if self.mode == 'continue':
            left_pad = (self.fft_len - self.win_len)//2
            right_pad = left_pad + (self.fft_len - self.win_len) % 2
            window = F.pad(window, (left_pad, right_pad))
        if self.win_sqrt:
            self.padded_window = window
            window = torch.sqrt(window)
        else:
            self.padded_window = window**2

        fft_kernel = fft_kernel.T * window
        ifft_kernel = ifft_kernel * window
        ola_kernel = torch.eye(self.fft_len)[:self.win_len, None, :]
        if self.mode == 'continue':
            ola_kernel = torch.eye(self.fft_len)[:, None, :self.fft_len]
        return enframed_kernel, fft_kernel, ifft_kernel, ola_kernel

    def transform(self, inputs, return_type='complex'):
        if inputs.dim() == 2:
            inputs = torch.unsqueeze(inputs, 1)
        self.num_samples = inputs.size(-1)
        if self.pad_center:
            inputs = F.pad(
                inputs, (self.pad_amount, self.pad_amount), mode='reflect')
        enframe_inputs = F.conv1d(inputs, self.en_k, stride=self.win_hop)
        outputs = torch.transpose(enframe_inputs, 1, 2)
        outputs = F.linear(outputs, self.fft_k)
        outputs = torch.transpose(outputs, 1, 2)
        dim = self.fft_len//2+1
        real = outputs[:, :dim, :]
        imag = outputs[:, dim:, :]
        if return_type == 'realimag':
            return real, imag
        elif return_type == 'complex':
            return torch.complex(real, imag)
        else:
            mags = torch.sqrt(real**2+imag**2)
            phase = torch.atan2(imag, real)
            return mags, phase

class WrapperPreprocessor(nn.Module):
    def __init__(self):
        super().__init__()
        self.stft = STFT(
            win_len=400, win_hop=160, fft_len=400,
            pad_center=False # For streaming
        )
        # Load mel filters using librosa
        import librosa
        filters = librosa.filters.mel(sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS)
        self.register_buffer('filters', torch.from_numpy(filters))
    
    def forward(self, audio_signal):
        mags, _ = self.stft.transform(audio_signal, return_type='magphase')
        mags = mags**2
        audio_signal = self.filters @ mags
        audio_signal = torch.clamp(audio_signal, min=1e-10).log10()
        audio_signal = (audio_signal + 4.0) / 4.0
        return audio_signal

class WrapperEncoderALiBi(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder.to(DEVICE)
        self.preprocessor = WrapperPreprocessor().to(DEVICE)

    def forward(self, 
                audio_chunk, audio_cache, 
                conv1_cache, conv2_cache, conv3_cache,
                k_cache, v_cache, cache_len):
        audio_chunk = torch.cat([audio_cache, audio_chunk], dim=1)
        audio_cache = audio_chunk[:, -(N_FFT - HOP_LENGTH):]

        x_chunk = self.preprocessor(audio_chunk)
        x_chunk = torch.cat([conv1_cache, x_chunk], dim=2)

        conv1_cache = x_chunk[:, :, -1].unsqueeze(2)
        x_chunk = F.gelu(self.encoder.conv1(x_chunk))

        x_chunk = torch.cat([conv2_cache, x_chunk], dim=2)
        conv2_cache = x_chunk[:, :, -1].unsqueeze(2)
        x_chunk = F.gelu(self.encoder.conv2(x_chunk))

        x_chunk = torch.cat([conv3_cache, x_chunk], dim=2)
        conv3_cache = x_chunk[:, :, -1].unsqueeze(2)
        x_chunk = F.gelu(self.encoder.conv3(x_chunk))

        x_chunk = x_chunk.permute(0, 2, 1)

        x_len = torch.tensor([ATTENTION_CONTEXT_SIZE[0] + ATTENTION_CONTEXT_SIZE[1] + 1]).to(DEVICE)
        offset = torch.neg(cache_len) + ATTENTION_CONTEXT_SIZE[0]

        attn_mask = self.encoder.form_attention_mask_for_streaming(ATTENTION_CONTEXT_SIZE, x_len, offset.to(DEVICE), DEVICE)
        attn_mask = attn_mask[:, :, ATTENTION_CONTEXT_SIZE[0]:, :]

        new_k_cache = []
        new_v_cache = []
        for i, block in enumerate(self.encoder.blocks):
            x_chunk, layer_k_cache, layer_v_cache = block(x_chunk, mask=attn_mask, k_cache=k_cache[i], v_cache=v_cache[i])
            new_k_cache.append(layer_k_cache)
            new_v_cache.append(layer_v_cache)

        enc_out = self.encoder.ln_post(x_chunk)

        k_cache = torch.stack(new_k_cache, dim=0)
        v_cache = torch.stack(new_v_cache, dim=0)
        cache_len = torch.clamp(cache_len + ATTENTION_CONTEXT_SIZE[1] + 1, max=ATTENTION_CONTEXT_SIZE[0])

        return enc_out, audio_cache, conv1_cache, conv2_cache, conv3_cache, k_cache, v_cache, cache_len

class WrapperDecoder(nn.Module):
    def __init__(self, decoder):
        super().__init__()
        self.decoder = decoder.to(DEVICE)

    def forward(self, token, h_n):
        dec, h_n = self.decoder(token, h_n)
        return dec, h_n

class WrapperJoint(nn.Module):
    def __init__(self, joint):
        super().__init__()
        self.joint = joint.to(DEVICE)

    def forward(self, enc, dec):
        return self.joint(enc, dec)[0, 0, 0, :]

def main():
    print("--- Exporting HKAB Model to ONNX ---")
    
    # 1. Load Model
    print("Loading model weights...")
    ckpt_path = hf_hub_download(
        repo_id="hkab/vietnamese-asr-model", 
        filename="rnnt-latest.ckpt",
        subfolder="rnnt-whisper-small/80_3"
    )
    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    
    encoder_weight = {}
    decoder_weight = {}
    joint_weight = {}
    for k, v in checkpoint['state_dict'].items():
        if 'alibi' in k: continue
        if 'encoder' in k: encoder_weight[k.replace('encoder.', '')] = v
        elif 'decoder' in k: decoder_weight[k.replace('decoder.', '')] = v
        elif 'joint' in k: joint_weight[k.replace('joint.', '')] = v

    encoder = AudioEncoder(N_MELS, n_state=N_STATE, n_head=N_HEAD, n_layer=N_LAYER, att_context_size=ATTENTION_CONTEXT_SIZE)
    decoder = Decoder(vocab_size=VOCAB_SIZE + 1)
    joint = Jointer(vocab_size=VOCAB_SIZE + 1)
    
    encoder.load_state_dict(encoder_weight, strict=False)
    decoder.load_state_dict(decoder_weight, strict=False)
    joint.load_state_dict(joint_weight, strict=False)
    
    encoder.eval().to(DEVICE)
    decoder.eval().to(DEVICE)
    joint.eval().to(DEVICE)
    
    # 2. Prepare Output Dir
    onnx_dir = os.path.join(hkab_repo_path, "onnx")
    os.makedirs(onnx_dir, exist_ok=True)
    
    # 3. Export Encoder
    print("Exporting Encoder...")
    export_encoder = WrapperEncoderALiBi(encoder)
    export_encoder.eval()
    
    audio_chunk = torch.zeros(1, HOP_LENGTH * 31 + N_FFT - (N_FFT - HOP_LENGTH), device=DEVICE)
    audio_cache = torch.zeros(1, N_FFT - HOP_LENGTH, device=DEVICE)
    conv1_cache = torch.zeros(1, 80, 1, device=DEVICE)
    conv2_cache = torch.zeros(1, 768, 1, device=DEVICE)
    conv3_cache = torch.zeros(1, 768, 1, device=DEVICE)
    k_cache = torch.zeros(12, 1, ATTENTION_CONTEXT_SIZE[0], 768, device=DEVICE)
    v_cache = torch.zeros(12, 1, ATTENTION_CONTEXT_SIZE[0], 768, device=DEVICE)
    cache_len = torch.zeros(1, dtype=torch.int, device=DEVICE)
    
    torch.onnx.export(
        export_encoder,
        (audio_chunk, audio_cache, conv1_cache, conv2_cache, conv3_cache, k_cache, v_cache, cache_len),
        os.path.join(onnx_dir, "encoder.onnx"),
        input_names=["audio_chunk", "audio_cache", "conv1_cache", "conv2_cache", "conv3_cache", "k_cache", "v_cache", "cache_len"],
        output_names=["enc_out", "audio_cache", "conv1_cache", "conv2_cache", "conv3_cache", "k_cache", "v_cache", "cache_len"],
        export_params=True,
        opset_version=17,
        do_constant_folding=False
    )
    
    # 4. Export Decoder
    print("Exporting Decoder...")
    wrapper_decoder = WrapperDecoder(decoder)
    wrapper_decoder.eval()
    token = torch.tensor([[RNNT_BLANK]], dtype=torch.long, device=DEVICE)
    h_n = torch.zeros(1, 1, 768, device=DEVICE)
    
    torch.onnx.export(
        wrapper_decoder,
        (token, h_n),
        os.path.join(onnx_dir, "decoder.onnx"),
        input_names=["token", "h_n"],
        output_names=["dec", "h_n"],
        export_params=True,
        opset_version=17
    )
    
    # 5. Export Jointer
    print("Exporting Jointer...")
    wrapper_joint = WrapperJoint(joint)
    wrapper_joint.eval()
    enc = torch.zeros(1, 1, 768, device=DEVICE)
    dec = torch.zeros(1, 1, 768, device=DEVICE)
    
    torch.onnx.export(
        wrapper_joint,
        (enc, dec),
        os.path.join(onnx_dir, "jointer.onnx"),
        input_names=["enc", "dec"],
        output_names=["output"],
        export_params=True,
        opset_version=17
    )
    
    # 6. Quantization
    print("Quantizing models...")
    
    # Preprocess (as per notebook)
    for name in ["encoder", "decoder", "jointer"]:
        subprocess.run([sys.executable, "-m", "onnxruntime.quantization.preprocess", 
                        "--input", os.path.join(onnx_dir, f"{name}.onnx"), 
                        "--output", os.path.join(onnx_dir, f"{name}-infer.onnx")])
    
    # Quantize
    quantize_dynamic(
        os.path.join(onnx_dir, 'encoder-infer.onnx'), 
        os.path.join(onnx_dir, 'encoder-infer.quant.onnx'),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=['MatMul']
    )
    quantize_dynamic(
        os.path.join(onnx_dir, 'decoder-infer.onnx'), 
        os.path.join(onnx_dir, 'decoder-infer.quant.onnx'),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=['GRU']
    )
    quantize_dynamic(
        os.path.join(onnx_dir, 'jointer-infer.onnx'), 
        os.path.join(onnx_dir, 'jointer-infer.quant.onnx'),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=['MatMul']
    )
    
    print("Export and Quantization Complete!")

if __name__ == "__main__":
    main()
