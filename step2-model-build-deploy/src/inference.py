#!/usr/bin/env python3
"""SageMaker inference script for customer segmentation model."""

import json
import joblib
import pandas as pd
import numpy as np
import os
import logging
import sys
from io import StringIO

sys.path.append(os.path.dirname(__file__))
from preprocessing import prepare_features_for_training, get_numerical_features

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def model_fn(model_dir):
    """Load model artifacts."""
    logger.info(f"Loading models from {model_dir}")
    
    try:
        normalizer = joblib.load(os.path.join(model_dir, 'normalizer.pkl'))
        pca_model = joblib.load(os.path.join(model_dir, 'pca_model.pkl'))
        kmeans_model = joblib.load(os.path.join(model_dir, 'kmeans_model.pkl'))
        
        with open(os.path.join(model_dir, 'cluster_names.json'), 'r') as f:
            cluster_names = json.load(f)
            
        with open(os.path.join(model_dir, 'model_metadata.json'), 'r') as f:
            metadata = json.load(f)
            
        logger.info("Models loaded successfully")
        
        return {
            'normalizer': normalizer,
            'pca_model': pca_model,
            'kmeans_model': kmeans_model,
            'cluster_names': cluster_names,
            'metadata': metadata
        }
        
    except Exception as e:
        logger.error(f"Error loading models: {str(e)}")
        raise


def input_fn(request_body, content_type):
    """Parse and validate input data."""
    logger.info(f"Processing input: {content_type}")
    
    try:
        if content_type == 'application/json':
            input_data = json.loads(request_body)
            
            if 'instances' in input_data:
                df = pd.DataFrame(input_data['instances'])
            elif isinstance(input_data, list):
                df = pd.DataFrame(input_data)
            elif isinstance(input_data, dict):
                df = pd.DataFrame([input_data])
            else:
                raise ValueError("Unsupported JSON format")
                
        elif content_type == 'text/csv':
            df = pd.read_csv(StringIO(request_body))
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
            
        # Validate required columns
        required_columns = ['Age', 'Income', 'Purchases', 'Gender']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        if 'Customer_ID' not in df.columns:
            df['Customer_ID'] = range(len(df))
            
        logger.info(f"Input validated: {df.shape}")
        return df
        
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise


def predict_fn(input_data, model):
    """Make predictions."""
    logger.info("Starting prediction")
    
    try:
        normalizer = model['normalizer']
        pca_model = model['pca_model']
        kmeans_model = model['kmeans_model']
        cluster_names = model['cluster_names']
        
        df_continuous, df_binary = prepare_features_for_training(input_data)
        numerical_features = get_numerical_features()
        
        scaled_continuous_features = normalizer.transform(df_continuous)
        scaled_continuous_df = pd.DataFrame(scaled_continuous_features, columns=numerical_features)
        
        processed_df = pd.concat([scaled_continuous_df, df_binary.reset_index(drop=True)], axis=1)
        pca_features = pca_model.transform(processed_df)
        cluster_predictions = kmeans_model.predict(pca_features)
        
        segment_names = [cluster_names.get(str(cluster), f"Cluster_{cluster}") for cluster in cluster_predictions]
        
        distances = kmeans_model.transform(pca_features)
        min_distances = np.min(distances, axis=1)
        
        results = []
        for cluster, segment, distance in zip(cluster_predictions, segment_names, min_distances):
            results.append({
                'cluster_id': int(cluster),
                'segment': segment,
                'confidence': float(1.0 / (1.0 + distance)),
                'distance_to_center': float(distance)
            })
            
        logger.info(f"Predictions completed: {len(results)} samples")
        
        return {
            'predictions': results,
            'model_metadata': model['metadata']
        }
        
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}")
        raise


def output_fn(prediction, accept):
    """Format output."""
    try:
        if accept == 'application/json':
            return json.dumps(prediction)
        else:
            logger.warning(f"Unsupported accept type {accept}, defaulting to JSON")
            return json.dumps(prediction)
            
    except Exception as e:
        logger.error(f"Error formatting output: {str(e)}")
        raise