# MsituGuard - Environmental Protection Platform

MsituGuard is an AI-assisted environmental monitoring and tree conservation platform for Kenya. It helps communities report environmental threats, supports organizations reviewing those reports, and guides tree planting through county-based species recommendations and survival prediction.

## Key Features

### AI and Tree Survival Prediction
- Tree survival prediction using a GradientBoosting model and rule-based fallbacks.
- County and species recommendations based on local environmental data.
- Planting guidance using rainfall, temperature, altitude, soil, season, method, and care level.
- Optional Mistral AI integration for clearer explanations and care instructions.

### Environmental Reporting
- Environmental issue submission with location, coordinates, image evidence, and contact details.
- Report categories such as fire, illegal logging, pollution, deforestation, wildlife poaching, water contamination, air pollution, and waste dumping.
- Review status tracking for new, verified, and resolved reports.
- Organization dashboard and export tools for monitoring reports.

### Tree Planting and Rewards
- Tree planting registration for individual and public users.
- Before/after tree planting photos and verification workflow.
- Tree points, badges, and profile impact tracking.
- Separate tree photo registration flow with duplicate image detection.

### Community and Accounts
- User registration, login, profile management, and Google OAuth support.
- Community forum posts and comments.
- Account types for community members, donors, and organizations.
- Verification workflow for trusted contributors and organizations.

## Technology Stack

- Backend: Django 5, Python 3.11
- Database: SQLite for development, PostgreSQL-ready for production
- Deployment: Render, Gunicorn, WhiteNoise
- Media storage: local development storage or Cloudinary in production
- ML: scikit-learn, pandas, numpy, joblib
- AI: Mistral API integration
- Frontend: Django templates, Bootstrap, CSS, JavaScript

## Quick Start

```bash
git clone https://github.com/MsituGuard-Sigma/MsituGuard.git
cd MsituGuard

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Local app: `http://localhost:8000`

Admin: `http://localhost:8000/admin`

## Environment Variables

Create a `.env` file for local development:

```env
SECRET_KEY=your-secret-key
DEBUG=true
DATABASE_URL=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=MsituGuard <noreply@msituguard.com>
MISTRAL_API_KEY=
OPENWEATHER_API_KEY=
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
GOOGLE_OAUTH2_CLIENT_ID=
GOOGLE_OAUTH2_CLIENT_SECRET=
LOCATIONIQ_API_KEY=
```

For production, use `DEBUG=false` or `DEBUG=release`.

## ML Model

The model can be rebuilt from the training data:

```bash
cd Tree_Prediction/training
python train_tree_model.py
```

Generated model files are stored in:

```text
Tree_Prediction/training/models/
```

The Render build scripts retrain the model during deployment so the saved model artifacts match the deployed scikit-learn version.

## Main Routes

- `/` - home page
- `/reports/new/` - submit environmental report
- `/environmental-reports/` - latest public reports
- `/organization-dashboard/` - organization review dashboard
- `/tree-prediction/` - tree survival prediction interface
- `/tree-initiative/` - tree initiative page
- `/plant-trees/` - register tree planting
- `/tree-registration/` - tree photo registration app
- `/forums/` - community forum

## Project Structure

```text
MsituGuard/
├── App/                    Main Django application
├── treeregistration/       Tree photo registration and badge app
├── Tree_Prediction/        ML training data, model artifacts, and integration files
├── crisis_communication/   Django project package
├── images/                 Project images
├── media/                  Local uploaded media
├── requirements.txt        Python dependencies
├── runtime.txt             Render Python version
├── render.yaml             Render service configuration
└── manage.py               Django management entrypoint
```

Note: the Django project package is still named `crisis_communication` for compatibility with existing settings, imports, and deployment commands. The product name is MsituGuard.

## MVP Status

MsituGuard is a working MVP. The core user value is already present:

- Communities can report environmental threats.
- Organizations/admins can review reports.
- Users can register tree planting activity.
- The platform can recommend species and estimate survival probability.
- Users can track environmental impact through points and badges.

## Deployment Notes

Render should use Python 3.11.9. This is pinned in:

- `runtime.txt`
- `.python-version`
- `render.yaml`

If Render still selects Python 3.13, clear the build cache and confirm the service is deploying the latest branch and commit.

## License

This project is licensed under the MIT License.
