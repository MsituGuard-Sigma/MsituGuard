# MsituGuard

MsituGuard is an AI-powered environmental conservation platform built for Kenya. It helps people make better tree-planting decisions and provides a simple way to report environmental issues.

The project was created during Hack for the Environment to support Kenya’s 15 billion Trees by 2032 initiative. The core idea is practical: plant smarter, not just more.

## Problem

Many tree-planting efforts fail because species are planted without checking whether local conditions support survival. This wastes time, funding, and community effort.

Environmental threats such as illegal logging, pollution, and waste dumping also go unreported or are hard to follow up on because communities lack a safe, simple reporting channel.

## What MsituGuard Does

- Predicts tree survival for a location before planting, using environmental signals (location, season, and weather).
- Recommends suitable tree species for a county to improve survival rates.
- Provides planting and after-care guidance tailored to the user’s situation.
- Supports tree registration and tracking to improve accountability and motivation.
- Enables environmental reporting (with location and image evidence) and an organization dashboard for review.
- Includes a community space for discussion and shared learning.

## Tools and Technologies

- Backend: Django (Python)
- Frontend: Django templates, JavaScript, Bootstrap/CSS
- Database: SQLite (development) and PostgreSQL-ready for production
- Weather data: OpenWeather (when available)
- Machine learning: scikit-learn (optional model) plus rule-based fallbacks
- LLM text generation: Groq API (explanations and care instructions)
- Deployment: Render
