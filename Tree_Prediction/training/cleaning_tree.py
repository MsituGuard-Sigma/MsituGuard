import pandas as pd
import numpy as np
import random

def clean_tree_dataset():
    """
    Comprehensive data cleaning and feature engineering for tree survival dataset.
    
    This function performs:
    1. Removes useless columns with constant values
    2. Fixes soil types to match regional geology (data generation step)
    3. Adjusts survival rates for realistic failure patterns (data generation step)
    4. Creates engineered features for better model performance
    5. Validates data ranges and saves final dataset
    
    Note: Steps 2-3 are data generation, not cleaning of real data.
    """
    
    print("STARTING TREE DATASET CLEANING")
    print("=" * 50)
    
    #Load the verified dataset
    print("Loading dataset...")
    df = pd.read_csv('cleaned_tree_data_fixed_VERIFIED.csv')
    print(f"Original dataset shape: {df.shape}")
    
    #REMOVE USELESS COLUMNS
    #Remove columns with constant values (zero predictive power)
    print("\nSTEP 1: Removing useless columns...")
    columns_to_remove = [
        'urban_pressure',           # Same value (30.049) for all rows
        'forest_cover_trend',       # Same value (6.586) for all rows  
        'agricultural_pressure',    # Same value (46.621) for all rows
        'climate_enhanced',         # Same value (631.016) for all rows
        'carbon_value',            # Same value (15.0) for all rows
        'unep_datasets_integrated', # Metadata, not predictive
        'dataset_version',         # Constant value
        'creation_date',           # Future date, not relevant
        'synthetic_survival_data', # Always True
        'data_source_rainfall',    # Metadata
        'real_climate_data'        # Always True
    ]
    
    # Check which columns exist before removing
    existing_cols_to_remove = [col for col in columns_to_remove if col in df.columns]
    df = df.drop(columns=existing_cols_to_remove, axis=1)
    print(f"Removed {len(existing_cols_to_remove)} useless columns")
    print(f"New shape: {df.shape}")
    
    #FIX SOIL TYPES BY REGION
    # Data generation step: Make soil types geographically plausible
    print("\nFixing soil types by region...")
    
    # Define realistic soil types per region based on Kenya's geology
    region_soils = {
        'Central': ['Volcanic', 'Red Soil', 'Clay'],
        'Coast': ['Sandy', 'Loam', 'Clay'],
        'Eastern': ['Red Soil', 'Clay', 'Loam'],
        'Northern': ['Sandy', 'Rocky', 'Red Soil'],
        'North Eastern': ['Sandy', 'Rocky', 'Red Soil'],
        'Rift Valley': ['Volcanic', 'Red Soil', 'Clay'],
        'Western': ['Loam', 'Clay', 'Volcanic'],
        'Nyanza': ['Loam', 'Clay', 'Volcanic'],
        'Nairobi': ['Red Soil', 'Clay', 'Rocky']
    }
    
    def correct_soil_type(row):
        region = row['region']
        current_soil = row['soil_type']
        valid_soils = region_soils.get(region, [current_soil])
        
        if current_soil not in valid_soils:
            return random.choice(valid_soils)
        return current_soil
    
    # Set random seed for reproducibility
    random.seed(42)
    df['soil_type'] = df.apply(correct_soil_type, axis=1)
    print("Fixed soil types to match regional geology")
    
    #FIX TARGET VARIABLES
    # Data generation step: Create realistic failure patterns
    print("\nFixing target variables...")
    
    # Remove unrealistic survival_probability column
    if 'survival_probability' in df.columns:
        df = df.drop('survival_probability', axis=1)
        print("Removed unrealistic survival_probability column")
    
    # Fix survived column - increase failure rate for harsh conditions
    print("Increasing failure rate for harsh conditions...")
    
    # Identify records with harsh conditions that should have higher failure rates
    harsh_conditions = (
        (df['rainfall_mm'] < 300) |  # Very arid
        (df['temperature_c'] > 28) |  # Very hot
        (df['soil_type'].isin(['Rocky', 'Sandy'])) |  # Poor soils
        (df['altitude_m'] > 2000) |  # Very high altitude
        (df['care_level'] == 'Low')  # Poor care
    )
    
    # Convert 25% of harsh condition records to failures
    harsh_indices = df[harsh_conditions].index
    fail_count = int(len(harsh_indices) * 0.25)
    
    np.random.seed(42)
    fail_indices = np.random.choice(harsh_indices, fail_count, replace=False)
    df.loc[fail_indices, 'survived'] = False
    
    # Add species-specific failure conditions
    print("Adding species-specific failure conditions...")
    
    species_fail_conditions = {
        'Cypress': (df['rainfall_mm'] < 500) | (df['temperature_c'] > 25),
        'Bamboo': (df['rainfall_mm'] < 800),
        'Eucalyptus': (df['rainfall_mm'] < 300),
        'Acacia': (df['temperature_c'] < 15),  # Acacia doesn't like cold
        'Pine': (df['temperature_c'] > 30) | (df['altitude_m'] < 1000),  # Pine prefers cool highlands
        'Cedar': (df['rainfall_mm'] < 600) | (df['temperature_c'] > 28),
        'Neem': (df['temperature_c'] < 18),  # Neem prefers warm climates
        'Grevillea': (df['rainfall_mm'] < 400),
        'Wattle': (df['soil_ph'] > 8.0),  # Wattle prefers slightly acidic soil
        'Casuarina': (df['rainfall_mm'] > 1500),  # Casuarina doesn't like too much water
        'Jacaranda': (df['temperature_c'] < 16),  # Jacaranda prefers warm climates
        'Indigenous Mix': (df['care_level'] == 'Low')  # Indigenous needs some care initially
    }
    
    for species, condition in species_fail_conditions.items():
        species_mask = df['tree_species'] == species
        species_indices = df[species_mask & condition].index
        if len(species_indices) > 0:
            fail_count = int(len(species_indices) * 0.30)  # 30% failure for wrong conditions
            if fail_count > 0:
                fail_indices = np.random.choice(species_indices, min(fail_count, len(species_indices)), replace=False)
                df.loc[fail_indices, 'survived'] = False
    
    survival_rate = df['survived'].mean()
    print(f"Final survival rate after species-specific failures: {survival_rate:.1%}")
    
    #FEATURE ENGINEERING
    # Create derived features to improve model performance
    print("\nSTEP 4: Feature engineering...")
    
    # Water balance - higher values = better water availability
    df['water_balance'] = df['rainfall_mm'] / (df['temperature_c'] + 1)
    
    # High altitude indicator - many species have altitude preferences
    df['is_high_altitude'] = df['altitude_m'] > 1500
    
    # Soil acidity - some trees prefer acidic vs alkaline soils
    df['soil_acidity'] = df['soil_ph'] < 7.0
    #Climate zone based on rainfall
    def get_climate_zone(rainfall):
        if rainfall < 300:
            return 'Extremely_Arid'
        elif rainfall < 500:
            return 'Arid'
        elif rainfall < 800:
            return 'Semi_Arid'
        elif rainfall < 1200:
            return 'Sub_Humid'
        else:
            return 'Humid'
    
    df['climate_zone'] = df['rainfall_mm'].apply(get_climate_zone)
    
    #Temperature category
    def get_temp_category(temp):
        if temp < 18:
            return 'Cool'
        elif temp < 25:
            return 'Moderate'
        else:
            return 'Hot'
    
    df['temp_category'] = df['temperature_c'].apply(get_temp_category)
    
    print("Created 5 new engineered features:")
    print("- water_balance: rainfall/temperature ratio for water availability")
    print("- is_high_altitude: boolean for altitude > 1500m")
    print("- soil_acidity: boolean for pH < 7.0")
    print("- climate_zone: 5 categories based on rainfall")
    print("- temp_category: Cool/Moderate/Hot temperature groups")
    
    #Data validation
    print("\nValidating data ranges...")
    
    def validate_data_ranges(df):
        try:
            assert df['rainfall_mm'].between(100, 2500).all(), "Unrealistic rainfall values found"
            assert df['temperature_c'].between(10, 35).all(), "Unrealistic temperature values found"
            assert df['soil_ph'].between(4.5, 9.0).all(), "Unrealistic soil pH values found"
            assert df['altitude_m'].between(0, 3000).all(), "Unrealistic altitude values found"
            assert df['tree_age_months'].between(1, 120).all(), "Unrealistic tree age values found"
            print("All value ranges are realistic")
            return True
        except AssertionError as e:
            print(f"Validation error: {e}")
            return False
    
    validation_passed = validate_data_ranges(df)
    if not validation_passed:
        print("WARNING: Data validation failed - check your data!")
    
    #DATA QUALITY CHECKS
    #Validate data integrity before saving
    print("\nData quality checks...")
    
    #Check for missing values
    missing_values = df.isnull().sum()
    if missing_values.sum() > 0:
        print("Missing values found:")
        print(missing_values[missing_values > 0])
    else:
        print("No missing values found")
    
    #Check data types
    print(f"\nData types:")
    print(df.dtypes.value_counts())
    
    #Check target variable distribution
    print(f"\nTarget variable distribution:")
    print(df['survived'].value_counts(normalize=True))
    
    #SAVE CLEANED DATASET
    #Export final dataset for model training
    print("\nSaving cleaned dataset...")
    
    output_file = 'cleaned_tree_data_FINAL.csv'
    df.to_csv(output_file, index=False)
    
    print(f"CLEANING COMPLETED!")
    print(f"Final dataset shape: {df.shape}")
    print(f"Saved as: {output_file}")
    
    #Summary statistics
    print(f"\nFINAL DATASET SUMMARY:")
    print(f"- Total records: {len(df):,}")
    print(f"- Features: {len(df.columns)}")
    print(f"- Survival rate: {df['survived'].mean():.1%}")
    
    return df

