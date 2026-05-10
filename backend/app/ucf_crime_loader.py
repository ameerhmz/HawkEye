"""
UCF-Crime Dataset Downloader and Loader.
Downloads and manages the UCF-Crime dataset for fine-tuning behavior detection models.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request

logger = logging.getLogger("ucf_crime_loader")

# UCF-Crime dataset metadata
UCF_CRIME_INFO = {
    "name": "UCF-Crime",
    "url": "https://www.crcv.ucf.edu/datasets/ucf-crime/",
    "paper": "https://arxiv.org/abs/1801.04264",
    "abnormal_behaviors": [
        "Abuse",
        "Arrest",
        "Arson",
        "Assault",
        "Burglary",
        "Explosion",
        "Fighting",
        "Robbery",
        "Shooting",
        "Shoplifting",
        "Stealing",
        "Trespassing",
        "Vandalism",
    ],
    "note": "Use official UCF-Crime dataset. Download from: https://www.crcv.ucf.edu/datasets/ucf-crime/"
}


class UCFCrimeDataset:
    """
    Interface for UCF-Crime dataset.
    
    The dataset contains:
    - 128 real-world surveillance videos
    - 13 types of abnormal behaviors
    - Temporal annotations for abnormal events
    - Total ~1900 video clips with anomaly labels
    """
    
    def __init__(self, data_dir: str = "/tmp/ucf-crime"):
        """
        Initialize UCF-Crime dataset interface.
        
        Args:
            data_dir: Directory to store dataset
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.anomaly_classes = UCF_CRIME_INFO["abnormal_behaviors"]
        self.class_to_idx = {name: idx for idx, name in enumerate(self.anomaly_classes)}
        self.idx_to_class = {idx: name for name, idx in self.class_to_idx.items()}
    
    def download_instructions(self) -> str:
        """Return instructions for downloading the dataset."""
        return f"""
        UCF-Crime Dataset Download Instructions:
        
        1. Visit: {UCF_CRIME_INFO['url']}
        2. Fill out the request form
        3. Download the dataset (~20 GB)
        4. Extract to: {self.data_dir}
        
        Expected structure:
        {self.data_dir}/
            Abuse/
            Arrest/
            ...
            Vandalism/
        
        Paper: {UCF_CRIME_INFO['paper']}
        """
    
    def get_class_name(self, class_idx: int) -> str:
        """Get class name from index."""
        return self.idx_to_class.get(class_idx, "Unknown")
    
    def get_class_idx(self, class_name: str) -> int:
        """Get class index from name."""
        return self.class_to_idx.get(class_name, -1)
    
    def is_available(self) -> bool:
        """Check if dataset is available locally."""
        if not self.data_dir.exists():
            return False
        
        # Check if any anomaly class directories exist
        for behavior in self.anomaly_classes:
            behavior_dir = self.data_dir / behavior
            if behavior_dir.exists():
                return True
        
        return False
    
    def get_video_paths(self, split: str = "all") -> Dict[str, List[str]]:
        """
        Get video paths organized by class.
        
        Args:
            split: "all", "train", or "test"
            
        Returns:
            Dict mapping class names to video paths
        """
        videos_by_class = {behavior: [] for behavior in self.anomaly_classes}
        
        if not self.is_available():
            logger.warning(f"UCF-Crime dataset not found at {self.data_dir}")
            return videos_by_class
        
        for behavior in self.anomaly_classes:
            behavior_dir = self.data_dir / behavior
            if behavior_dir.exists():
                # Look for video files (.avi, .mp4, .mov)
                video_extensions = [".avi", ".mp4", ".mov", ".mkv"]
                for ext in video_extensions:
                    videos_by_class[behavior].extend(
                        str(p) for p in behavior_dir.glob(f"*{ext}")
                    )
                
                logger.info(f"Found {len(videos_by_class[behavior])} videos in {behavior}")
        
        return videos_by_class
    
    def get_dataset_stats(self) -> Dict:
        """Get dataset statistics."""
        videos_by_class = self.get_video_paths()
        total_videos = sum(len(v) for v in videos_by_class.values())
        
        return {
            "total_videos": total_videos,
            "total_classes": len(self.anomaly_classes),
            "classes": self.anomaly_classes,
            "videos_per_class": {k: len(v) for k, v in videos_by_class.items()},
            "available": self.is_available()
        }


