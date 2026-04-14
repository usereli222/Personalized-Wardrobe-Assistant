# DeepFashion2 Dataset

## Download

DeepFashion2 is available on Kaggle:
https://www.kaggle.com/datasets/thusharanair/deepfashion2-original-with-dataframes

### Steps:

1. Go to the Kaggle link above
2. Download the dataset (requires Kaggle account)
3. Extract the contents into this directory (`training/data/deepfashion2_raw/`)

### Expected directory structure after extraction:

```
deepfashion2_raw/
├── train/
│   ├── annos/          # 191,961 JSON annotation files
│   │   ├── 000001.json
│   │   ├── 000002.json
│   │   └── ...
│   └── image/          # 191,961 image files
│       ├── 000001.jpg
│       ├── 000002.jpg
│       └── ...
├── validation/
│   ├── annos/          # 32,153 JSON annotation files
│   └── image/          # 32,153 image files
├── test/
│   └── image/          # Test images (no annotations)
├── train_df.csv
├── val_df.csv
└── test_df.csv
```

> **Note:** The CSV dataframes are not used by our conversion scripts —
> we read the per-image JSON files directly from the `annos/` directories.

## Citation

```
@article{DeepFashion2,
  author = {Yuying Ge and Ruimao Zhang and Xiaogang Wang and Xiaoou Tang and Ping Luo},
  title = {DeepFashion2: A Versatile Benchmark for Detection, Pose Estimation, Segmentation and Re-Identification of Clothing Images},
  journal = {CVPR},
  year = {2019}
}
```
