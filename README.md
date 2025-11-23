# 🌿 MsituGuard - Smart Tree Planting Platform

**Plant Trees Smarter with AI**

MsituGuard helps you plant trees that actually survive. Our AI tells you which trees will grow best in your location, you can report environmental problems in your area, and track your impact as you help restore Kenya's forests.

## ✨ What You Can Do

### 🌳 Smart Tree Planting
- **Find the Right Trees** - AI tells you which tree species will survive in your exact location
- **Get Survival Predictions** - Know your chances of success before you plant
- **Track Your Trees** - Register and monitor your tree planting progress
- **Earn Rewards** - Get points and badges for your environmental actions

### 📱 Report Environmental Problems
- **Take Photos** - Document environmental issues with your phone
- **Add Location** - Tag where problems are happening
- **Get Community Support** - Connect with others who care about the environment
- **Make Real Impact** - Help organizations respond to environmental threats

### 📈 See Your Impact
- **Personal Dashboard** - View all your tree planting and reporting activities
- **Community Forum** - Share experiences and learn from other tree planters
- **Progress Tracking** - Watch your environmental contribution grow over time

## 🚀 Technology Stack

### Backend & AI
- **Framework**: Django 5.0.3
- **Machine Learning**: scikit-learn, pandas, numpy
- **AI Models**: GradientBoosting Classifier + MISTRAL AI
- **AI Integration**: mistralai==1.0.1 for advanced environmental analysis
- **Data Processing**: Advanced feature engineering and model serialization

### Frontend & Design
- **Frontend**: HTML5, CSS3, JavaScript ES6+, Bootstrap 5
- **UI Framework**: Modern responsive design with CSS Grid/Flexbox
- **Icons**: Font Awesome 6.4+
- **Fonts**: Inter, Poppins (Google Fonts)

### Infrastructure & Services
- **Database**: PostgreSQL (Production), SQLite (Development)
- **Media Storage**: Cloudinary CDN for images and file uploads
- **Deployment**: Render.com with automatic deployments
- **Version Control**: Git with comprehensive commit history

## 🧠 AI Model Performance

### Tree Survival Prediction System
- **Hybrid Approach**: ML Model (40%) + Expert Knowledge Database (60%) + MISTRAL AI LLM
- **ML Algorithm**: GradientBoosting Classifier
- **Training Data**: 10,000+ Kenyan tree planting records
- **County Coverage**: All 47 Kenyan counties with species compatibility data
- **MISTRAL AI Integration**: Uses API key to enhance explanations and provide intelligent care instructions

### Key Prediction Factors
1. **Tree Species** - Native vs non-native adaptation
2. **County Environment** - Climate and soil compatibility
3. **Seasonal Timing** - Optimal planting seasons
4. **Planting Method** - Technique optimization
5. **Care Level** - Maintenance and monitoring intensity

## 🎯 How It Works

### For Everyone
- **Try Tree Prediction** - Get AI-powered species recommendations for any Kenyan county
- **See What Grows** - Get survival predictions and care instructions
- **Report Environmental Issues** - Submit reports with photos

### Create Free Account
- **Save Prediction History** - Track all your tree predictions
- **Register Tree Plantings** - Record and verify your tree planting activities
- **Join the Community** - Connect with other tree planters in forums
- **Earn Rewards** - Get points and badges for verified environmental actions

### For Organizations
- **Organization Dashboard** - Review and verify environmental reports and tree plantings
- **Track Community Impact** - See total trees planted and environmental reports
- **Export Data** - Download CSV reports for grants and documentation

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- pip (Python package manager)
- Git

### Quick Start
```bash
# Clone repository
git clone https://github.com/Melbride/MsituGuard.git
cd MsituGuard

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Database setup
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Access Points
- **Local Development**: `http://localhost:8000`
- **Admin Panel**: `http://localhost:8000/admin`
- **Tree Prediction**: `http://localhost:8000/tree-prediction/`
- **API Endpoints**: `http://localhost:8000/api/`

