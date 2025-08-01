"""
Configuration settings for customer segmentation model.
"""

import os

# Data configuration
DEFAULT_DATA_FILE = 'customer_segmentation_data.csv'
DATA_DIR = os.environ.get('DATA_DIR', '/opt/ml/input/data/training')
MODEL_DIR = os.environ.get('MODEL_DIR', '/opt/ml/model')

# Model hyperparameters
DEFAULT_N_CLUSTERS = 3
DEFAULT_N_COMPONENTS = 1

# Training configuration
DEFAULT_INSTANCE_TYPE = 'ml.m5.large'
DEFAULT_FRAMEWORK_VERSION = '1.2-1'

# Environment variables for SageMaker consistency
SAGEMAKER_ENV_VARS = {
    'MODEL_DIR': MODEL_DIR,
    'DATA_DIR': DATA_DIR
}