# 🌿 MsituGuard - Tree Survival Prediction & Environmental Reporting

**AI-Powered Tree Survival Prediction and Environmental Monitoring for Kenya**

MsituGuard combines advanced AI technology with community-driven environmental reporting to help restore Kenya's forests. Get accurate tree survival predictions for any location and report environmental issues to create real impact.

## 🎯 Core Features

### 🤖 AI Tree Survival Prediction
- **Species Recommendations** - Get AI-powered suggestions for trees that will thrive in your specific county
- **Survival Rate Analysis** - Receive accurate predictions based on location, season, and planting method
- **Expert Care Instructions** - Get detailed guidance powered by MISTRAL AI for optimal tree care
- **Risk Assessment** - Understand potential challenges and mitigation strategies

### 📱 Environmental Reporting System
- **Photo Documentation** - Capture and report environmental issues with GPS location
- **Community Verification** - Connect with local organizations for issue validation
- **Impact Tracking** - Monitor how your reports lead to real environmental action
- **Data Export** - Download reports for research and grant applications

### 📊 Monitoring & Analytics
- **Tree Registration** - Log and track your tree planting activities
- **Progress Dashboard** - Visualize your environmental impact over time
- **Community Forums** - Share experiences with other environmental champions
- **Rewards System** - Earn points and badges for verified contributions

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

## 🧠 AI Prediction Technology

### Hybrid Intelligence System
- **Machine Learning**: GradientBoosting Classifier trained on 10,000+ Kenyan tree records
- **Expert Knowledge**: Comprehensive database covering all 47 Kenyan counties
- **MISTRAL AI**: Advanced language model for intelligent explanations and care guidance
- **Accuracy**: Combines ML predictions (40%) with expert knowledge (60%) for optimal results

### Prediction Factors
| Factor | Impact | Description |
|--------|--------|-------------|
| **Species Type** | High | Native vs non-native adaptation rates |
| **Location** | High | County-specific climate and soil conditions |
| **Season** | Medium | Optimal planting timing for survival |
| **Method** | Medium | Planting technique and preparation |
| **Care Level** | Medium | Maintenance and monitoring intensity |

## 🚀 How It Works

### 1. Tree Survival Prediction
1. **Select Location** - Choose any of Kenya's 47 counties
2. **Get AI Analysis** - Receive species recommendations with survival rates
3. **View Care Instructions** - Access MISTRAL AI-powered planting guidance
4. **Make Informed Decisions** - Plant trees with confidence

### 2. Environmental Reporting
1. **Document Issues** - Take photos of environmental problems
2. **Add Details** - Include location, description, and severity
3. **Submit Report** - Share with community and organizations
4. **Track Impact** - Monitor how reports lead to action

### 3. Community Engagement
- **Free Access** - Try predictions and submit reports without registration
- **User Accounts** - Save history, register plantings, earn rewards
- **Organization Dashboard** - Verify reports and track community impact
- **Data Export** - Download CSV files for research and grants

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

## ✨ Platform Highlights

### 🌳 Tree Survival Prediction
- Complete species database for all 47 Kenyan counties
- Hybrid AI system combining machine learning with expert knowledge
- MISTRAL AI-powered care instructions and risk assessments
- Seasonal optimization and alternative species recommendations

### 🌍 Environmental Reporting
- GPS-enabled photo documentation of environmental issues
- Community-driven verification and organization dashboards
- Impact tracking from report submission to resolution
- CSV data export for research and grant applications

### 📊 Data & Community
- User accounts with prediction history and tree registration
- Points and badges reward system for verified contributions
- Community forums for knowledge sharing
- Mobile-responsive design for field use

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

## 🌍 Try MsituGuard Today

**Live Platform**: https://msituguard.onrender.com

**Get Started**:
1. Visit the platform
2. Try tree predictions for any Kenyan county
3. Report environmental issues in your area
4. Join the community of environmental champions

---

**Predict. Plant. Protect. 🌳**

*MsituGuard - AI-Powered Environmental Action for Kenya*