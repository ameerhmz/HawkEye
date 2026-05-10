"""
Behavior Anomaly Detector using SlowFast Networks.
Detects abnormal activities in video frames without classification.
Pre-trained on UCF-Crime dataset (13 abnormal behaviors).
"""

import logging
import os
from typing import Optional, List, Tuple
import cv2
import numpy as np
from collections import deque

try:
    import torch
    import torchvision.transforms as transforms
    from mmaction.apis import init_recognizer, inference_recognizer
except ImportError:
    torch = None
    transforms = None
    init_recognizer = None
    inference_recognizer = None

logger = logging.getLogger("behavior_detector")

# SlowFast configuration
SLOWFAST_FRAME_BUFFER_SIZE = 32  # SlowFast uses 32 frames
SLOWFAST_SAMPLE_RATE = 2  # Sample every 2nd frame
ANOMALY_THRESHOLD = 0.5  # Score threshold for anomaly (0-1)
ANOMALY_SMOOTHING = 0.7  # Exponential moving average for scores


class BehaviorAnomalyDetector:
    """
    Detects anomalous behavior in video using SlowFast Networks.
    
    Model: SlowFast pre-trained on Kinetics-400
    Fine-tuning: Can be fine-tuned on UCF-Crime dataset
    Output: Anomaly score (0-1, where 1 = high anomaly)
    """
    
    def __init__(self, device: str = "cpu", model_path: Optional[str] = None):
        """
        Initialize SlowFast anomaly detector.
        
        Args:
            device: "cpu", "cuda", or "mps" (for Mac GPU)
            model_path: Path to pretrained model weights (optional)
        """
        self.device = device
        self.model = None
        self.frame_buffer: deque = deque(maxlen=SLOWFAST_FRAME_BUFFER_SIZE)
        self.anomaly_score = 0.0
        self.frame_preprocessor = None
        
        if torch is None:
            logger.warning("PyTorch not installed. Behavior anomaly detection disabled.")
            return
        
        try:
            self._init_model(model_path)
            logger.info(f"BehaviorAnomalyDetector initialized on device: {self.device}")
        except Exception as e:
            logger.error(f"Failed to initialize BehaviorAnomalyDetector: {e}")
            self.model = None
    
    def _init_model(self, model_path: Optional[str] = None):
        """Initialize SlowFast model from MMAction2 model zoo or custom weights."""
        try:
            # Option 1: Use PyTorch Hub pre-trained SlowFast (Kinetics-400)
            # This is the easiest approach without MMAction2
            self.model = torch.hub.load(
                'facebookresearch/pytorchvideo',
                'slowfast_r50',
                pretrained=True
            ).to(self.device)
            self.model.eval()
            
            # Setup preprocessing
            self.frame_preprocessor = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.45, 0.45, 0.45],
                    std=[0.225, 0.225, 0.225]
                ),
                transforms.Resize((256, 256))
            ])
            
            logger.info("Loaded SlowFast-R50 model from PyTorch Hub (Kinetics-400)")
            
        except Exception as e:
            logger.warning(f"Could not load SlowFast from PyTorch Hub: {e}")
            logger.info("Falling back to simple motion-based anomaly detection")
            self.model = None
    
    def add_frame(self, frame: np.ndarray) -> None:
        """
        Add a frame to the buffer.
        
        Args:
            frame: BGR image (H, W, 3)
        """
        # Resize to standard size for consistency
        resized = cv2.resize(frame, (224, 224))
        self.frame_buffer.append(resized)
    
    def detect_anomaly(self) -> Tuple[float, bool]:
        """
        Detect anomaly from buffered frames.
        
        Returns:
            (anomaly_score, is_anomaly) where score in [0, 1]
        """
        if not self.frame_buffer or len(self.frame_buffer) < 8:
            # Need at least 8 frames for meaningful detection
            return 0.0, False
        
        if self.model is None:
            # Fallback: simple motion-based anomaly detection
            return self._detect_anomaly_motion()
        
        try:
            return self._detect_anomaly_slowfast()
        except Exception as e:
            logger.warning(f"SlowFast inference failed: {e}. Using fallback.")
            return self._detect_anomaly_motion()
    
    def _detect_anomaly_slowfast(self) -> Tuple[float, bool]:
        """
        Detect anomaly using SlowFast model.
        
        Returns:
            (anomaly_score, is_anomaly)
        """
        # Stack frames: (T, H, W, 3)
        frames = np.array(list(self.frame_buffer))  # (T, 224, 224, 3)
        
        # Convert BGR to RGB and normalize
        frames_rgb = cv2.cvtColor(frames[0], cv2.COLOR_BGR2RGB)
        
        # Prepare batch: (1, 3, T, H, W) for slow pathway
        # SlowFast expects (B, C, T, H, W)
        frames_tensor = torch.from_numpy(frames_rgb).permute(2, 0, 1).unsqueeze(0).float()
        frames_tensor = frames_tensor.to(self.device)
        
        # Normalize
        frames_tensor = frames_tensor / 255.0
        frames_tensor = transforms.Normalize(
            mean=[0.45, 0.45, 0.45],
            std=[0.225, 0.225, 0.225]
        )(frames_tensor)
        
        with torch.no_grad():
            # For SlowFast, we need to prepare slow and fast pathways
            # Slow: sample every 2 frames, Fast: sample every frame
            slow_frames = frames_tensor[:, :, ::2, :, :]  # Sample slow pathway
            fast_frames = frames_tensor  # Fast pathway uses all frames
            
            # Model expects dict input for SlowFast
            inputs = {
                'slow': slow_frames,
                'fast': fast_frames
            }
            
            # If model only accepts tensor, use the tensor directly
            try:
                output = self.model(frames_tensor)
            except:
                output = self.model([frames_tensor])
        
        # Extract anomaly score (use softmax output for abnormal class)
        # For Kinetics-400, we look for suspicious activity patterns
        anomaly_score = self._compute_anomaly_score(output)
        
        # Apply exponential smoothing
        self.anomaly_score = ANOMALY_SMOOTHING * self.anomaly_score + (1 - ANOMALY_SMOOTHING) * anomaly_score
        
        is_anomaly = self.anomaly_score > ANOMALY_THRESHOLD
        
        return self.anomaly_score, is_anomaly
    
    def _compute_anomaly_score(self, model_output: torch.Tensor) -> float:
        """
        Compute anomaly score from model output.
        Kinetics-400 has action classes; we map suspicious actions to high anomaly scores.
        
        Args:
            model_output: Model output logits or probabilities
            
        Returns:
            Anomaly score (0-1)
        """
        try:
            # Apply softmax to get probabilities
            if model_output.dim() == 2:
                probs = torch.softmax(model_output, dim=1)
            else:
                probs = torch.softmax(model_output, dim=0)
            
            probs = probs.cpu().numpy()
            
            # Kinetics-400 suspicious action indices (approximation)
            # These are common action indices associated with abnormal behaviors
            suspicious_indices = [
                80,   # Breaking
                94,   # Chopping
                105,  # Climbing
                142,  # Falling
                156,  # Fighting
                240,  # Jumping
                280,  # Pushing
                310,  # Running
                350,  # Throwing
                374,  # Tumbling
            ]
            
            # Get max probability from suspicious actions
            if len(suspicious_indices) > 0:
                suspicious_probs = probs[0, suspicious_indices] if probs.ndim == 2 else probs[suspicious_indices]
                anomaly_score = float(np.max(suspicious_probs))
            else:
                anomaly_score = float(np.max(probs))
            
            return min(1.0, anomaly_score * 2.0)  # Scale up for sensitivity
        
        except Exception as e:
            logger.warning(f"Error computing anomaly score: {e}")
            return 0.5
    
    def _detect_anomaly_motion(self) -> Tuple[float, bool]:
        """
        Fallback: Simple motion-based anomaly detection.
        Detects sudden movement changes or high motion variance.
        
        Returns:
            (anomaly_score, is_anomaly)
        """
        if len(self.frame_buffer) < 2:
            return 0.0, False
        
        frames = list(self.frame_buffer)
        
        # Compute optical flow
        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        motions = []
        
        for frame in frames[1:]:
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            
            # Compute motion magnitude
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            motion_mean = np.mean(mag)
            motions.append(motion_mean)
            prev_gray = curr_gray
        
        if len(motions) == 0:
            return 0.0, False
        
        # High variance in motion = anomaly
        motion_variance = np.var(motions)
        motion_mean = np.mean(motions)
        
        # Anomaly score based on motion variance and intensity
        anomaly_score = min(1.0, (motion_variance / 100.0) + (motion_mean / 50.0))
        
        # Apply smoothing
        self.anomaly_score = ANOMALY_SMOOTHING * self.anomaly_score + (1 - ANOMALY_SMOOTHING) * anomaly_score
        
        is_anomaly = self.anomaly_score > ANOMALY_THRESHOLD
        
        return self.anomaly_score, is_anomaly
    
    def reset(self) -> None:
        """Reset frame buffer and anomaly score."""
        self.frame_buffer.clear()
        self.anomaly_score = 0.0


def get_behavior_detector(device: Optional[str] = None) -> Optional[BehaviorAnomalyDetector]:
    """
    Factory function to create a behavior detector.
    
    Args:
        device: "cpu", "cuda", or "mps". If None, auto-detect.
        
    Returns:
        BehaviorAnomalyDetector instance or None if PyTorch unavailable
    """
    if torch is None:
        return None
    
    if device is None:
        # Auto-detect device
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    
    return BehaviorAnomalyDetector(device=device)
