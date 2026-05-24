import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.utils.class_weight import compute_sample_weight
import joblib
import os


# Species-environment compatibility scores based on ecological knowledge across Kenya climate zones.
# These give the model signal to differentiate species since the training data alone cannot.
# Update these values as you collect real outcome data from the field.
SPECIES_ENV_COMPAT = {
    ('Neem',          'Extremely_Arid'): 0.90,
    ('Neem',          'Semi_Arid'):      0.85,
    ('Neem',          'Sub_Humid'):      0.70,
    ('Neem',          'Humid'):          0.60,
    ('Bamboo',        'Sub_Humid'):      0.95,
    ('Bamboo',        'Humid'):          0.90,
    ('Bamboo',        'Semi_Arid'):      0.55,
    ('Bamboo',        'Extremely_Arid'): 0.20,
    ('Pine',          'Sub_Humid'):      0.90,
    ('Pine',          'Humid'):          0.85,
    ('Pine',          'Semi_Arid'):      0.55,
    ('Pine',          'Extremely_Arid'): 0.25,
    ('Cypress',       'Sub_Humid'):      0.85,
    ('Cypress',       'Humid'):          0.80,
    ('Cypress',       'Semi_Arid'):      0.60,
    ('Cypress',       'Extremely_Arid'): 0.25,
    ('Cedar',         'Sub_Humid'):      0.90,
    ('Cedar',         'Humid'):          0.80,
    ('Cedar',         'Semi_Arid'):      0.55,
    ('Cedar',         'Extremely_Arid'): 0.20,
    ('Eucalyptus',    'Sub_Humid'):      0.85,
    ('Eucalyptus',    'Humid'):          0.85,
    ('Eucalyptus',    'Semi_Arid'):      0.80,
    ('Eucalyptus',    'Extremely_Arid'): 0.50,
    ('Acacia',        'Semi_Arid'):      0.90,
    ('Acacia',        'Extremely_Arid'): 0.80,
    ('Acacia',        'Sub_Humid'):      0.80,
    ('Acacia',        'Humid'):          0.75,
    ('Grevillea',     'Sub_Humid'):      0.90,
    ('Grevillea',     'Semi_Arid'):      0.80,
    ('Grevillea',     'Humid'):          0.80,
    ('Grevillea',     'Extremely_Arid'): 0.40,
    ('Wattle',        'Sub_Humid'):      0.85,
    ('Wattle',        'Semi_Arid'):      0.80,
    ('Wattle',        'Humid'):          0.80,
    ('Wattle',        'Extremely_Arid'): 0.55,
    ('Casuarina',     'Sub_Humid'):      0.85,
    ('Casuarina',     'Semi_Arid'):      0.80,
    ('Casuarina',     'Humid'):          0.75,
    ('Casuarina',     'Extremely_Arid'): 0.55,
    ('Jacaranda',     'Sub_Humid'):      0.85,
    ('Jacaranda',     'Semi_Arid'):      0.80,
    ('Jacaranda',     'Humid'):          0.75,
    ('Jacaranda',     'Extremely_Arid'): 0.60,
    ('Indigenous Mix','Sub_Humid'):      0.82,
    ('Indigenous Mix','Semi_Arid'):      0.78,
    ('Indigenous Mix','Humid'):          0.78,
    ('Indigenous Mix','Extremely_Arid'): 0.65,
}

# Best propagation method per species based on agronomy knowledge.
# Used at inference when ML scores are too close to distinguish methods.
SPECIES_METHOD_PREFERENCE = {
    'Bamboo':         'Cutting',
    'Eucalyptus':     'Seedling',
    'Pine':           'Seedling',
    'Cypress':        'Seedling',
    'Cedar':          'Seedling',
    'Neem':           'Direct Seeding',
    'Acacia':         'Direct Seeding',
    'Wattle':         'Direct Seeding',
    'Grevillea':      'Seedling',
    'Indigenous Mix': 'Seedling',
    'Jacaranda':      'Seedling',
    'Casuarina':      'Seedling',
}


