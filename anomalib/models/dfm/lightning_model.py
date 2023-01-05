"""DFM: Deep Feature Modeling."""

# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import List, Tuple

import torch
from pytorch_lightning.utilities.cli import MODEL_REGISTRY
from torch import Tensor

from anomalib.models.components import AnomalyModule
from anomalib.models.components.feature_extraction import FeatureExtractorParams

from .torch_model import DFMModel

logger = logging.getLogger(__name__)


@MODEL_REGISTRY
class Dfm(AnomalyModule):
    """DFM: Deep Featured Kernel Density Estimation.

    Args:
        feature_extractor (FeatureExtractorParams): Feature extractor params
        input_size (Tuple[int, int]): Input size for the model.
        pooling_kernel_size (int, optional): Kernel size to pool features extracted from the CNN.
            Defaults to 4.
        pca_level (float, optional): Ratio from which number of components for PCA are calculated.
            Defaults to 0.97.
        score_type (str, optional): Scoring type. Options are `fre` and `nll`. Defaults to "fre".
        nll: for Gaussian modeling, fre: pca feature-reconstruction error. Anomaly segmentation is
        supported with `fre` only. If using `nll`, set `task` in config.yaml to classification
    """

    def __init__(
        self,
        feature_extractor: FeatureExtractorParams,
        input_size: Tuple[int, int],
        pooling_kernel_size: int = 4,
        pca_level: float = 0.97,
        score_type: str = "fre",
    ):
        super().__init__()

        self.model: DFMModel = DFMModel(
            feature_extractor_params=feature_extractor,
            input_size=input_size,
            pooling_kernel_size=pooling_kernel_size,
            n_comps=pca_level,
            score_type=score_type,
        )
        self.embeddings: List[Tensor] = []
        self.score_type = score_type

    @staticmethod
    def configure_optimizers() -> None:  # pylint: disable=arguments-differ
        """DFM doesn't require optimization, therefore returns no optimizers."""
        return None

    def training_step(self, batch, _):  # pylint: disable=arguments-differ
        """Training Step of DFM.

        For each batch, features are extracted from the CNN.

        Args:
          batch (Dict[str, Tensor]): Input batch
          _: Index of the batch.

        Returns:
          Deep CNN features.
        """
        embedding = self.model.get_features(batch["image"]).squeeze()

        # NOTE: `self.embedding` appends each batch embedding to
        #   store the training set embedding. We manually append these
        #   values mainly due to the new order of hooks introduced after PL v1.4.0
        #   https://github.com/PyTorchLightning/pytorch-lightning/pull/7357
        self.embeddings.append(embedding)

    def on_validation_start(self) -> None:
        """Fit a PCA transformation and a Gaussian model to dataset."""
        # NOTE: Previous anomalib versions fit Gaussian at the end of the epoch.
        #   This is not possible anymore with PyTorch Lightning v1.4.0 since validation
        #   is run within train epoch.
        logger.info("Aggregating the embedding extracted from the training set.")
        embeddings = torch.vstack(self.embeddings)

        logger.info("Fitting a PCA and a Gaussian model to dataset.")
        self.model.fit(embeddings)

    def validation_step(self, batch, _):  # pylint: disable=arguments-differ
        """Validation Step of DFM.

        Similar to the training step, features are extracted from the CNN for each batch.

        Args:
          batch (List[Dict[str, Any]]): Input batch

        Returns:
          Dictionary containing FRE anomaly scores and anomaly maps.
        """
        if self.score_type == "fre":
            batch["anomaly_maps"], batch["pred_scores"] = self.model(batch["image"])
        elif self.score_type == "nll":
            batch["pred_scores"] = self.model(batch["image"])

        return batch
