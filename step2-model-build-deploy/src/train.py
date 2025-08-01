#!/usr/bin/env python3
"""
SageMaker training script for customer segmentation model.
"""

import argparse
import os
import pandas as pd
import joblib
from sklearn.preprocessing import Normalizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import json
import shutil
from preprocessing import prepare_features_for_training, get_numerical_features, get_cluster_names
from config import DEFAULT_DATA_FILE, DEFAULT_N_CLUSTERS, DEFAULT_N_COMPONENTS


def train_model(args):
    """Train the customer segmentation model."""
    
    print("Starting training...")
    print(f"Data directory: {args.data_dir}")
    print(f"Model output path: {args.model_dir}")
    
    # Load training data
    train_file = os.path.join(args.data_dir, args.data_file)
    df = pd.read_csv(train_file)
    print(f"Loaded {len(df)} records")
    
    # Prepare features
    df_continuous, df_binary = prepare_features_for_training(df)
    
    # Normalize continuous features
    normalizer = Normalizer()
    scaled_continuous_features = normalizer.fit_transform(df_continuous)
    scaled_continuous_df = pd.DataFrame(scaled_continuous_features, columns=get_numerical_features())
    
    # Combine features
    processed_df = pd.concat([scaled_continuous_df, df_binary.reset_index(drop=True)], axis=1)
    
    # Train PCA
    pca = PCA(n_components=args.n_components)
    pca_features = pca.fit_transform(processed_df)
    
    # Train KMeans
    kmeans = KMeans(
        n_clusters=args.n_clusters, 
        init='k-means++', 
        n_init=20, 
        max_iter=300, 
        random_state=42
    )
    cluster_labels = kmeans.fit_predict(pca_features)
    
    # Calculate metrics
    silhouette_avg = silhouette_score(pca_features, cluster_labels)
    calinski_harabasz = calinski_harabasz_score(pca_features, cluster_labels)
    davies_bouldin = davies_bouldin_score(pca_features, cluster_labels)
    
    print(f"Silhouette Score: {silhouette_avg:.4f}")
    print(f"Calinski-Harabasz Index: {calinski_harabasz:.4f}")
    print(f"Davies-Bouldin Index: {davies_bouldin:.4f}")
    
    # Save models
    joblib.dump(normalizer, os.path.join(args.model_dir, 'normalizer.pkl'))
    joblib.dump(pca, os.path.join(args.model_dir, 'pca_model.pkl'))
    joblib.dump(kmeans, os.path.join(args.model_dir, 'kmeans_model.pkl'))
    
    # Save cluster names
    with open(os.path.join(args.model_dir, 'cluster_names.json'), 'w') as f:
        json.dump(get_cluster_names(), f)
    
    # Save metadata
    metadata = {
        'n_clusters': args.n_clusters,
        'n_components': args.n_components,
        'silhouette_score': silhouette_avg,
        'calinski_harabasz_score': calinski_harabasz,
        'davies_bouldin_score': davies_bouldin,
        'feature_names': get_numerical_features(),
        'model_version': '1.0'
    }
    
    with open(os.path.join(args.model_dir, 'model_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Save metrics for SageMaker (replaces regex parsing)
    metrics = {
        "silhouette_score": {"value": silhouette_avg},
        "calinski_harabasz_score": {"value": calinski_harabasz},
        "davies_bouldin_score": {"value": davies_bouldin}
    }
    
    with open(os.path.join(args.model_dir, 'evaluation.json'), 'w') as f:
        json.dump(metrics, f)
    
    source_files = ['inference.py', 'preprocessing.py', 'config.py']

    print("Copying source files to model directory...")
    for source_file in source_files:
        src_path = os.path.join('/opt/ml/code', source_file)
        dest_path = os.path.join(args.model_dir, source_file)
        
        if os.path.exists(src_path):
            shutil.copy2(src_path, dest_path)
            print(f"✅ Copied {source_file}")
        else:
            print(f"❌ {source_file} not found at {src_path}")
    
    print("Training completed successfully!")
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR'))
    parser.add_argument('--data-dir', type=str, default=os.environ.get('SM_CHANNEL_TRAINING'))
    parser.add_argument('--data-file', type=str, default=DEFAULT_DATA_FILE)
    parser.add_argument('--n-clusters', type=int, default=DEFAULT_N_CLUSTERS)
    parser.add_argument('--n-components', type=int, default=DEFAULT_N_COMPONENTS)
    
    args = parser.parse_args()
    train_model(args)