def analyze_dataset_comprehensive():
    """
    Comprehensive dataset analysis for ML model preparation.
    
    Analyzes:
    - Class imbalance in target variable
    - Feature correlations and multicollinearity
    - Key insights about tree survival patterns
    - Feature engineering effectiveness
    """
    print("\nCOMPREHENSIVE DATASET ANALYSIS")
    print("=" * 50)
    
    #Load cleaned dataset
    df = pd.read_csv('cleaned_tree_data_FINAL.csv')
    print(f"Dataset shape: {df.shape}")
    
    #CLASS IMBALANCE ANALYSIS
    print("\nCLASS IMBALANCE ANALYSIS")
    print("-" * 30)
    survived_counts = df['survived'].value_counts()
    survived_pct = df['survived'].value_counts(normalize=True) * 100
    
    print(f"Survived: {survived_counts[True]:,} ({survived_pct[True]:.1f}%)")
    print(f"Failed: {survived_counts[False]:,} ({survived_pct[False]:.1f}%)")
    
    imbalance_ratio = survived_counts[True] / survived_counts[False]
    if imbalance_ratio > 3:
        print(f"HIGH class imbalance (ratio: {imbalance_ratio:.1f}) - use SMOTE or class_weight='balanced'")
    elif imbalance_ratio > 1.5:
        print(f"MODERATE class imbalance (ratio: {imbalance_ratio:.1f}) - use class_weight='balanced'")
    else:
        print(f"BALANCED classes (ratio: {imbalance_ratio:.1f})")
    
    #CORRELATION ANALYSIS
    print("\n2. CORRELATION ANALYSIS")
    print("-" * 30)
    
    #Select numeric columns for correlation
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    correlation_matrix = df[numeric_cols].corr()
    
    #Find high correlations (>0.8)
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            corr_val = abs(correlation_matrix.iloc[i, j])
            if corr_val > 0.8:
                col1, col2 = correlation_matrix.columns[i], correlation_matrix.columns[j]
                high_corr_pairs.append((col1, col2, corr_val))
    
    if high_corr_pairs:
        print("HIGH CORRELATIONS FOUND (>0.8):")
        for col1, col2, corr in high_corr_pairs:
            print(f"  {col1} <-> {col2}: {corr:.3f}")
        print("Consider removing one feature from each pair")
    else:
        print("No high correlations (>0.8) found")
    
    #Features most correlated with survival
    if 'survived' in df.columns:
        #Convert boolean to numeric for correlation
        df_corr = df.copy()
        df_corr['survived'] = df_corr['survived'].astype(int)
        
        target_corr = df_corr[numeric_cols].corrwith(df_corr['survived']).abs().sort_values(ascending=False)
        print("\nFeatures most correlated with survival:")
        for feature, corr in target_corr.head(5).items():
            if feature != 'survived':
                print(f"  {feature}: {corr:.3f}")
    
    #ANSWER KEY QUESTIONS
    print("\nKEY INSIGHTS")
    print("-" * 30)
    
    #Which tree species have highest survival rate in arid regions?
    arid_regions = df[df['climate_zone'].isin(['Arid', 'Extremely_Arid'])]
    if len(arid_regions) > 0:
        species_survival_arid = arid_regions.groupby('tree_species')['survived'].agg(['count', 'mean']).sort_values('mean', ascending=False)
        species_survival_arid = species_survival_arid[species_survival_arid['count'] >= 10]  # Min 10 samples
        
        print("\nBest tree species for arid regions:")
        for species, row in species_survival_arid.head(3).iterrows():
            print(f"  {species}: {row['mean']:.1%} survival ({row['count']} samples)")
    
    #How does soil pH affect survival by species?
    print("\nSoil pH impact by species (avg pH for survived vs failed):")
    ph_analysis = df.groupby(['tree_species', 'survived'])['soil_ph'].mean().unstack()
    for species in ph_analysis.index[:5]:  # Top 5 species
        if not pd.isna(ph_analysis.loc[species, True]) and not pd.isna(ph_analysis.loc[species, False]):
            survived_ph = ph_analysis.loc[species, True]
            failed_ph = ph_analysis.loc[species, False]
            print(f"  {species}: Survived={survived_ph:.1f}, Failed={failed_ph:.1f}")
    
    #Most effective planting method by altitude
    print("\nBest planting methods by altitude:")
    altitude_groups = pd.cut(df['altitude_m'], bins=[0, 1000, 1500, 3000], labels=['Low', 'Medium', 'High'])
    method_altitude = df.groupby([altitude_groups, 'planting_method'])['survived'].mean().unstack()
    
    for altitude in method_altitude.index:
        best_method = method_altitude.loc[altitude].idxmax()
        best_rate = method_altitude.loc[altitude].max()
        print(f"  {altitude} altitude: {best_method} ({best_rate:.1%} survival)")
    
    #Water source impact in low-rainfall areas
    low_rainfall = df[df['rainfall_mm'] < 500]
    if len(low_rainfall) > 0:
        water_source_impact = low_rainfall.groupby('water_source')['survived'].agg(['count', 'mean']).sort_values('mean', ascending=False)
        water_source_impact = water_source_impact[water_source_impact['count'] >= 5]
        
        print("\nWater source effectiveness in low-rainfall areas:")
        for source, row in water_source_impact.iterrows():
            print(f"  {source}: {row['mean']:.1%} survival ({row['count']} samples)")
    
    #FEATURE ENGINEERING EVALUATION
    print("\nFEATURE ENGINEERING RECOMMENDATIONS")
    print("-" * 30)
    
    #Evaluate engineered features effectiveness
    engineered_features = ['water_balance', 'is_high_altitude', 'soil_acidity', 'climate_zone']
    existing_engineered = [f for f in engineered_features if f in df.columns]
    
    if existing_engineered:
        print("Engineered features correlation with survival:")
        for feature in existing_engineered:
            if df[feature].dtype in ['bool', 'int64', 'float64']:
                corr = df[feature].astype(int).corr(df['survived'].astype(int))
                print(f"  {feature}: {abs(corr):.3f}")
    
    #Suggest interaction terms
    print("\nSuggested interaction terms:")
    print("  - rainfall_mm × temperature_c (climate stress)")
    print("  - soil_ph × tree_species (species-soil compatibility)")
    print("  - altitude_m × planting_season (seasonal altitude effects)")
    
    return df

