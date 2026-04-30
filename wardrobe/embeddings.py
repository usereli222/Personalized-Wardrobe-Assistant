"""
FashionCLIP Embedding generator.

Takes raw or cropped clothing images and extracts dense numerical
vectors mapping their specific visual features into a shared space.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoProcessor, CLIPModel

logger = logging.getLogger(__name__)


class ClothingEmbedder:
    """
    Generates FashionCLIP embeddings for clothing images.
    
    FashionCLIP understands nuanced fashion details compared to generic
    CLIP models. We use it to produce normalized L2 feature vectors so
    cosine similarity strictly equals the dot product.
    """

    def __init__(
        self,
        model_name: str = "patrickjohncyh/fashion-clip",
        device: str = "cpu",
    ):
        """
        Load the FashionCLIP model and processor.

        Args:
            model_name: HuggingFace model ID for FashionCLIP.
            device: Computing device. Defaults to CPU safely.
        """
        self.device = torch.device(device)
        self.model_name = model_name

        logger.info(f"Loading FashionCLIP ({model_name})...")
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.model.eval()  # strictly inference mode
        logger.info(f"FashionCLIP loaded entirely on {self.device}.")

    def _ensure_pil(self, image_input: Union[str, Path, Image.Image, np.ndarray]) -> Image.Image:
        """Convert input to a proper RGB PIL Image."""
        if isinstance(image_input, (str, Path)):
            img = Image.open(image_input)
        elif isinstance(image_input, np.ndarray):
            img = Image.fromarray(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            raise ValueError(f"Unsupported image format: type {type(image_input)}")

        # Make sure it's strictly RGB (no Alpha channel as black backgrounds wreck CLIP embeddings)
        if img.mode == "RGBA":
            # Composite over standard white
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3]) # 3 is the alpha channel mask
            return background
        
        return img.convert("RGB")

    def _encode_image(self, pixel_values):
        """Run the CLIP vision encoder + visual projection manually.

        We bypass `model.get_image_features` because its return shape became
        unstable in transformers >= 4.51 (sometimes a tensor, sometimes a
        ModelOutput wrapper, sometimes pre-projected, sometimes not). Going
        straight through `vision_model` and `visual_projection` is well-
        defined across versions and gives us a clean (B, 512) tensor.
        """
        vision_out = self.model.vision_model(pixel_values=pixel_values)
        pooled = vision_out.pooler_output  # (B, hidden_dim) raw ViT CLS
        return self.model.visual_projection(pooled)  # (B, 512)

    def _encode_text(self, input_ids, attention_mask=None):
        """Run the CLIP text encoder + text projection manually."""
        kwargs = {"input_ids": input_ids}
        if attention_mask is not None:
            kwargs["attention_mask"] = attention_mask
        text_out = self.model.text_model(**kwargs)
        pooled = text_out.pooler_output  # (B, hidden_dim)
        return self.model.text_projection(pooled)  # (B, 512)

    @torch.no_grad()
    def embed(self, image: Union[str, Path, Image.Image, np.ndarray]) -> np.ndarray:
        """
        Embed a single clothing image.

        Args:
            image: PIL Image, numpy array, or file path

        Returns:
            Normalized 1D embedding vector as numpy array, shape (512,)
        """
        pil_img = self._ensure_pil(image)

        # Preprocess
        inputs = self.processor(images=pil_img, return_tensors="pt")
        # Move to correct device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        features = self._encode_image(inputs["pixel_values"])
        embeddings = F.normalize(features, p=2, dim=-1)
        return embeddings.cpu().numpy()[0]

    @torch.no_grad()
    def embed_text(self, prompts: list[str]) -> np.ndarray:
        """
        Embed a list of text prompts in the same FashionCLIP space as images.

        Used by the zero-shot categorizer: dot-product an image embedding
        against per-category prompt embeddings to pick the best label.

        Returns:
            L2-normalized embeddings as 2D numpy array, shape (len(prompts), 512)
        """
        if not prompts:
            return np.array([])

        inputs = self.processor(text=prompts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        features = self._encode_text(
            inputs["input_ids"], inputs.get("attention_mask")
        )
        embeddings = F.normalize(features, p=2, dim=-1)
        return embeddings.cpu().numpy()

    @torch.no_grad()
    def embed_batch(
        self,
        images: list[Union[str, Path, Image.Image, np.ndarray]],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Embed multiple clothing images efficiently.

        Args:
            images: list of images (PIL, path, numpy)
            batch_size: number of images processed simultaneously

        Returns:
            Normalized embeddings as 2D numpy array, shape (N, 512)
        """
        if not images:
            return np.array([])

        all_embeddings = []
        
        for i in range(0, len(images), batch_size):
            batch_inputs = images[i : i + batch_size]
            pil_batch = [self._ensure_pil(img) for img in batch_inputs]

            # Preprocess the entire batch at once
            inputs = self.processor(images=pil_batch, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            features = self._encode_image(inputs["pixel_values"])
            embeddings = F.normalize(features, p=2, dim=-1)

            all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    @staticmethod
    def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute similarity between two normalized embeddings.
        Since they are unit length, cosine similarity is just the dot product.
        """
        return float(np.dot(embedding1, embedding2))

    @staticmethod
    def compute_similarity_matrix(embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """
        Matrix of pairwise cosine similarities between two embedding sets.
        
        Args:
            embeddings1: (N, D) array
            embeddings2: (M, D) array
            
        Returns:
            (N, M) matrix of cosine similarities
        """
        return np.dot(embeddings1, embeddings2.T)