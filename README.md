# AI Job Application Agent

An intelligent automation system that helps streamline the job application process using AI-powered tools.

## Features

- **Job Discovery**: Automatically find relevant job postings based on your profile
- **Resume Optimization**: Tailor your resume for specific job requirements using AI
- **Application Automation**: Automate form filling and application submission
- **Human-in-the-Loop**: Review and approve applications before submission
- **Application Tracking**: Monitor the status of your job applications
- **AI Integration**: Powered by Google Gemini for intelligent decision making

## Development Progress

### Phase 2: Core Agent Architecture & MVP Definition ✅ **Completed**
- ✅ All Pydantic data models defined and validated
- ✅ MVP scope clearly defined with workflow and success criteria
- ✅ Database schema implemented and tested
- ✅ API integrations (Gemini, Playwright) verified

### Phase 3: MVP Development – Building Core Modules ⏳ **In Progress**
**Objective**: Iteratively build and test the modules defined for the MVP scope.

**Current Status**: 
- ✅ CLI Framework (`main.py`) implemented using Typer and Rich
- ✅ SerpAPI Integration (`app/services/serpapi_client.py`) completed and integrated
- ✅ `find-jobs` command now functional with SerpAPI integration - can fetch and display job listings
- ⏳ Next: Database Service (`app/services/database_service.py`) for saving job results

## Project Structure

```
ai_job_application_agent/
├── app/                        # Main application code
│   ├── agent_orchestrator.py   # Main coordination logic
│   ├── discovery/              # Job discovery module
│   ├── resume_management/      # Resume optimization
│   ├── application_automation/ # Form filling automation
│   ├── hitl/                   # Human-in-the-loop interface
│   ├── tracking/               # Application tracking
│   ├── services/               # External service integrations
│   └── models/                 # Data models
├── config/                     # Configuration management
├── data/                       # Data storage
│   ├── logs/                   # Application logs
│   ├── user_profiles/          # User profile data
│   └── output_resumes/         # Generated resumes
├── notebooks/                  # Jupyter notebooks for analysis
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
└── main.py                     # CLI entry point
```

## Setup

1. **Clone the repository** (if using Git)
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in your API keys and configuration

## Configuration

Create a `.env` file with the following variables:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SERPAPI_API_KEY=your_serpapi_key_here
DATABASE_URL=sqlite:///data/agent_database.db
CAPSOLVER_API_KEY=your_capsolver_api_key_here
```

## Usage

Ensure your virtual environment is active and the `.env` file is configured with necessary API keys.

To see available commands:
```bash
python main.py --help
```

To run specific commands:
```bash
# Find jobs (requires SERPAPI_API_KEY)
python main.py find-jobs --keywords "Python Developer" --location "Remote"

# Log a job application
python main.py log-application --job-url "https://example.com/job/123" --resume-path "resume.pdf"

# Get help for a specific command
python main.py find-jobs --help
```

*Note: Actual functionality for commands is under development in Phase 3*

## Development

### Running Tests

```bash
pytest
```

### Code Structure

- **Modular Design**: Each component is separated into its own module
- **Service Layer**: External integrations are abstracted into service classes
- **Data Models**: Pydantic models for data validation and structure
- **Configuration**: Centralized configuration management

#### Data Models (`app/models/`)

- `user_profile_models.py`: Defines Pydantic models for user profiles, including skills, experience, education, and job search preferences. ✅ **Completed**
- `job_posting_models.py`: Defines Pydantic models for job postings scraped from various sources (LinkedIn, Indeed, SerpApi), including job details, descriptions, extracted skills, and AI relevance scoring. ✅ **Completed**
- `application_log_models.py`: Defines models for tracking job application statuses and history. ✅ **Completed**
- `gemini_interaction_models.py`: Defines models for structuring requests to and responses from the Gemini API. ✅ **Completed**

**All core Pydantic data models for Phase 2 are now defined, ensuring consistent data structures across the application.**

## Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

[Add your license information here] 