class BehaviorDatasetPreparer:
    """
    Prepare behavior dataset for fine-tuning SlowFast model.
    Converts video sequences to frame stacks compatible with SlowFast.
    """
    
    def __init__(self, output_dir: str = "/tmp/slowfast-prepared"):
        """
        Initialize dataset preparer.
        
        Args:
            output_dir: Output directory for prepared dataset
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_frame_stacks(
        self,
        video_dir: str,
        num_frames: int = 32,
        stride: int = 2,
        output_format: str = "npz"
    ) -> List[str]:
        """
        Prepare video frame stacks for SlowFast training.
        
        Args:
            video_dir: Directory containing video files
            num_frames: Number of frames per stack (SlowFast default: 32)
            stride: Frame sampling stride
            output_format: "npz" or "jpg"
            
        Returns:
            List of prepared dataset file paths
        """
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not installed. Cannot prepare frame stacks.")
            return []
        
        prepared_files = []
        video_dir = Path(video_dir)
        
        if not video_dir.exists():
            logger.error(f"Video directory not found: {video_dir}")
            return prepared_files
        
        for video_file in video_dir.glob("*.avi"):
            try:
                frames = self._extract_frames(str(video_file), num_frames, stride)
                if frames is not None:
                    output_file = self._save_frame_stack(
                        frames, video_file.stem, output_format
                    )
                    prepared_files.append(output_file)
                    logger.info(f"Prepared: {video_file.name}")
            except Exception as e:
                logger.warning(f"Failed to prepare {video_file.name}: {e}")
        
        return prepared_files
    
    def _extract_frames(
        self,
        video_path: str,
        num_frames: int,
        stride: int
    ) -> Optional[List]:
        """Extract frames from video."""
        try:
            import cv2
        except ImportError:
            return None
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return None
        
        frames = []
        frame_count = 0
        sample_count = 0
        
        while sample_count < num_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % stride == 0:
                # Resize to SlowFast input size (224x224)
                frame = cv2.resize(frame, (224, 224))
                frames.append(frame)
                sample_count += 1
            
            frame_count += 1
        
        cap.release()
        
        # Pad or truncate to exact num_frames
        if len(frames) < num_frames:
            # Repeat last frame to pad
            frames.extend([frames[-1]] * (num_frames - len(frames)))
        else:
            frames = frames[:num_frames]
        
        return frames if len(frames) == num_frames else None
    
    def _save_frame_stack(
        self,
        frames: List,
        video_name: str,
        output_format: str
    ) -> str:
        """Save extracted frame stack."""
        if output_format == "npz":
            import numpy as np
            output_file = self.output_dir / f"{video_name}.npz"
            np.savez_compressed(output_file, frames=np.array(frames))
        else:
            # Save as individual JPEGs
            output_subdir = self.output_dir / video_name
            output_subdir.mkdir(exist_ok=True)
            
            try:
                import cv2
            except ImportError:
                return ""
            
            for idx, frame in enumerate(frames):
                cv2.imwrite(str(output_subdir / f"frame_{idx:04d}.jpg"), frame)
            
            output_file = str(output_subdir)
        
        return str(output_file)


def get_ucf_crime_dataset(data_dir: Optional[str] = None) -> UCFCrimeDataset:
    """
    Factory function to get UCF-Crime dataset instance.
    
    Args:
        data_dir: Path to dataset directory
        
    Returns:
        UCFCrimeDataset instance
    """
    if data_dir is None:
        # Try default locations
        default_locations = [
            "/data/ucf-crime",
            "/tmp/ucf-crime",
            os.path.expanduser("~/datasets/ucf-crime"),
        ]
        for loc in default_locations:
            if os.path.exists(loc):
                data_dir = loc
                break
        else:
            data_dir = default_locations[0]
    
    return UCFCrimeDataset(data_dir)


if __name__ == "__main__":
    # Quick test
    dataset = get_ucf_crime_dataset()
    print(dataset.download_instructions())
    print("\nDataset stats:", dataset.get_dataset_stats())
