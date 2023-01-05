from pathlib import Path
from typing import List, Optional, Union

from omegaconf import DictConfig, ListConfig

from anomalib.config import get_configurable_parameters

from .dataset import get_dataset_path


def get_test_configurable_parameters(
    dataset_path: Optional[str] = None,
    model_name: Optional[str] = None,
    config_path: Optional[Union[Path, str]] = None,
) -> Union[DictConfig, ListConfig]:
    """Get configurable parameters for testing.

    Args:
        datset_path: Optional[Path]: Path to dataset
        model_name: Optional[str]:  (Default value = None)
        config_path: Optional[Union[Path, str]]:  (Default value = None)

    Returns:
        Union[DictConfig, ListConfig]: Configurable parameters in DictConfig object.
    """

    config = get_configurable_parameters(model_name, config_path)

    # Update path to match the dataset path in the test image/runner
    config.data.init_args.root = get_dataset_path() if dataset_path is None else dataset_path

    return config
