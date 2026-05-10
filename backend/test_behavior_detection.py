#!/usr/bin/env python3
"""
Test script for behavior anomaly detection.
Run this to verify SlowFast model loads correctly and anomaly detection works.
"""

import sys
import os
import logging

# Setup paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_behavior_detection")

def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing imports...")
    try:
        import torch
        logger.info(f"✓ PyTorch {torch.__version__}")
    except ImportError as e:
        logger.error(f"✗ PyTorch not installed: {e}")
        return False
    
    try:
        import torchvision
        logger.info(f"✓ Torchvision {torchvision.__version__}")
    except ImportError as e:
        logger.error(f"✗ Torchvision not installed: {e}")
        return False
    
    try:
        import cv2
        logger.info(f"✓ OpenCV {cv2.__version__}")
    except ImportError as e:
        logger.error(f"✗ OpenCV not installed: {e}")
        return False
    
    try:
        from app.behavior_detector import get_behavior_detector
        logger.info("✓ behavior_detector module")
    except ImportError as e:
        logger.error(f"✗ behavior_detector import failed: {e}")
        return False
    
    return True


def test_behavior_detector():
    """Test behavior detector initialization and inference."""
    logger.info("\nTesting behavior detector...")
    
    try:
        from app.behavior_detector import get_behavior_detector
        import numpy as np
        
        # Create detector
        detector = get_behavior_detector(device="cpu")
        if detector is None:
            logger.warning("⚠ Behavior detector returned None (PyTorch may not be available)")
            return False
        
        logger.info("✓ Behavior detector initialized")
        
        # Create dummy frames
        dummy_frame = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        
        # Add frames to buffer
        for _ in range(32):
            detector.add_frame(dummy_frame)
        
        logger.info("✓ Added 32 frames to buffer")
        
        # Run anomaly detection
        score, is_anomaly = detector.detect_anomaly()
        logger.info(f"✓ Anomaly detection ran: score={score:.4f}, is_anomaly={is_anomaly}")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Behavior detector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ucf_crime_dataset():
    """Test UCF-Crime dataset interface."""
    logger.info("\nTesting UCF-Crime dataset...")
    
    try:
        from app.ucf_crime_loader import get_ucf_crime_dataset
        
        dataset = get_ucf_crime_dataset()
        logger.info("✓ UCF-Crime dataset interface initialized")
        
        stats = dataset.get_dataset_stats()
        logger.info(f"✓ Dataset stats:")
        logger.info(f"  - Available locally: {stats['available']}")
        logger.info(f"  - Supported classes: {stats['total_classes']}")
        logger.info(f"  - Classes: {', '.join(stats['classes'])}")
        
        if not stats['available']:
            logger.warning("⚠ Dataset not found locally. Download instructions:")
            logger.info(dataset.download_instructions())
        
        return True
    
    except Exception as e:
        logger.error(f"✗ UCF-Crime dataset test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_device_detection():
    """Test GPU device detection."""
    logger.info("\nTesting device detection...")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            logger.info(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            logger.info("✓ MPS (Apple Metal) available")
        else:
            logger.info("⚠ No GPU detected, will use CPU")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Device detection failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Behavior Anomaly Detection - Test Suite")
    logger.info("=" * 60)
    
    results = {}
    results['imports'] = test_imports()
    results['device'] = test_device_detection()
    results['behavior_detector'] = test_behavior_detector()
    results['ucf_crime'] = test_ucf_crime_dataset()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Results:")
    logger.info("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n✓ All tests passed!")
        return 0
    else:
        logger.error("\n✗ Some tests failed. See above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
