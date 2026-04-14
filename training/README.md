# Clothing Instance Segmentation — Training Pipeline

Fine-tuning YOLOv8-seg on DeepFashion2 for clothing detection and pixel-level segmentation.

## Setup

```bash
cd training
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Dataset Preparation

1. Download DeepFashion2 from Kaggle (see `data/README.md` for instructions)
2. Place it in `data/deepfashion2_raw/`
3. Run the conversion script:

```bash
cd scripts
python convert_deepfashion2_to_yolo.py \
    --raw-dir ../data/deepfashion2_raw \
    --out-dir ../data/deepfashion2_yolo \
    --splits train validation
```

4. (Optional) Visualize converted labels to verify:

```bash
python visualize_labels.py \
    --data-dir ../data/deepfashion2_yolo \
    --split train \
    --num-images 10
```

5. Sample a balanced subset for training:

```bash
python sample_subset.py \
    --input-dir ../data/deepfashion2_yolo \
    --output-dir ../data/deepfashion2_yolo_subset \
    --train-size 15000 \
    --val-size 2000
```

## Category Mapping

DeepFashion2's 13 fine-grained categories are merged into 6 classes:

| YOLO Class ID | Class Name | DeepFashion2 Categories |
|---|---|---|
| 0 | top | short sleeve top, long sleeve top, vest, sling |
| 1 | outerwear | short sleeve outwear, long sleeve outwear |
| 2 | shorts | shorts |
| 3 | trousers | trousers |
| 4 | skirt | skirt |
| 5 | dress | short sleeve dress, long sleeve dress, vest dress, sling dress |

## Pipeline Overview

```
deepfashion2_raw/     →  convert  →  deepfashion2_yolo/     →  sample  →  subset/
(391K images, JSON)                  (391K images, YOLO txt)              (15K train, 2K val)
                                                                              ↓
                                                                          train.py
                                                                              ↓
                                                                      runs/clothing_seg_v1/
                                                                          weights/best.pt
```
