"""Anomaly Detection via Reverse Distillation from One-Class Embedding.

https://arxiv.org/abs/2201.10703v2
"""

# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

from typing import Dict, Tuple, Union

from omegaconf import DictConfig, ListConfig
from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning.utilities.cli import MODEL_REGISTRY
from torch import Tensor, optim

from anomalib.models.components import AnomalyModule
from anomalib.models.components.feature_extraction import FeatureExtractorParams

from .loss import ReverseDistillationLoss
from .torch_model import ReverseDistillationModel


@MODEL_REGISTRY
class ReverseDistillation(AnomalyModule):
    """PL Lightning Module for Reverse Distillation Algorithm.

    Args:
        input_size (Tuple[int, int]): Size of model input
        feature_extractor (FeatureExtractorParams): Feature extractor params
    """

    def __init__(
        self,
        input_size: Tuple[int, int],
        feature_extractor: FeatureExtractorParams,
        anomaly_map_mode: str,
        lr: float,
        beta1: float,
        beta2: float,
    ):
        super().__init__()
        self.model = ReverseDistillationModel(
            feature_extractor_params=feature_extractor,
            input_size=input_size,
            anomaly_map_mode=anomaly_map_mode,
        )
        self.loss = ReverseDistillationLoss()
        # TODO: LR should be part of optimizer in config.yaml! Since reverse distillation has custom
        #   optimizer this is to be addressed later.
        self.learning_rate = lr
        self.beta1 = beta1
        self.beta2 = beta2

    def configure_optimizers(self):
        """Configures optimizers for decoder and bottleneck.

        Note:
            This method is used for the existing CLI.
            When PL CLI is introduced, configure optimizers method will be
                deprecated, and optimizers will be configured from either
                config.yaml file or from CLI.

        Returns:
            Optimizer: Adam optimizer for each decoder
        """
        return optim.Adam(
            params=list(self.model.decoder.parameters()) + list(self.model.bottleneck.parameters()),
            lr=self.learning_rate,
            betas=(self.beta1, self.beta2),
        )

    def training_step(self, batch, _) -> Dict[str, Tensor]:  # type: ignore
        """Training Step of Reverse Distillation Model.

        Features are extracted from three layers of the Encoder model. These are passed to the bottleneck layer
        that are passed to the decoder network. The loss is then calculated based on the cosine similarity between the
        encoder and decoder features.

        Args:
          batch (Tensor): Input batch
          _: Index of the batch.

        Returns:
          Feature Map
        """
        loss = self.loss(*self.model(batch["image"]))
        self.log("train_loss", loss.item(), on_epoch=True, prog_bar=True, logger=True)
        return {"loss": loss}

    def validation_step(self, batch, _):  # pylint: disable=arguments-differ
        """Validation Step of Reverse Distillation Model.

        Similar to the training step, encoder/decoder features are extracted from the CNN for each batch, and
        anomaly map is computed.

        Args:
          batch (Tensor): Input batch
          _: Index of the batch.

        Returns:
          Dictionary containing images, anomaly maps, true labels and masks.
          These are required in `validation_epoch_end` for feature concatenation.
        """
        batch["anomaly_maps"] = self.model(batch["image"])
        return batch


class ReverseDistillationLightning(ReverseDistillation):
    """PL Lightning Module for Reverse Distillation Algorithm.

    Args:
        hparams(Union[DictConfig, ListConfig]): Model parameters
    """

    def __init__(self, hparams: Union[DictConfig, ListConfig]):
        super().__init__(
            input_size=hparams.model.input_size,
            feature_extractor=hparams.model.feature_extractor,
            anomaly_map_mode=hparams.model.anomaly_map_mode,
            lr=hparams.model.lr,
            beta1=hparams.model.beta1,
            beta2=hparams.model.beta2,
        )
        self.hparams: Union[DictConfig, ListConfig]  # type: ignore
        self.save_hyperparameters(hparams)

    def configure_callbacks(self):
        """Configure model-specific callbacks.

        Note:
            This method is used for the existing CLI.
            When PL CLI is introduced, configure callback method will be
                deprecated, and callbacks will be configured from either
                config.yaml file or from CLI.
        """
        early_stopping = EarlyStopping(
            monitor=self.hparams.model.early_stopping.metric,
            patience=self.hparams.model.early_stopping.patience,
            mode=self.hparams.model.early_stopping.mode,
        )
        return [early_stopping]