def train_tree_survival_model():
    """Train, calibrate, and save the tree survival prediction model."""

    base_dir   = os.path.dirname(os.path.abspath(__file__))
    data_path  = os.path.join(base_dir, 'cleaned_tree_data_FINAL.csv')
    models_dir = os.path.join(base_dir, 'models')

    print("Loading dataset...")
    df = pd.read_csv(data_path)
    print(f"Shape: {df.shape}")
    print(f"\nClass distribution:")
    print(df['survived'].value_counts())
    print(f"Survival rate: {df['survived'].mean():.1%}")

    # Add species-environment compatibility as a feature.
    # This is the primary signal that lets the model score species differently
    # across climate zones, since the raw training data treats all species as
    # equally likely in all environments.
    df['species_env_compat'] = df.apply(
        lambda r: SPECIES_ENV_COMPAT.get(
            (r['tree_species'], r['climate_zone']), 0.65
        ), axis=1
    )

    # Encode all categorical columns and store encoders for use at inference
    encoders = {}
    categorical_map = {
        'tree_species':    'species',
        'region':          'region',
        'county':          'county',
        'soil_type':       'soil_type',
        'planting_season': 'planting_season',
        'planting_method': 'planting_method',
        'care_level':      'care_level',
        'water_source':    'water_source',
        'climate_zone':    'climate_zone',
        'temp_category':   'temp_category',
    }
    for col, key in categorical_map.items():
        le = LabelEncoder()
        df[col + '_enc'] = le.fit_transform(df[col])
        encoders[key] = le

    # Derived numeric features.
    # The is_high_altitude threshold MUST stay at 1500 — ml_utils.py uses the same value.
    # Changing one without the other causes silent prediction errors.
    df['water_balance']    = df['rainfall_mm'] - (df['temperature_c'] * 20)
    df['is_high_altitude'] = (df['altitude_m'] > 1500).astype(int)
    df['soil_acidity']     = (df['soil_ph'] < 6.5).astype(int)

    feature_columns = [
        'tree_species_enc', 'region_enc', 'county_enc', 'soil_type_enc',
        'rainfall_mm', 'temperature_c', 'altitude_m', 'soil_ph',
        'planting_season_enc', 'planting_method_enc', 'care_level_enc', 'water_source_enc',
        'tree_age_months', 'water_balance', 'is_high_altitude', 'soil_acidity',
        'climate_zone_enc', 'temp_category_enc',
        'species_env_compat',
    ]

    X = df[feature_columns]
    y = df['survived'].astype(int)

    # Stratify keeps the same 77/23 survival ratio in both train and test splits
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Class weights: penalise missed deaths 3x more than missed survivals.
    # Without this the model ignores 80% of trees that die because predicting
    # survival is the easy path for an imbalanced dataset.
    sample_weights = compute_sample_weight(class_weight={0: 3, 1: 1}, y=y_train)

    # Model tuning rationale:
    # n_estimators=200 + learning_rate=0.05 gives a stable ensemble without overfitting.
    # max_depth=4 keeps individual trees shallow so they generalise.
    # subsample=0.8 introduces stochasticity that reduces variance.
    # min_samples_leaf=20 stops the model fitting noise in tiny leaf nodes.
    print("\nTraining model...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_leaf=20,
        random_state=42
    )
    model.fit(X_train, y_train, sample_weight=sample_weights)

    # Calibration makes the probability percentages shown to users actually mean
    # what they say. Newer scikit-learn versions no longer support cv='prefit' here.
    # We calibrate via cross-validation on the training split, then evaluate on X_test.
    print("Calibrating probabilities...")
    calibrated_model = CalibratedClassifierCV(estimator=model, cv=5, method='isotonic')
    calibrated_model.fit(X_train, y_train, sample_weight=sample_weights)

    # Evaluate on the test set using the calibrated model
    y_pred = calibrated_model.predict(X_test)
    y_prob = calibrated_model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    auc      = roc_auc_score(y_test, y_prob)

    print(f"\nMODEL PERFORMANCE:")
    print(f"  Accuracy : {accuracy:.3f}")
    print(f"  ROC-AUC  : {auc:.3f}")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Did not survive', 'Survived']))

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    print(f"Confusion Matrix:")
    print(f"  Correctly predicted survival   : {tp}")
    print(f"  Correctly predicted death      : {tn}")
    print(f"  Predicted survival, actually died : {fp}  ({fp/(tn+fp)*100:.0f}% of actual deaths missed)")
    print(f"  Predicted death, actually survived: {fn}")

    # Feature importance shows what the model actually learned
    importance = pd.DataFrame({
        'feature':    feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(f"\nTop 8 features by importance:")
    print(importance.head(8).to_string(index=False))

    # Spot-check that species now score differently across environments
    print("\nSpecies probability spread — Semi-Arid, Medium care:")
    for sp in sorted(df['tree_species'].unique()):
        sample = df[
            (df['climate_zone'] == 'Semi_Arid') &
            (df['care_level'] == 'Medium') &
            (df['tree_species'] == sp)
        ].head(1)
        if len(sample):
            p   = calibrated_model.predict_proba(sample[feature_columns])[0][1]
            bar = '█' * int(p * 20)
            print(f"  {sp:<20} {p:.1%}  {bar}")

    # Save all artifacts needed at inference time
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(calibrated_model,          os.path.join(models_dir, 'tree_survival_model.pkl'))
    # Compatibility: the Django loader expects a scaler artifact.
    # This model does not require scaling; we store None as a placeholder.
    joblib.dump(None,                      os.path.join(models_dir, 'tree_scaler.pkl'))
    joblib.dump(encoders,                  os.path.join(models_dir, 'tree_encoders.pkl'))
    joblib.dump(feature_columns,           os.path.join(models_dir, 'feature_columns.pkl'))
    joblib.dump(SPECIES_ENV_COMPAT,        os.path.join(models_dir, 'species_env_compat.pkl'))
    joblib.dump(SPECIES_METHOD_PREFERENCE, os.path.join(models_dir, 'species_method_pref.pkl'))

    print("\nArtifacts saved to:", models_dir)
    return calibrated_model, encoders, feature_columns


if __name__ == "__main__":
    train_tree_survival_model()