def add_realistic_altitude_variation():
    """
    Optional: Add realistic altitude variation within counties.
    This addresses the geographical simplification issue identified in analysis.
    """
    print("\nADDING REALISTIC ALTITUDE VARIATION")
    print("-" * 40)
    
    df = pd.read_csv('cleaned_tree_data_FINAL.csv')
    
    #Real-world altitude ranges for Kenyan counties
    county_altitude_ranges = {
        'Mombasa': (0, 100),
        'Kiambu': (1450, 2350), 
        'Turkana': (360, 2000),
        'Garissa': (20, 400),
        'Nakuru': (1600, 3000),
        'Meru': (900, 5199),
        'Eldoret': (1800, 2500),
        'Kakamega': (1200, 2000),
        'Kisumu': (1100, 1400),
        'Machakos': (1000, 1800),
        'Nyeri': (1200, 2400),
        'Thika': (1400, 2100),
        'Embu': (1100, 2500),
        'Kitui': (400, 1800)
    }
    
    #Add realistic variation
    np.random.seed(42)
    for county in df['county'].unique():
        county_mask = df['county'] == county
        if county in county_altitude_ranges:
            min_alt, max_alt = county_altitude_ranges[county]
            #Generate realistic altitude distribution
            county_count = county_mask.sum()
            new_altitudes = np.random.uniform(min_alt, max_alt, county_count)
            df.loc[county_mask, 'altitude_m'] = new_altitudes.astype(int)
    
    #Update high altitude feature
    df['is_high_altitude'] = df['altitude_m'] > 1500
    
    #Save updated dataset
    df.to_csv('cleaned_tree_data_REALISTIC_GEO.csv', index=False)
    
    print("Created realistic altitude variation:")
    for county in df['county'].unique()[:5]:
        county_data = df[df['county'] == county]['altitude_m']
        print(f"  {county}: {county_data.min()}-{county_data.max()}m (range: {county_data.max()-county_data.min()}m)")
    
    print("\nSaved as: cleaned_tree_data_REALISTIC_GEO.csv")
    return df

