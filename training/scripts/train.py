#!/usr/bin/env python3
from __future__ import annotations

"""
Train YOLOv8-seg on the DeepFashion2 dataset for clothing instance segmentation.

Fine-tunes a COCO-pretrained YOLOv8 segmentation model on our 6 merged
clothing categories: top, outerwear, shorts, trousers, skirt, dress.

Usage:
    # Local test run (2 epochs, verify pipeline works)
    python train.py \
        --data ../data/deepfashion2_yolo_subset/dataset.yaml \
        --epochs 2 \
        --batch 8 \
        --name local_test

    # Full training (run on Colab with GPU)
    python train.py \
        --data ../data/deepfashion2_yolo_subset/dataset.yaml \
        --epochs 50 \
        --batch 16 \
        --name clothing_seg_v1

    # Use a larger model
    python train.py \
        --data ../data/deepfashion2_yolo_subset/dataset.yaml \
        --model yolov8s-seg.pt \
        --epochs 50 \
        --name clothing_seg_s
"""

import argparse
import sys
import torch


def detect_device() -> str:
    """
    Auto-detect the best available device.

    Priority: CUDA (Colab/desktop GPU) → MPS (Apple Silicon) → CPU

    Returns:
        Device string for ultralytics: "0" (first CUDA GPU), "mps", or "cpu"
    """
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
        print(f"  ✓ CUDA GPU detected: {gpu_name} ({vram:.1f} GB VRAM)")
        return "0"

    if torch.backends.mps.is_available():
        print("  ✓ Apple Silicon MPS detected")
        print("  ⚠ MPS training is slower than CUDA and may have stability issues.")
        print("    For full training, consider using Google Colab (free T4 GPU).")
        return "mps"

    print("  ⚠ No GPU detected — training will run on CPU (very slow!)")
    print("    For full training, use Google Colab (free T4 GPU).")
    return "cpu"


def main():
    parser = argparse.ArgumentParser(
        description="Train YOLOv8-seg for clothing instance segmentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model sizes (COCO-pretrained):
  yolov8n-seg.pt  — Nano   (3.4M params, fastest, least accurate)
  yolov8s-seg.pt  — Small  (11.8M params, good balance)
  yolov8m-seg.pt  — Medium (27.3M params, more accurate, slower)
  yolov8l-seg.pt  — Large  (46.0M params, even more accurate)

Recommended workflow:
  1. Start with nano (yolov8n-seg.pt) to iterate quickly
  2. Once happy with data/pipeline, upgrade to small or medium
  3. Compare results across model sizes for your capstone report
        """,
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to dataset.yaml file.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n-seg.pt",
        help="Pretrained model to fine-tune. Default: yolov8n-seg.pt (nano).",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Max training epochs. Default: 50.",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Batch size. Reduce if you get OOM errors. Default: 16.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Training image size. Default: 640.",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=10,
        help="Early stopping patience (epochs without improvement). Default: 10.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device: '0' (CUDA), 'mps' (Apple Silicon), 'cpu'. Auto-detected if not specified.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="clothing_seg_v1",
        help="Run name. Results saved to runs/<name>/. Default: clothing_seg_v1.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Dataloader workers. Default: 4.",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume training from (e.g., runs/clothing_seg_v1/weights/last.pt).",
    )
    parser.add_argument(
        "--freeze",
        type=int,
        default=0,
        help="Number of backbone layers to freeze (0 = none). Try 10 to freeze the backbone for small datasets.",
    )

    args = parser.parse_args()

    # ---------------------------------------------------------------------------
    # Device detection
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  YOLOv8-seg Training — Clothing Instance Segmentation")
    print("=" * 60)
    print("\nDevice detection:")

    device = args.device or detect_device()

    # ---------------------------------------------------------------------------
    # Print training config
    # ---------------------------------------------------------------------------
    print(f"\nTraining configuration:")
    print(f"  Model:          {args.model}")
    print(f"  Dataset:        {args.data}")
    print(f"  Epochs:         {args.epochs}")
    print(f"  Batch size:     {args.batch}")
    print(f"  Image size:     {args.imgsz}")
    print(f"  Patience:       {args.patience}")
    print(f"  Device:         {device}")
    print(f"  Workers:        {args.workers}")
    print(f"  Run name:       {args.name}")
    print(f"  Freeze layers:  {args.freeze}")
    if args.resume:
        print(f"  Resuming from:  {args.resume}")
    print()

    # ---------------------------------------------------------------------------
    # Load model
    # ---------------------------------------------------------------------------
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    if args.resume:
        print(f"Resuming training from {args.resume}...")
        model = YOLO(args.resume)
    else:
        print(f"Loading pretrained model: {args.model}")
        model = YOLO(args.model)

    # ---------------------------------------------------------------------------
    # Train
    # ---------------------------------------------------------------------------
    print(f"\nStarting training...\n")

    train_args = dict(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        device=device,
        workers=args.workers,
        name=args.name,
        project="../runs",
        save=True,
        plots=True,
        exist_ok=True,
        verbose=True,
        # Freeze backbone layers if specified
        freeze=args.freeze if args.freeze > 0 else None,
    )

    # Remove None values (ultralytics doesn't like explicit None for some args)
    train_args = {k: v for k, v in train_args.items() if v is not None}

    results = model.train(**train_args)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Training Complete!")
    print("=" * 60)
    print(f"\n  Results saved to: runs/{args.name}/")
    print(f"  Best weights:     runs/{args.name}/weights/best.pt")
    print(f"  Last weights:     runs/{args.name}/weights/last.pt")
    print(f"  Training plots:   runs/{args.name}/")
    print(f"\n  Next steps:")
    print(f"    1. Check training curves in runs/{args.name}/results.png")
    print(f"    2. Run evaluation:  python evaluate.py --weights runs/{args.name}/weights/best.pt")
    print(f"    3. Run inference:   python inference.py --weights runs/{args.name}/weights/best.pt --source <image>")
    print()


if __name__ == "__main__":
    main()