### ML Model Setup
```bash
# Pre-trained models are included in Tree_Prediction/training/models/
# Model files:
# - tree_survival_model.pkl (GradientBoosting model)
# - tree_scaler.pkl (StandardScaler for preprocessing)
# - tree_encoders.pkl (LabelEncoders for categorical features)
# - feature_columns.pkl (List of features used)

# To retrain models (optional):
cd Tree_Prediction/training
python train_tree_model.py
```

## 🌐 Try It Now

**Visit**: https://msituguard.onrender.com

### What's Working
- ✅ **AI Tree Predictions** - Get species recommendations for all 47 Kenyan counties
- ✅ **Hybrid AI System** - ML model + expert knowledge + MISTRAL AI explanations
- ✅ **Environmental Reporting** - Report problems with photos and location
- ✅ **Tree Registration** - Register and track tree planting activities
- ✅ **Organization Dashboard** - Verify reports and tree plantings
- ✅ **Rewards System** - Earn points and badges for verified actions
- ✅ **Community Forums** - Connect with other environmental champions
- ✅ **MISTRAL AI Explanations** - Get intelligent, context-aware planting advice
- ✅ **Data Export** - CSV export for reports and tree data
- ✅ **Mobile Friendly** - Responsive design works on all devices

## 📊 Project Structure

```
MsituGuard/
├── App/                          # Main Django application
│   ├── models.py               # Database models (County, Species, TreePlanting, etc.)
│   ├── views.py                # Main application views
│   ├── views_ml.py             # ML API endpoints for tree prediction
│   ├── mistral_ai.py           # MISTRAL AI integration
│   ├── ml_utils.py             # ML model utilities
│   ├── urls.py                 # URL routing
│   ├── templates/App/          # HTML templates
│   │   ├── tree_prediction.html # AI prediction interface
│   │   ├── home.html           # Landing page
│   │   ├── organization_dashboard.html # Organization dashboard
│   │   └── ...                 # Other templates
│   └── static/                 # CSS, JS, images
├── Tree_Prediction/            # AI/ML system
│   └── training/
│       ├── models/             # Pre-trained ML models (.pkl files)
│       ├── cleaned_tree_data_FINAL.csv # Training dataset
│       └── train_tree_model.py # Model training script
├── treeregistration/           # Tree registration app
├── crisis_communication/       # Django project settings
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🆕 Key Features

### AI-Powered Tree Prediction
- **County-Species Database**: Complete compatibility matrix for 47 Kenyan counties
- **Hybrid Prediction System**: Combines ML model with expert knowledge
- **MISTRAL AI Integration**: Generates intelligent explanations and care instructions
- **Seasonal Optimization**: Accounts for planting season performance
- **Risk Assessment**: Provides clear risk levels and alternative recommendations

### Environmental Impact Tracking
- **Tree Registration**: Public and authenticated user tree planting tracking
- **Environmental Reporting**: Photo-based issue reporting with verification workflow
- **Organization Verification**: Dashboard for organizations to verify community actions
- **Rewards System**: Points and badges for verified environmental contributions
- **MISTRAL AI Enhancement**: Intelligent analysis and recommendations throughout the platform

### Data Management
- **CSV Export**: Download reports and tree data for analysis
- **Prediction History**: Track all tree predictions for logged-in users
- **Community Forums**: Discussion platform for environmental topics
- **Mobile Responsive**: Works seamlessly on all device sizes

## 🔗 API Endpoints

### Tree Prediction APIs
- `POST /api/get-species-recommendations/` - Get recommended species for a county
- `POST /api/predict-tree-survival/` - Get AI survival prediction for specific species
- `GET /tree-prediction/` - Interactive tree prediction interface

### Data Management
- `POST /reports/new/` - Submit environmental report
- `POST /plant-trees/` - Register tree planting (authenticated users)
- `POST /public-tree-planting/` - Public tree registration
- `GET /export/reports/` - Export environmental reports (CSV)
- `GET /export/tree-data/` - Export tree planting data (CSV)

### Organization Features
- `GET /organization-dashboard/` - Organization verification dashboard
- `POST /update-report-status/<id>/` - Update report verification status
- `POST /update-tree-status/<id>/` - Update tree planting verification status

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Plant Trees That Actually Grow** 🌳✨

*MsituGuard - Smart Tree Planting for Everyone*