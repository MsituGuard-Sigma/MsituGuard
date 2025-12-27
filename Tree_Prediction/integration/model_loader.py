import joblib
import os

class SurvivalModel:
    def __init__(self):
        base = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(base, "..", "training", "models")

        self.model = joblib.load(os.path.join(model_dir, "tree_survival_model.pkl"))
        self.scaler = joblib.load(os.path.join(model_dir, "tree_scaler.pkl"))
        self.encoders = joblib.load(os.path.join(model_dir, "tree_encoders.pkl"))
        self.feature_columns = joblib.load(os.path.join(model_dir, "feature_columns.pkl"))

    def predict(self, df):
        df_scaled = self.scaler.transform(df[self.feature_columns])
        prob = self.model.predict_proba(df_scaled)[0][1]
        return round(prob, 3)

model_loader = SurvivalModel()
