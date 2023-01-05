"""Test Config Getter."""

# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

import pytest

from anomalib.config import get_configurable_parameters


class TestConfig:
    """Test Config Getter."""

    def test_get_configurable_parameters_return_correct_model_name(self):
        """Configurable parameter should return the correct model name."""
        model_name = "stfpm"
        configurable_parameters = get_configurable_parameters(model_name)
        assert configurable_parameters.model.class_path == f"anomalib.models.{model_name.title()}"

    def test_get_configurable_parameter_fails_with_none_arguments(self):
        """Configurable parameter should raise an error with none arguments."""
        with pytest.raises(ValueError):
            get_configurable_parameters()