def validate_geographical_data():
    """
    Validate geographical data accuracy and identify limitations.
    
    Checks for:
    - Altitude variation within counties (should vary naturally)ould vary naturally)
    - Soil type diversity within counties (real counties have multiple soil types)
    - Overall assessment of geographical realism
    """
    print("\nGEOGRAPHICAL DATA VALIDATION")
    print("-" * 30)
    
    df = pd.read_csv('cleaned_tree_data_FINAL.csv')
    
    #Check altitude variation within counties
    county_altitude = df.groupby('county')['altitude_m'].agg(['min', 'max', 'nunique'])
    county_altitude['range'] = county_altitude['max'] - county_altitude['min']
    
    print("Altitude variation by county:")
    print(f"Counties with NO altitude variation: {(county_altitude['range'] == 0).sum()}/{len(county_altitude)}")
    
    #Show examples of problematic counties
    no_variation = county_altitude[county_altitude['range'] == 0]
    if len(no_variation) > 0:
        print("\nCounties with fixed altitude (UNREALISTIC):")
        for county, row in no_variation.head(5).iterrows():
            print(f"  {county}: {row['min']}m (should vary)")
    
    #Check soil type variation within counties
    county_soil = df.groupby('county')['soil_type'].nunique()
    limited_soil = county_soil[county_soil <= 2]
    
    print(f"\nCounties with limited soil diversity: {len(limited_soil)}/{len(county_soil)}")
    if len(limited_soil) > 0:
        print("Counties with ≤2 soil types (SIMPLIFIED):")
        for county, soil_count in limited_soil.head(5).items():
            soils = df[df['county'] == county]['soil_type'].unique()
            print(f"  {county}: {soil_count} types - {list(soils)}")
    
    #Overall assessment
    print("\nGEOGRAPHICAL DATA ASSESSMENT:")
    print("[OK] SUITABLE FOR: Prototype/proof-of-concept model")
    print("[X] NOT SUITABLE FOR: Production deployment in Kenya")
    print("\nREASONS:")
    print("- Fixed altitude per county (ignores topographical variation)")
    print("- Simplified soil distribution (real counties have more diversity)")
    print("- Missing micro-climate variations within regions")
    
    print("\nOPTIONAL FIX:")
    print("Run add_realistic_altitude_variation() to create geographically accurate dataset")
    
    return df

def generate_model_recommendations():
    """
    Generate ML model recommendations based on dataset analysis.
    
    Provides:
    - Model selection recommendations based on class imbalance
    - Feature encoding requirements
    - Model limitations due to geographical simplification
    """
    print("\nML MODEL RECOMMENDATIONS")
    print("-" * 30)
    
    df = pd.read_csv('cleaned_tree_data_FINAL.csv')
    
    #Check class balance for model selection
    survival_rate = df['survived'].mean()
    
    print("Recommended approaches:")
    if survival_rate < 0.3 or survival_rate > 0.7:
        print("  - Use class_weight='balanced' in RandomForest")
        print("  - Consider SMOTE for oversampling minority class")
        print("  - Use stratified train-test split")
    
    print("  - RandomForest: Good for mixed data types and feature importance")
    print("  - XGBoost: Better performance with proper tuning")
    print("  - Logistic Regression: Good baseline with feature engineering")
    
    #Feature selection recommendations
    categorical_features = df.select_dtypes(include=['object', 'bool']).columns.tolist()
    numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()
    
    print(f"\nFeature encoding needed:")
    print(f"  - Categorical features ({len(categorical_features)}): {categorical_features[:3]}...")
    print(f"  - Numeric features ({len(numeric_features)}): {numeric_features[:3]}...")
    
    print("\nMODEL LIMITATIONS (due to geographical simplification):")
    print("- Will learn county-specific patterns rather than true environmental factors")
    print("- Poor generalization to new locations within same counties")
    print("- Overfit to simplified geographical assumptions")
    
    return df

#Main execution block
if __name__ == "__main__":
    print("TREE SURVIVAL DATASET PROCESSING")
    print("=" * 50)
    print("This script performs data generation and analysis for tree survival prediction.")
    print("Note: This creates synthetic realistic data, not cleaning of real-world data.\n")
    
    #Generate and clean dataset
    clean_tree_dataset()
    
    #Analyze dataset for ML readiness
    analyze_dataset_comprehensive()
    
    #Validate geographical accuracy
    validate_geographical_data()
    
    #geographical variation
    create_realistic = input("\nCreate realistic altitude variation? (y/n): ").lower().strip()
    if create_realistic == 'y':
        add_realistic_altitude_variation()
        print("Use 'cleaned_tree_data_REALISTIC_GEO.csv' for better geographical accuracy")
    
    #model recommendations
    generate_model_recommendations()
    
    print("\n" + "=" * 50)
    print("PROCESSING COMPLETE")
    print("Dataset ready for prototype model training.")
    print("File saved: cleaned_tree_data_FINAL.csv")